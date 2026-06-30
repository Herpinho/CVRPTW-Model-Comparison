# http://localhost:5000

import importlib.util, os, sys, math, json, time, threading
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

#Carregar solver.py 
_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "solver.py")
_spec = importlib.util.spec_from_file_location("cvrptw_solver", _path)
_mod  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

Customer          = _mod.Customer
Instance          = _mod.Instance
solve_cvrptw      = _mod.solve_cvrptw
load_solomon      = _mod.load_solomon
SOLOMON_REFERENCE = _mod.SOLOMON_REFERENCE

from lisboa_data import DEPOSITO, CLIENTES
from visualize_routes import generate_html

ROUTES_DIR = os.path.join(os.path.dirname(__file__), "static", "routes")
os.makedirs(ROUTES_DIR, exist_ok=True)

ALL_LOCATIONS = [DEPOSITO] + CLIENTES


def generate_routes_html_async(instance, result, instance_name):
    try:
        output_path = os.path.join(ROUTES_DIR, f"{instance_name}_routes.html")
        generate_html(instance, result, output_path)
        print(f"✓ HTML gerado para {instance_name}: {output_path}")
    except Exception as e:
        print(f"✗ Erro ao gerar HTML para {instance_name}: {e}")


def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2 +
         math.cos(lat1 * p) * math.cos(lat2 * p) *
         math.sin((lon2 - lon1) * p / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def get_distances(points):
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
    travel = {}
    for pi in points:
        for pj in points:
            if pi["id"] != pj["id"]:
                travel[(pi["id"], pj["id"])] = haversine(pi["lat"], pi["lon"], pj["lat"], pj["lon"])
    return travel, "haversine"


@app.route("/")
def home():
    return render_template("home.html")

@app.route("/lisboa")
def lisboa():
    return render_template("index.html", locations=ALL_LOCATIONS)

@app.route("/benchmark")
def benchmark():
    return render_template("benchmark.html")

@app.route("/api/locations")
def api_locations():
    return jsonify(ALL_LOCATIONS)


@app.route("/api/solve", methods=["POST"])
def api_solve():
    try:
        data = request.get_json()
        selected_ids     = data.get("selected_ids", [])
        num_vehicles     = int(data.get("num_vehicles", 3))
        vehicle_capacity = int(data.get("vehicle_capacity", 200))
        time_limit       = float(data.get("time_limit", 60))

        if not selected_ids:
            return jsonify({"error": "Nenhum cliente selecionado."}), 400

        loc_map      = {p["id"]: p for p in ALL_LOCATIONS}
        total_demand = sum(loc_map[i]["demand"] for i in selected_ids if i in loc_map)
        min_vehicles = math.ceil(total_demand / vehicle_capacity)
        if min_vehicles > num_vehicles:
            return jsonify({"error": f"Capacidade insuficiente. Procura total: {total_demand} unid. "
                                     f"Precisas de pelo menos {min_vehicles} veículos com capacidade {vehicle_capacity}."}), 400

        selected_clients   = [loc_map[i] for i in selected_ids if i in loc_map]
        points             = [DEPOSITO] + selected_clients
        travel, dist_source = get_distances(points)

        id_original_to_seq = {c["id"]: i+1 for i, c in enumerate(selected_clients)}
        id_seq_to_original = {v: k for k, v in id_original_to_seq.items()}

        depot = Customer(id=0, x=DEPOSITO["lon"], y=DEPOSITO["lat"], demand=0,
                         ready_time=DEPOSITO["ready_time"], due_time=DEPOSITO["due_time"], service_time=0)
        customers = [Customer(id=id_original_to_seq[c["id"]], x=c["lon"], y=c["lat"],
                              demand=c["demand"], ready_time=c["ready_time"],
                              due_time=c["due_time"], service_time=c["service_time"])
                     for c in selected_clients]

        travel_seq = {}
        for c_i in selected_clients:
            seq_i = id_original_to_seq[c_i["id"]]
            travel_seq[(0, seq_i)] = travel.get((0, c_i["id"]),
                haversine(DEPOSITO["lat"], DEPOSITO["lon"], c_i["lat"], c_i["lon"]))
            travel_seq[(seq_i, 0)] = travel.get((c_i["id"], 0),
                haversine(c_i["lat"], c_i["lon"], DEPOSITO["lat"], DEPOSITO["lon"]))
            for c_j in selected_clients:
                if c_i["id"] == c_j["id"]: continue
                seq_j = id_original_to_seq[c_j["id"]]
                travel_seq[(seq_i, seq_j)] = travel.get((c_i["id"], c_j["id"]),
                    haversine(c_i["lat"], c_i["lon"], c_j["lat"], c_j["lon"]))

        coord_to_seq = {(round(DEPOSITO["lon"], 8), round(DEPOSITO["lat"], 8)): 0}
        for c in selected_clients:
            coord_to_seq[(round(c["lon"], 8), round(c["lat"], 8))] = id_original_to_seq[c["id"]]

        def real_dist(ax, ay, bx, by):
            id_a = coord_to_seq.get((round(ax, 8), round(ay, 8)))
            id_b = coord_to_seq.get((round(bx, 8), round(by, 8)))
            if id_a is not None and id_b is not None and id_a != id_b:
                return travel_seq.get((id_a, id_b), haversine(ay, ax, by, bx))
            return haversine(ay, ax, by, bx)

        _mod.euclidean = real_dist

        instance = Instance(name="Lisboa-MarquesPombal", vehicle_capacity=vehicle_capacity,
                            num_vehicles=num_vehicles, depot=depot, customers=customers)

        result = solve_cvrptw(instance, time_limit=time_limit, mip_gap=0.01, verbose=False)

        if result["obj_value"] is None:
            return jsonify({"error": "Nenhuma solução encontrada. Tenta aumentar o tempo limite "
                                     "ou reduzir o número de clientes.", "status": "infeasible"}), 400

        routes_out = []
        for r in result["routes"]:
            stops        = []
            solver_times = r.get("times", [])
            for idx, node in enumerate(r["route"]):
                orig_id = id_seq_to_original.get(node, 0)
                p = loc_map.get(orig_id, DEPOSITO)
                arrival_time_str = ""
                if idx < len(solver_times):
                    time_min = int(solver_times[idx])
                    arrival_time_str = f"{7 + time_min // 60:02d}:{time_min % 60:02d}"
                stops.append({"id": orig_id, "nome": p.get("nome", "Depósito"),
                              "tipo": p.get("tipo", "Depósito"), "lat": p["lat"], "lon": p["lon"],
                              "demand": p.get("demand", 0), "arrival_time": arrival_time_str})
            routes_out.append({"vehicle": r["vehicle"], "load": r["load"],
                                "distance": round(r["distance"], 2), "stops": stops})

        return jsonify({"status": "optimal" if result["mip_gap"] < 0.001 else "feasible",
                        "obj_value": round(result["obj_value"], 2),
                        "mip_gap": round(result["mip_gap"] * 100, 2),
                        "runtime": round(result["runtime"], 2),
                        "num_vehicles": result["num_vehicles"],
                        "distance_source": dist_source,
                        "routes": routes_out})

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500


@app.route("/api/benchmark", methods=["POST"])
def api_benchmark():
    try:
        data       = request.get_json()
        instances  = data.get("instances", [])
        time_limit = float(data.get("time_limit", 300))

        if not instances:
            return jsonify({"error": "Nenhuma instância selecionada"}), 400

        results = []
        for inst_name in instances:
            try:
                solomon_file = None
                for root, dirs, files in __import__('os').walk("in"):
                    for file in files:
                        if file.lower() == f"{inst_name.lower()}.txt":
                            solomon_file = __import__('os').path.join(root, file)
                            break

                if not solomon_file:
                    results.append({"instance": inst_name,
                                    "error": f"Ficheiro não encontrado: {inst_name}.txt"})
                    continue

                instance = load_solomon(solomon_file)
                result   = solve_cvrptw(instance, time_limit=time_limit,
                                        mip_gap=0.001, verbose=False, speed_kmh=60.0)

                if result["obj_value"] is not None:
                    thread = threading.Thread(target=generate_routes_html_async,
                                             args=(instance, result, inst_name), daemon=True)
                    thread.start()

                ref = SOLOMON_REFERENCE.get(inst_name.upper())
                ref_veh, ref_dist = ref if ref else (None, None)
                gap_solomon = (result["obj_value"] - ref_dist) / ref_dist * 100 if ref_dist and result["obj_value"] else None

                route_data = []
                if result.get("routes"):
                    clients = {i: c for i, c in enumerate(instance.customers, 1)}
                    depot   = instance.depot
                    for route in result["routes"]:
                        stops = []
                        for node in route.get("route", []):
                            if node == 0:
                                stops.append({"id": 0, "nome": "Depósito",
                                              "lat": depot.x, "lon": depot.y, "demand": 0})
                            else:
                                client = clients.get(node)
                                if client:
                                    stops.append({"id": node, "nome": f"Cliente {node}",
                                                  "lat": client.x, "lon": client.y,
                                                  "demand": client.demand})
                        route_data.append({"vehicle": route.get("vehicle"), "stops": stops,
                                           "distance": route.get("distance"), "load": route.get("load")})

                status_str = ("optimal"    if result["status"] == "OPTIMAL"   else
                              "feasible"   if result["obj_value"] is not None  else
                              "infeasible")

                results.append({"instance": inst_name, "status": status_str,
                                "distance": result["obj_value"] or 0,
                                "ref_distance": ref_dist or 0,
                                "gap_solomon": gap_solomon or 0,
                                "mip_gap": result["mip_gap"] * 100 if result["mip_gap"] else 0,
                                "num_vehicles": result["num_vehicles"],
                                "runtime": result["runtime"],
                                "routes": route_data,
                                "html_url": f"/static/routes/{inst_name}_routes.html"})

            except Exception as e:
                print(f"Erro ao resolver {inst_name}: {str(e)}")
                results.append({"instance": inst_name, "error": f"Erro na resolução: {str(e)}"})

        return jsonify(results)

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Erro: {str(e)}"}), 500


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  CVRPTW — Servidor Flask (OR-Tools)")
    print("  ")
    print("  📍 Lisboa:    http://localhost:5000/lisboa")
    print("  🔬 Benchmark: http://localhost:5000/benchmark")
    print("="*55 + "\n")
    app.run(debug=False, port=5000)
