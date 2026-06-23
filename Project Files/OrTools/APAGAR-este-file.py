import math
import sys
from dataclasses import dataclass
from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2



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


def create_data_model(instance: Instance) -> dict:
    all_nodes = [instance.depot] + instance.customers
    n = len(all_nodes)

    # Matriz das distâncias euclidianas
    distance_matrix = []
    for i in range(n):
        row = []
        for j in range(n):
            dx = all_nodes[i].x - all_nodes[j].x
            dy = all_nodes[i].y - all_nodes[j].y
            row.append(int(math.sqrt(dx * dx + dy * dy)))
        distance_matrix.append(row)

    time_windows  = [(int(c.ready_time), int(c.due_time))  for c in all_nodes]
    service_times = [int(c.service_time)                    for c in all_nodes]
    demands       = [int(c.demand)                          for c in all_nodes]

    return {
        "distance_matrix":  distance_matrix,
        "time_windows":     time_windows,
        "service_time":     service_times,
        "demands":          demands,
        "vehicle_capacity": int(instance.vehicle_capacity),
        "num_vehicles":     instance.num_vehicles,
        "depot":            0,
    }


def distance_callback(from_index, to_index, manager, data):
    """Custo do arco i→j (distância euclidiana em unidades Solomon)."""
    i = manager.IndexToNode(from_index)
    j = manager.IndexToNode(to_index)
    return data["distance_matrix"][i][j]


def time_callback(from_index, to_index, manager, data):
    """
    Tempo de trânsito i→j = distância(i,j) + tempo_serviço(i).
    No Solomon: distância == tempo de viagem (mesma escala, minutos).
    """
    i = manager.IndexToNode(from_index)
    j = manager.IndexToNode(to_index)
    return data["distance_matrix"][i][j] + data["service_time"][i]


def demand_callback(from_index, manager, data):
    """Procura do nó i."""
    i = manager.IndexToNode(from_index)
    return data["demands"][i]


def fmt_time(minutes):
    """Converte minutos para formato hh:mm."""
    h = int(minutes) // 60
    m = int(minutes) % 60
    return f"{h:02d}h{m:02d}min"


def fmt_dist(units):
    """Converte as unidades do Solomon para km (1 unidade ≈ 1 km)."""
    return f"{units / 10:.1f} km"




def print_solution(data, manager, routing, solution, instance_name: str):
    time_dim = routing.GetDimensionOrDie("Time")

    total_dist = 0
    total_load = 0

    print(f"\n{'='*70}")
    print(f"  SOLUÇÃO - {instance_name} | Distância total: "
          f"{fmt_dist(solution.ObjectiveValue())}")
    print(f"{'='*70}\n")

    for v in range(data["num_vehicles"]):
        idx = routing.Start(v)

        # Ignora os veículos que não têm clientes
        if routing.IsEnd(solution.Value(routing.NextVar(idx))):
            continue

        route_dist = 0
        route_load = 0
        stops = []

        while not routing.IsEnd(idx):
            node  = manager.IndexToNode(idx)
            t_var = time_dim.CumulVar(idx)
            t_arr = solution.Min(t_var)
            tw    = data["time_windows"][node]
            stops.append((node, t_arr, tw))
            route_load += data["demands"][node]

            nxt = solution.Value(routing.NextVar(idx))
            route_dist += routing.GetArcCostForVehicle(idx, nxt, v)
            idx = nxt

        # Depósito final
        node  = manager.IndexToNode(idx)
        t_var = time_dim.CumulVar(idx)
        t_arr = solution.Min(t_var)
        tw    = data["time_windows"][node]
        stops.append((node, t_arr, tw))

        print(f"  Veículo {v+1:2d}  |  Carga: {route_load}/{data['vehicle_capacity']}  "
              f"|  Distância: {fmt_dist(route_dist)}")
        for node, t_arr, tw in stops:
            tw_str  = f"[{fmt_time(tw[0])} – {fmt_time(tw[1])}]"
            arr_str = fmt_time(t_arr)
            label   = "Depósito" if node == 0 else f"Cliente {node:3d}"
            print(f"    {label}  Janela: {tw_str}  Chegada: {arr_str}")
        print()

        total_dist += route_dist
        total_load += route_load

    print(f"{'='*70}")
    print(f"  Distância total : {fmt_dist(total_dist)}")
    print(f"  Carga total     : {total_load}")
    print(f"{'='*70}\n")




def main():
    if len(sys.argv) < 2:
        print("Uso: python CVRPTW-em-ortools.py <ficheiro_solomon>")
        print("Exemplo: python CVRPTW-em-ortools.py solomon/C101.txt")
        sys.exit(1)

    filepath = sys.argv[1]
    instance = load_solomon(filepath)

    print(f"\nInstância carregada: {instance.name}")
    print(f"  Clientes  : {instance.n}")
    print(f"  Veículos  : {instance.num_vehicles}")
    print(f"  Capacidade: {instance.vehicle_capacity}")

    data = create_data_model(instance)

    # Gestor de índices
    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]),
        data["num_vehicles"],
        data["depot"],
    )

    
    routing = pywrapcp.RoutingModel(manager)

    # Callback da Distancia
    dist_cb_idx = routing.RegisterTransitCallback(
        lambda fi, ti: distance_callback(fi, ti, manager, data)
    )
    routing.SetArcCostEvaluatorOfAllVehicles(dist_cb_idx)

    # Dimensão da capacidade
    dem_cb_idx = routing.RegisterUnaryTransitCallback(
        lambda fi: demand_callback(fi, manager, data)
    )
    routing.AddDimensionWithVehicleCapacity(
        dem_cb_idx,
        0,
        [data["vehicle_capacity"]] * data["num_vehicles"],
        True,
        "Capacity",
    )

    # Dimensão das janelas de tempo
    time_cb_idx = routing.RegisterTransitCallback(
        lambda fi, ti: time_callback(fi, ti, manager, data)
    )
    horizon = int(instance.depot.due_time) + int(instance.depot.service_time)
    routing.AddDimension(
        time_cb_idx,
        horizon,   
        horizon,   
        False,     
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")

    # Aplica as janelas de tempo a cada nó
    for node, (ready, due) in enumerate(data["time_windows"]):
        idx = manager.NodeToIndex(node)
        time_dim.CumulVar(idx).SetRange(ready, due)

    # Minimiza o tempo de chegada ao depósito no final
    for v in range(data["num_vehicles"]):
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
    params.time_limit.seconds = 30

    print("A resolver... (limite: 30 segundos)\n")
    solution = routing.SolveWithParameters(params)

    if solution:
        print_solution(data, manager, routing, solution, instance.name)
    else:
        print("Nenhuma solução encontrada.")


if __name__ == "__main__":
    main()
