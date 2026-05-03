import math
from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2

# O codigo roda para 100 clientes + 1 deposito com 25 veiculos, cada um com capacidade de 200 unidades. 
#Para cada cliente há um tempo de serviço de 90 minutos

# Formato: (CUST_NO, X, Y, DEMAND, READY_TIME, DUE_DATE, SERVICE_TIME)

SOLOMON_C101 = [
    #  no   x    y  dem  ready   due  serv
    (  0,  40,  50,   0,    0,  1236,   0),
    (  1,  45,  68,  10,  912,   967,  90),
    (  2,  45,  70,  30,  825,   870,  90),
    (  3,  42,  66,  10,   65,   146,  90),
    (  4,  42,  68,  10,  727,   782,  90),
    (  5,  42,  65,  10,   15,    67,  90),
    (  6,  40,  69,  20,  621,   702,  90),
    (  7,  40,  66,  20,  170,   225,  90),
    (  8,  38,  68,  20,  255,   324,  90),
    (  9,  38,  70,  10,  534,   605,  90),
    ( 10,  35,  66,  10,  357,   410,  90),
    ( 11,  35,  69,  10,  448,   505,  90),
    ( 12,  25,  85,  20,  652,   721,  90),
    ( 13,  22,  75,  30,   30,    92,  90),
    ( 14,  22,  85,  10,  567,   620,  90),
    ( 15,  20,  80,  40,  384,   429,  90),
    ( 16,  20,  85,  40,  475,   528,  90),
    ( 17,  18,  75,  20,   99,   148,  90),
    ( 18,  15,  75,  20,  179,   254,  90),
    ( 19,  15,  80,  10,  278,   345,  90),
    ( 20,  30,  50,  10,   10,    73,  90),
    ( 21,  30,  52,  20,  914,   965,  90),
    ( 22,  28,  52,  20,  812,   883,  90),
    ( 23,  28,  55,  10,  732,   777,  90),
    ( 24,  25,  50,  10,   65,   144,  90),
    ( 25,  25,  52,  40,  169,   224,  90),
    ( 26,  25,  55,  10,  622,   701,  90),
    ( 27,  23,  52,  10,  261,   316,  90),
    ( 28,  23,  55,  20,  546,   593,  90),
    ( 29,  20,  50,  10,  358,   405,  90),
    ( 30,  20,  55,  10,  449,   504,  90),
    ( 31,  10,  35,  20,  200,   237,  90),
    ( 32,  10,  40,  30,   31,   100,  90),
    ( 33,   8,  40,  40,   87,   158,  90),
    ( 34,   8,  45,  20,  751,   816,  90),
    ( 35,   5,  35,  10,  283,   344,  90),
    ( 36,   5,  45,  10,  665,   716,  90),
    ( 37,   2,  40,  20,  383,   434,  90),
    ( 38,   0,  40,  30,  479,   522,  90),
    ( 39,   0,  45,  20,  567,   624,  90),
    ( 40,  35,  30,  10,  264,   321,  90),
    ( 41,  35,  32,  10,  166,   235,  90),
    ( 42,  33,  32,  20,   68,   149,  90),
    ( 43,  33,  35,  10,   16,    80,  90),
    ( 44,  32,  30,  10,  359,   412,  90),
    ( 45,  30,  30,  10,  541,   600,  90),
    ( 46,  30,  32,  30,  448,   509,  90),
    ( 47,  30,  35,  10, 1054,  1127,  90),
    ( 48,  28,  30,  10,  632,   693,  90),
    ( 49,  28,  35,  10, 1001,  1066,  90),
    ( 50,  26,  32,  10,  815,   880,  90),
    ( 51,  25,  30,  10,  725,   786,  90),
    ( 52,  25,  35,  10,  912,   969,  90),
    ( 53,  44,   5,  20,  286,   347,  90),
    ( 54,  42,  10,  40,  186,   257,  90),
    ( 55,  42,  15,  10,   95,   158,  90),
    ( 56,  40,   5,  30,  385,   436,  90),
    ( 57,  40,  15,  40,   35,    87,  90),
    ( 58,  38,   5,  30,  471,   534,  90),
    ( 59,  38,  15,  10,  651,   740,  90),
    ( 60,  35,   5,  20,  562,   629,  90),
    ( 61,  50,  30,  10,  531,   610,  90),
    ( 62,  50,  35,  20,  262,   317,  90),
    ( 63,  50,  40,  50,  171,   218,  90),
    ( 64,  48,  30,  10,  632,   693,  90),
    ( 65,  48,  40,  10,   76,   129,  90),
    ( 66,  47,  35,  10,  826,   875,  90),
    ( 67,  47,  40,  10,   12,    77,  90),
    ( 68,  45,  30,  10,  734,   777,  90),
    ( 69,  45,  35,  10,  916,   969,  90),
    ( 70,  95,  30,  30,  387,   456,  90),
    ( 71,  95,  35,  20,  293,   360,  90),
    ( 72,  53,  30,  10,  450,   505,  90),
    ( 73,  92,  30,  10,  478,   551,  90),
    ( 74,  53,  35,  50,  353,   412,  90),
    ( 75,  45,  65,  20,  997,  1068,  90),
    ( 76,  90,  35,  10,  203,   260,  90),
    ( 77,  88,  30,  10,  574,   643,  90),
    ( 78,  88,  35,  20,  109,   170,  90),
    ( 79,  87,  30,  10,  668,   731,  90),
    ( 80,  85,  25,  10,  769,   820,  90),
    ( 81,  85,  35,  30,   47,   124,  90),
    ( 82,  75,  55,  20,  369,   420,  90),
    ( 83,  72,  55,  10,  265,   338,  90),
    ( 84,  70,  58,  20,  458,   523,  90),
    ( 85,  68,  60,  30,  555,   612,  90),
    ( 86,  66,  55,  10,  173,   238,  90),
    ( 87,  65,  55,  20,   85,   144,  90),
    ( 88,  65,  60,  30,  645,   708,  90),
    ( 89,  63,  58,  10,  737,   802,  90),
    ( 90,  60,  55,  10,   20,    84,  90),
    ( 91,  60,  60,  10,  836,   889,  90),
    ( 92,  67,  85,  20,  368,   441,  90),
    ( 93,  65,  85,  40,  475,   518,  90),
    ( 94,  65,  82,  10,  285,   336,  90),
    ( 95,  62,  80,  30,  196,   239,  90),
    ( 96,  60,  80,  10,   95,   156,  90),
    ( 97,  60,  85,  30,  561,   622,  90),
    ( 98,  58,  75,  20,   30,    84,  90),
    ( 99,  55,  80,  10,  743,   820,  90),
    (100,  55,  85,  20,  647,   726,  90),
]
 
 
def create_data_model():
    """Cria o modelo de dados"""
    n = len(SOLOMON_C101)
 
    
    coordenadas       = [(row[1], row[2]) for row in SOLOMON_C101]
    demands      = [row[3] for row in SOLOMON_C101]
    time_windows = [(row[4], row[5]) for row in SOLOMON_C101]
    service_time = [row[6] for row in SOLOMON_C101]
 
    # Usa a Matriz de distâncias euclidianas 
  
    distance_matrix = []
    for i in range(n):
        row = []
        for j in range(n):
            dx = coordenadas[i][0] - coordenadas[j][0]
            dy = coordenadas[i][1] - coordenadas[j][1]
            row.append(int(math.sqrt(dx*dx + dy*dy)))
        distance_matrix.append(row)
 
    return {
        "distance_matrix": distance_matrix,
        "time_windows":    time_windows,
        "service_time":    service_time,
        "demands":         demands,
        "vehicle_capacity": 200,
        "num_vehicles":    25,
        "depot":           0,
    }
 
 
# ----------
# CALLBACKS
# ----------
 
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
 
 
def print_solution(data, manager, routing, solution):
    time_dim = routing.GetDimensionOrDie("Time")
 
    total_dist  = 0
    total_load  = 0
 
    print(f"\n{'='*70}")
    print(f"  SOLUÇÃO - Solomon C101 | Distância total: "
          f"{fmt_dist(solution.ObjectiveValue())}")
    print(f"{'='*70}\n")
 
    for v in range(data["num_vehicles"]):
        idx = routing.Start(v)
 
        # Ignora os veículos sem clientes
        if routing.IsEnd(solution.Value(routing.NextVar(idx))):
            continue
 
        route_dist = 0
        route_load = 0
        stops = []
 
        while not routing.IsEnd(idx):
            node    = manager.IndexToNode(idx)
            t_var   = time_dim.CumulVar(idx)
            t_arr   = solution.Min(t_var)
            tw      = data["time_windows"][node]
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
 
 

# FUNÇÃO PRINCIPAL

 
def main():
    print("\nA carregar Solomon C101 (101 nós, 25 veículos)...")
    data = create_data_model()
 
    # Gestor de índices
    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]),
        data["num_vehicles"],
        data["depot"],
    )
 
    # Modelo
    routing = pywrapcp.RoutingModel(manager)
 
    #Callback de distância
    dist_cb_idx = routing.RegisterTransitCallback(
        lambda fi, ti: distance_callback(fi, ti, manager, data)
    )
    routing.SetArcCostEvaluatorOfAllVehicles(dist_cb_idx)
 
    #Tamanho da capacidade
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
 
    # janelas de tempo
    time_cb_idx = routing.RegisterTransitCallback(
        lambda fi, ti: time_callback(fi, ti, manager, data)
    )
    horizon = 1236 + 90  
    routing.AddDimension(
        time_cb_idx,
        horizon,   
        horizon,   
        False,     
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")
 
    #Aplica as janelas de tempo a cada nó
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
        print_solution(data, manager, routing, solution)
    else:
        print("Nenhuma solução encontrada.")
 
 
if __name__ == "__main__":
    main()