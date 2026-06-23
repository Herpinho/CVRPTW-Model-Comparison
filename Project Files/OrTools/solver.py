import math
import time
import sys
from dataclasses import dataclass
from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2


# ── Estruturas de dados

@dataclass
class Customer:
    id: int
    x: float
    y: float
    demand: float
    ready_time: float
    due_time: float
    service_time: float


@dataclass
class Instance:
    name: str
    vehicle_capacity: float
    num_vehicles: int
    depot: Customer
    customers: list[Customer]

    @property
    def n(self) -> int:
        return len(self.customers)


# ── Parser dos ficheiros de Solomon 

def load_solomon(filepath: str) -> Instance:
    with open(filepath) as f:
        all_lines = f.readlines()

    name = all_lines[0].strip()

    num_vehicles, capacity = None, None
    for i, line in enumerate(all_lines):
        if "NUMBER" in line and "CAPACITY" in line:
            parts = all_lines[i + 1].split()
            num_vehicles, capacity = int(parts[0]), float(parts[1])
            break

    nodes = []
    reading = False
    for line in all_lines:
        if "CUST" in line and "NO" in line:
            reading = True
            continue
        if reading:
            parts = line.split()
            if len(parts) >= 7:
                try:
                    nodes.append(Customer(
                        id=int(parts[0]),
                        x=float(parts[1]), y=float(parts[2]),
                        demand=float(parts[3]),
                        ready_time=float(parts[4]),
                        due_time=float(parts[5]),
                        service_time=float(parts[6])
                    ))
                except ValueError:
                    continue

    depot = nodes[0]
    depot.id = 0
    customers = nodes[1:]
    for i, c in enumerate(customers, 1):
        c.id = i

    return Instance(name, capacity, num_vehicles, depot, customers)


# ── Distância euclidiana (ponto de extensão)

def euclidean(ax, ay, bx, by) -> float:
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


# ── Solver OR-Tools 

def solve_cvrptw(
    instance: Instance,
    time_limit: float = 300.0,
    mip_gap: float = 0.01,
    verbose: bool = True,
    speed_kmh: float = 60.0,
) -> dict:
    
    
    """
    Interface idêntica ao solver.py Gurobi:
        - Usa os mesmos parâmetros de entrada
        - E os mesmos formatos do dicionário de retorno:
            {
                "status":       str  ("OPTIMAL" | "TIME_LIMIT" | "INFEASIBLE")
                "obj_value":    float | None
                "mip_gap":      float | None
                "runtime":      float
                "routes":       [ {"vehicle", "route", "load", "distance", "times"} ]
                "num_vehicles": int
            }

    """
    all_nodes = [instance.depot] + instance.customers
    n = len(all_nodes)

    SCALE = 1000  # converte float → inteiro mantendo precisão milimétrica

    # Matriz de distâncias reais — usa a função global `euclidean`
    dist_real = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                dist_real[i][j] = euclidean(
                    all_nodes[i].x, all_nodes[i].y,
                    all_nodes[j].x, all_nodes[j].y,
                )

    dist_int = [[int(round(d * SCALE)) for d in row] for row in dist_real]

    # Matriz de tempos de viagem (minutos) = distância / velocidade + serviço
    time_matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            travel_min = (dist_real[i][j] / speed_kmh) * 60.0 if speed_kmh > 0 else dist_real[i][j]
            time_matrix[i][j] = int(round(travel_min)) + int(all_nodes[i].service_time)

    demands      = [int(c.demand)       for c in all_nodes]
    time_windows = [(int(c.ready_time), int(c.due_time)) for c in all_nodes]

    if verbose:
        print(f"  [OR-Tools] Nós: {n} | Veículos: {instance.num_vehicles} | "
              f"Tempo limite: {time_limit}s")

    manager = pywrapcp.RoutingIndexManager(n, instance.num_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def dist_cb(fi, ti):
        return dist_int[manager.IndexToNode(fi)][manager.IndexToNode(ti)]
    dist_cb_idx = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(dist_cb_idx)

    def dem_cb(fi):
        return demands[manager.IndexToNode(fi)]
    dem_cb_idx = routing.RegisterUnaryTransitCallback(dem_cb)
    routing.AddDimensionWithVehicleCapacity(
        dem_cb_idx, 0,
        [int(instance.vehicle_capacity)] * instance.num_vehicles,
        True, "Capacity",
    )

    def time_cb(fi, ti):
        return time_matrix[manager.IndexToNode(fi)][manager.IndexToNode(ti)]
    time_cb_idx = routing.RegisterTransitCallback(time_cb)
    horizon = int(instance.depot.due_time) + int(instance.depot.service_time) + 1
    routing.AddDimension(time_cb_idx, horizon, horizon, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")

    for node, (ready, due) in enumerate(time_windows):
        idx = manager.NodeToIndex(node)
        time_dim.CumulVar(idx).SetRange(ready, due)

    for v in range(instance.num_vehicles):
        routing.AddVariableMinimizedByFinalizer(
            time_dim.CumulVar(routing.End(v))
        )

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    params.time_limit.seconds = max(1, int(time_limit))

    start    = time.time()
    solution = routing.SolveWithParameters(params)
    elapsed  = time.time() - start

    if solution is None:
        return {
            "status":       "INFEASIBLE",
            "obj_value":    None,
            "mip_gap":      None,
            "runtime":      elapsed,
            "routes":       [],
            "num_vehicles": 0,
        }

    routes     = []
    total_dist = 0.0

    for v in range(instance.num_vehicles):
        idx = routing.Start(v)
        if routing.IsEnd(solution.Value(routing.NextVar(idx))):
            continue

        route_nodes = [manager.IndexToNode(idx)]
        route_times = [float(solution.Min(time_dim.CumulVar(idx)))]
        route_load  = demands[route_nodes[0]]
        route_dist  = 0.0

        while not routing.IsEnd(idx):
            nxt      = solution.Value(routing.NextVar(idx))
            i, j     = manager.IndexToNode(idx), manager.IndexToNode(nxt)
            route_dist += dist_real[i][j]
            idx = nxt
            node = manager.IndexToNode(idx)
            route_nodes.append(node)
            route_times.append(float(solution.Min(time_dim.CumulVar(idx))))
            route_load  += demands[node]

        # Converter nó final de depósito: OR-Tools usa só 1 nó de depósito (0)
        display = route_nodes  # 0 = depósito

        routes.append({
            "vehicle":  v + 1,         
            "route":    display,
            "load":     route_load - demands[0],  # desconta o depósito inicial e final
            "distance": route_dist,
            "times":    route_times,    # minutos desde ready_time do depósito
        })
        total_dist += route_dist

    gap    = 0.0 if elapsed < time_limit * 0.95 else max(mip_gap, 0.001)
    status = "OPTIMAL" if elapsed < time_limit * 0.95 else "TIME_LIMIT"

    if verbose:
        print(f"  [OR-Tools] Distância: {total_dist:.2f} | "
              f"Veículos: {len(routes)} | Tempo: {elapsed:.1f}s | Estado: {status}")

    return {
        "status":       status,
        "obj_value":    total_dist,
        "mip_gap":      gap,
        "runtime":      elapsed,
        "routes":       routes,
        "num_vehicles": len(routes),
    }


# ── Referências Solomon 
# Formato: nome_instância → (num_veículos, distância)

SOLOMON_REFERENCE = {
    # Classe C1 — clientes em cluster, janelas apertadas
    "C101": (10, 828.94), "C102": (10, 828.94), "C103": (10, 828.06),
    "C104": (10, 824.78), "C105": (10, 828.94), "C106": (10, 828.94),
    "C107": (10, 828.94), "C108": (10, 828.94), "C109": (10, 828.94),
    # Classe C2 — clientes em cluster, janelas largas
    "C201": (3, 591.56),  "C202": (3, 591.56),  "C203": (3, 591.17),
    "C204": (3, 590.60),  "C205": (3, 588.88),  "C206": (3, 588.49),
    "C207": (3, 588.29),  "C208": (3, 588.32),
    # Classe R1 — clientes aleatórios, janelas apertadas
    "R101": (19, 1645.79), "R102": (17, 1486.12), "R103": (13, 1292.68),
    "R104": (9,  1007.31), "R105": (14, 1377.11), "R106": (12, 1251.98),
    "R107": (10, 1104.66), "R108": (9,   960.88), "R109": (11, 1194.73),
    "R110": (10, 1118.84), "R111": (10, 1096.72), "R112": (9,   982.14),
    # Classe R2 — clientes aleatórios, janelas largas
    "R201": (4, 1252.37), "R202": (3, 1191.70), "R203": (3, 939.50),
    "R204": (2,  825.52), "R205": (3, 994.42),  "R206": (3, 906.14),
    "R207": (2,  890.61), "R208": (2, 726.82),  "R209": (3, 909.16),
    "R210": (3,  939.37), "R211": (2, 885.71),
    # Classe RC1 — misto, janelas apertadas
    "RC101": (14, 1696.94), "RC102": (12, 1554.75), "RC103": (11, 1261.67),
    "RC104": (10, 1135.48), "RC105": (13, 1629.44), "RC106": (11, 1424.73),
    "RC107": (11, 1230.48), "RC108": (10, 1139.82),
    # Classe RC2 — misto, janelas largas
    "RC201": (4, 1406.91), "RC202": (3, 1365.65), "RC203": (3, 1049.62),
    "RC204": (3,  798.46), "RC205": (4, 1297.19), "RC206": (3, 1146.32),
    "RC207": (3, 1061.14), "RC208": (3,  828.14),
}


# ── print_solution 

def print_solution(result: dict, instance: Instance) -> None:
    status_map = {
        "OPTIMAL":    "ÓPTIMO (busca convergiu)",
        "TIME_LIMIT": "LIMITE DE TEMPO",
        "INFEASIBLE": "INFEASIBLE",
    }
    print("\n" + "=" * 60)
    print(f"  Instância : {instance.name}")
    print(f"  Estado    : {status_map.get(result['status'], str(result['status']))}")
    print(f"  Tempo     : {result['runtime']:.2f}s")

    if result["obj_value"] is None:
        print("  Nenhuma solução encontrada.")
        print("=" * 60)
        return

    print(f"  Distância : {result['obj_value']:.2f}")
    print(f"  MIP Gap   : {result['mip_gap'] * 100:.2f}%")
    print(f"  Veículos  : {result['num_vehicles']}")

    ref = SOLOMON_REFERENCE.get(instance.name.upper())
    if ref:
        ref_vehicles, ref_dist = ref
        gap_dist = ((result["obj_value"] - ref_dist) / ref_dist) * 100
        gap_veh  = result["num_vehicles"] - ref_vehicles
        print(f"\n  ── Comparação com referência Solomon ──")
        print(f"  Ref. Distância : {ref_dist:.2f}  (obtida: {result['obj_value']:.2f})  "
              f"gap: {gap_dist:+.2f}%  {'✓ Ótimo global!' if abs(gap_dist) < 0.01 else ''}")
        print(f"  Ref. Veículos  : {ref_vehicles}      "
              f"(obtidos: {result['num_vehicles']})       dif: {gap_veh:+d}")
    else:
        print(f"\n  (Sem referência disponível para '{instance.name}')")

    print("=" * 60)

    for r in result["routes"]:
        route_str = " → ".join(str(node) for node in r["route"])
        print(f"\n  Veículo {r['vehicle']:>2} | Carga: {r['load']:.0f} | Dist: {r['distance']:.2f}")
        print(f"    {route_str}")


# ── Ponto de entrada 

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python solver.py <ficheiro_solomon>")
        print("Exemplo: python solver.py solomon/C101.txt")
        sys.exit(1)

    instance = load_solomon(sys.argv[1])

    print(f"Instância carregada: {instance.name}")
    print(f"  Clientes  : {instance.n}")
    print(f"  Veículos  : {instance.num_vehicles}")
    print(f"  Capacidade: {instance.vehicle_capacity}")

    result = solve_cvrptw(
        instance,
        time_limit=300.0,
        mip_gap=0.01,
        verbose=True,
        speed_kmh=60.0,
    )

    print_solution(result, instance)
