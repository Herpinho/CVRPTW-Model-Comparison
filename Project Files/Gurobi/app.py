# http://localhost:5000


import importlib.util, os, sys, math, json, time
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

_spec = importlib.util.spec_from_file_location(
    "cvrptw_solver",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "BigM.py")
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
Customer     = _mod.Customer
Instance     = _mod.Instance
solve_cvrptw = _mod.solve_cvrptw

from lisboa_data import DEPOSITO, CLIENTES


ALL_LOCATIONS = [DEPOSITO] + CLIENTES

def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0  # km
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2 +
         math.cos(lat1 * p) * math.cos(lat2 * p) *
         math.sin((lon2 - lon1) * p / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def get_distances(points: list[dict]) -> dict:
    """
    Tenta obter distâncias reais via OSRM.
    Fallback para Haversine se OSRM indisponível.
    """
    import urllib.request
    coords_str = ";".join(f"{p['lon']},{p['lat']}" for p in points)
    url = (f"http://router.project-osrm.org/table/v1/driving/"
           f"{coords_str}?annotations=distance")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CVRPTW-UAL/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        if data.get("code") == "Ok":
            matrix = data["distances"]
            travel = {}
            for i, pi in enumerate(points):
                for j, pj in enumerate(points):
                    if i != j:
                        travel[(pi["id"], pj["id"])] = matrix[i][j] / 1000.0 
            return travel, "osrm"
    except Exception:
        pass

    # Fallback Haversine
    travel = {}
    for pi in points:
        for pj in points:
            if pi["id"] != pj["id"]:
                d = haversine(pi["lat"], pi["lon"], pj["lat"], pj["lon"])
                travel[(pi["id"], pj["id"])] = d  # já em km
    return travel, "haversine"



@app.route("/")
def index():
    return render_template("index.html", locations=ALL_LOCATIONS)


@app.route("/api/locations")
def api_locations():
    """Devolve todos os locais disponíveis."""
    return jsonify(ALL_LOCATIONS)


@app.route("/api/solve", methods=["POST"])
def api_solve():
    try:
        data = request.get_json()

        selected_ids     = data.get("selected_ids", [])
        num_vehicles     = int(data.get("num_vehicles", 3))
        vehicle_capacity = int(data.get("vehicle_capacity", 200))
        time_limit       = float(data.get("time_limit", 60))

        if len(selected_ids) == 0:
            return jsonify({"error": "Nenhum cliente selecionado."}), 400

        loc_map      = {p["id"]: p for p in ALL_LOCATIONS}
        total_demand = sum(loc_map[i]["demand"] for i in selected_ids if i in loc_map)
        min_vehicles = math.ceil(total_demand / vehicle_capacity)
        if min_vehicles > num_vehicles:
            return jsonify({
                "error": f"Capacidade insuficiente. Procura total: {total_demand} unid. "
                         f"Precisas de pelo menos {min_vehicles} veículos com capacidade {vehicle_capacity}."
            }), 400

        selected_clients = [loc_map[i] for i in selected_ids if i in loc_map]
        points           = [DEPOSITO] + selected_clients

        travel, dist_source = get_distances(points)

        id_original_to_seq = {c["id"]: i+1 for i, c in enumerate(selected_clients)}
        id_seq_to_original = {v: k for k, v in id_original_to_seq.items()}

        depot = Customer(
            id=0,
            x=DEPOSITO["lon"], y=DEPOSITO["lat"],
            demand=0,
            ready_time=DEPOSITO["ready_time"],
            due_time=DEPOSITO["due_time"],
            service_time=0
        )
        customers = [
            Customer(
                id=id_original_to_seq[c["id"]],  # ID sequencial
                x=c["lon"], y=c["lat"],
                demand=c["demand"],
                ready_time=c["ready_time"],
                due_time=c["due_time"],
                service_time=c["service_time"]
            ) for c in selected_clients
        ]

        # Reconstruir dicionário de distâncias com IDs sequenciais
        travel_seq = {}
        for c_i in selected_clients:
            seq_i = id_original_to_seq[c_i["id"]]
            # depósito → cliente
            travel_seq[(0, seq_i)] = travel.get((0, c_i["id"]),
                haversine(DEPOSITO["lat"], DEPOSITO["lon"], c_i["lat"], c_i["lon"]))
            travel_seq[(seq_i, 0)] = travel.get((c_i["id"], 0),
                haversine(c_i["lat"], c_i["lon"], DEPOSITO["lat"], DEPOSITO["lon"]))
            for c_j in selected_clients:
                if c_i["id"] == c_j["id"]: continue
                seq_j = id_original_to_seq[c_j["id"]]
                travel_seq[(seq_i, seq_j)] = travel.get((c_i["id"], c_j["id"]),
                    haversine(c_i["lat"], c_i["lon"], c_j["lat"], c_j["lon"]))

        # Construir mapa de coordenadas 
        coord_to_seq = {(round(DEPOSITO["lon"], 8), round(DEPOSITO["lat"], 8)): 0}
        for c in selected_clients:
            coord_to_seq[(round(c["lon"], 8), round(c["lat"], 8))] = id_original_to_seq[c["id"]]

        def real_dist(ax, ay, bx, by):
            id_a = coord_to_seq.get((round(ax, 8), round(ay, 8)))
            id_b = coord_to_seq.get((round(bx, 8), round(by, 8)))
            if id_a is not None and id_b is not None and id_a != id_b:
                return travel_seq.get((id_a, id_b),
                       haversine(ay, ax, by, bx))
            return haversine(ay, ax, by, bx)

        _mod.euclidean = real_dist

        instance = Instance(
            name="Lisboa-MarquesPombal",
            vehicle_capacity=vehicle_capacity,
            num_vehicles=num_vehicles,
            depot=depot,
            customers=customers
        )

        result = solve_cvrptw(instance, time_limit=time_limit, mip_gap=0.01, verbose=False)

        if result["obj_value"] is None:
            return jsonify({
                "error": "Nenhuma solução encontrada. Tenta aumentar o tempo limite "
                         "ou reduzir o número de clientes.",
                "status": "infeasible"
            }), 400

        # Construir resposta — converter IDs sequenciais de volta para originais
        routes_out = []
        for r in result["routes"]:
            stops = []
            for node in r["route"]:
                orig_id = id_seq_to_original.get(node, 0)  # 0 = depósito
                p = loc_map.get(orig_id, DEPOSITO)
                stops.append({
                    "id":     orig_id,
                    "nome":   p.get("nome", "Depósito"),
                    "tipo":   p.get("tipo", "Depósito"),
                    "lat":    p["lat"],
                    "lon":    p["lon"],
                    "demand": p.get("demand", 0),
                })
            routes_out.append({
                "vehicle":  r["vehicle"],
                "load":     r["load"],
                "distance": round(r["distance"], 2),
                "stops":    stops,
            })

        return jsonify({
            "status":          "optimal" if result["mip_gap"] < 0.001 else "feasible",
            "obj_value":       round(result["obj_value"], 2),
            "mip_gap":         round(result["mip_gap"] * 100, 2),
            "runtime":         round(result["runtime"], 2),
            "num_vehicles":    result["num_vehicles"],
            "distance_source": dist_source,
            "routes":          routes_out,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  CVRPTW Lisboa — Servidor Flask")
    print("  Abre http://localhost:5000 no browser")
    print("="*55 + "\n")
    app.run(debug=False, port=5000)