import gurobipy as gp
from gurobipy import GRB
import math
import time
from dataclasses import dataclass
import sys


# Estruturas de dados 

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


# Parser dos ficheiros de Solomon 

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


#  Distância euclidiana 

def euclidean(ax, ay, bx, by) -> float:
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


# Modelo Gurobi 
def solve_cvrptw(
    instance: Instance,
    time_limit: float = 300.0,
    mip_gap: float = 0.01,
    verbose: bool = True
) -> dict:
    """
    Formulação com dois nós de depósito (standard na literatura):
        Nó 0     — depósito de saída
        Nós 1..n — clientes
        Nó n+1   — depósito de chegada (cópia do depósito)

    Variáveis:
        x[i,j,k] ∈ {0,1}  — veículo k percorre arco (i→j)
        t[i,k]   ≥ 0       — instante de início de serviço do veículo k no nó i

    Objetivo: minimizar distância total percorrida
    """
    depot   = instance.depot
    clients = instance.customers
    K       = list(range(instance.num_vehicles))
    n       = instance.n

    DS = 0        # depot start
    DE = n + 1    # depot end
    N  = list(range(1, n + 1))
    V  = [DS] + N + [DE]

    coords = {DS: (depot.x, depot.y), DE: (depot.x, depot.y)}
    for c in clients:
        coords[c.id] = (c.x, c.y)

    demand       = {DS: 0, DE: 0}
    ready_time   = {DS: depot.ready_time, DE: depot.ready_time}
    due_time     = {DS: depot.due_time,   DE: depot.due_time}
    service_time = {DS: 0, DE: 0}
    for c in clients:
        demand[c.id]       = c.demand
        ready_time[c.id]   = c.ready_time
        due_time[c.id]     = c.due_time
        service_time[c.id] = c.service_time

    arcs   = [(i, j) for i in V for j in V
              if i != j and i != DE and j != DS]
    travel = {(i, j): euclidean(*coords[i], *coords[j]) for (i, j) in arcs}

    # Big-M 
    M = {}
    feasible_arcs = []
    for (i, j) in arcs:
        m_ij = due_time[i] + service_time[i] + travel[i, j] - ready_time[j]
        if m_ij > 0:
            M[i, j] = m_ij
            feasible_arcs.append((i, j))

    arcs   = feasible_arcs
    travel = {(i, j): travel[i, j] for (i, j) in arcs}
    print(f"  [Formulação] Arcos feasíveis: {len(arcs)} (de {(n+2)*(n+1)} totais)")

    model = gp.Model("CVRPTW")
    model.setParam("TimeLimit", time_limit)
    model.setParam("MIPGap", mip_gap)
    model.setParam("OutputFlag", 1 if verbose else 0)

    # Variáveis 

    x = model.addVars(
        [(i, j, k) for (i, j) in arcs for k in K],
        vtype=GRB.BINARY, name="x"
    )

    t = model.addVars(
        [(i, k) for i in V for k in K],
        lb=0.0, vtype=GRB.CONTINUOUS, name="t"
    )

    for i in V:
        for k in K:
            t[i, k].lb = ready_time[i]
            t[i, k].ub = due_time[i]

    # Função objetivo 
    model.setObjective(
        gp.quicksum(travel[i, j] * x[i, j, k] for (i, j) in arcs for k in K),
        GRB.MINIMIZE
    )

    # Arcos pré-indexados por nó
    out_arcs = {i: [(i, j) for (i2, j) in arcs if i2 == i] for i in V}
    in_arcs  = {j: [(i, j) for (i, j2) in arcs if j2 == j] for j in V}

    # Restrições 

    # 1. Cada cliente visitado exactamente uma vez
    for i in N:
        model.addConstr(
            gp.quicksum(x[i, j, k] for (_, j) in out_arcs[i] for k in K) == 1,
            name=f"visit_{i}"
        )

    # 2. Cada veículo parte do depósito no máximo uma vez
    for k in K:
        model.addConstr(
            gp.quicksum(x[DS, j, k] for (_, j) in out_arcs[DS]) <= 1,
            name=f"depart_{k}"
        )

    # 3. Continuidade de fluxo nos clientes
    for i in N:
        for k in K:
            model.addConstr(
                gp.quicksum(x[i, j, k] for (_, j) in out_arcs[i]) ==
                gp.quicksum(x[j, i, k] for (j, _) in in_arcs[i]),
                name=f"flow_{i}_{k}"
            )

    # 4. Conservação no depósito
    for k in K:
        model.addConstr(
            gp.quicksum(x[DS, j, k] for (_, j) in out_arcs[DS]) ==
            gp.quicksum(x[i, DE, k] for (i, _) in in_arcs[DE]),
            name=f"return_{k}"
        )

    # 5. Capacidade
    for k in K:
        model.addConstr(
            gp.quicksum(
                demand[i] * gp.quicksum(x[i, j, k] for (_, j) in out_arcs[i])
                for i in N
            ) <= instance.vehicle_capacity,
            name=f"cap_{k}"
        )

    # 6–8. Janelas de tempo já garantidas pelos bounds de t (lb/ub)
    for k in K:
        model.addConstr(t[DE, k] <= due_time[DE], name=f"tw_de_{k}")

    # 9. Consistência temporal com big-M 
    for (i, j) in arcs:
        for k in K:
            model.addConstr(
                t[j, k] >= t[i, k] + service_time[i] + travel[i, j]
                           - M[i, j] * (1 - x[i, j, k]),
                name=f"time_{i}_{j}_{k}"
            )

    # Warm start com estratégia Nearest Neighbor para ter um ponto de partida válido
    print("  [Warm start] A construir solução inicial com Nearest Neighbor...")
    nn_routes = nearest_neighbor(instance, travel, DS, DE,
                                 demand, ready_time, due_time, service_time)
    covered = sum(len(r) - 2 for r in nn_routes)
    print(f"  [Warm start] {len(nn_routes)} rotas construídas para {covered}/{instance.n} clientes")

    for key in x:
        x[key].Start = 0.0

    for k, route in enumerate(nn_routes):
        if k >= len(K):
            break
        current_time = float(ready_time[DS])
        for idx in range(len(route) - 1):
            i, j = route[idx], route[idx + 1]
            if (i, j) in travel:
                x[i, j, k].Start = 1.0
        
            dist         = travel.get((i, j), 0.0)
            arrival      = current_time + service_time[i] + dist
            current_time = max(arrival, float(ready_time[j]))
            t[j, k].Start = current_time

    # Resolver 

    start = time.time()
    model.optimize()
    elapsed = time.time() - start

    result = {
        "status":       model.Status,
        "obj_value":    None,
        "mip_gap":      None,
        "runtime":      elapsed,
        "routes":       [],
        "num_vehicles": 0,
    }

    if model.Status in (GRB.OPTIMAL, GRB.TIME_LIMIT) and model.SolCount > 0:
        result["obj_value"] = model.ObjVal
        result["mip_gap"]   = model.MIPGap

        routes = []
        for k in K:
            active = {(i, j) for (i, j) in arcs if x[i, j, k].X > 0.5}
            if not active:
                continue

            route = [DS]
            while True:
                current = route[-1]
                nxt = next((j for (i, j) in active if i == current), None)
                if nxt is None:
                    break
                route.append(nxt)
                active.discard((current, nxt))
                if nxt == DE:
                    break

            display = [0 if node == DE else node for node in route]

            routes.append({
                "vehicle":  k,
                "route":    display,
                "load":     sum(demand[i] for i in display if i != 0),
                "distance": sum(travel[route[i], route[i+1]]
                                for i in range(len(route) - 1)),
            })

        result["routes"]       = routes
        result["num_vehicles"] = len(routes)

    return result


# Estratégia Nearest Neighbor (warm start) 

def nearest_neighbor(instance: Instance, travel: dict, DS: int, DE: int,
                     demand: dict, ready_time: dict, due_time: dict,
                     service_time: dict) -> list[list[int]]:
    """
    Constrói uma solução inicial heurística usando Nearest Neighbor.
    Garante que todos os clientes são visitados — se necessário cria
    rotas extra com um cliente cada (ignorando janelas de tempo).
    """
    unvisited = set(range(1, instance.n + 1))
    routes    = []
    K         = list(range(instance.num_vehicles))

    for k in K:
        if not unvisited:
            break

        route        = [DS]
        load         = 0.0
        current_time = ready_time[DS]
        current      = DS

        while unvisited:
            best, best_dist, best_arrival = None, float("inf"), None

            for j in unvisited:
                if load + demand[j] > instance.vehicle_capacity:
                    continue
                dist    = travel.get((current, j), float("inf"))
                arrival = max(current_time + service_time[current] + dist,
                              ready_time[j])
                if arrival > due_time[j]:
                    continue
                return_time = arrival + service_time[j] + travel.get((j, DE), float("inf"))
                if return_time > due_time[DE]:
                    continue
                if dist < best_dist:
                    best, best_dist, best_arrival = j, dist, arrival

            if best is None:
                break

            route.append(best)
            load        += demand[best]
            current_time = best_arrival
            current      = best
            unvisited.discard(best)

        route.append(DE)
        if len(route) > 2:
            routes.append(route)

    # Forçar rota por clientes nao visitados
    if unvisited:
        remaining = list(unvisited)
        capacity  = instance.vehicle_capacity
        route     = [DS]
        load      = 0.0
        for j in remaining:
            if load + demand[j] > capacity:
                route.append(DE)
                routes.append(route)
                route = [DS]
                load  = 0.0
            route.append(j)
            load += demand[j]
        route.append(DE)
        if len(route) > 2:
            routes.append(route)

    return routes



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


def print_solution(result: dict, instance: Instance) -> None:
    status_map = {2: "ÓPTIMO", 3: "INFEASIBLE", 9: "LIMITE DE TEMPO"}
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
        print(f"  Ref. Distância : {ref_dist:.2f}  (obtida: {result['obj_value']:.2f})  gap: {gap_dist:+.2f}%  {'✓ Ótimo global!' if abs(gap_dist) < 0.01 else ''}")
        print(f"  Ref. Veículos  : {ref_vehicles}      (obtidos: {result['num_vehicles']})       dif: {gap_veh:+d}")
    else:
        print(f"\n  (Sem referência disponível para '{instance.name}')")

    print("=" * 60)

    for r in result["routes"]:
        route_str = " → ".join(str(node) for node in r["route"])
        print(f"\n  Veículo {r['vehicle']:>2} | Carga: {r['load']:.0f} | Dist: {r['distance']:.2f}")
        print(f"    {route_str}")


# Ponto de entrada 

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python gurobi.py <ficheiro_solomon>")
        print("Exemplo: python gurobi.py solomon/C101.txt")
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
        verbose=True
    )

    print_solution(result, instance)