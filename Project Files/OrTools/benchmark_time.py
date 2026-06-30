"""
usar: python benchmark_time.py in/R201.txt
"""

import sys
import time
import importlib.util
import os

#  Carregar solver.py 
def load_solver():
    for name in ("solver.py"):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
        if os.path.exists(path):
            spec = importlib.util.spec_from_file_location("solver", path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            print(f"  Solver carregado: {name}\n")
            return mod
    raise FileNotFoundError("Não encontrei solver.py na mesma pasta.")

solver = load_solver()
load_solomon      = solver.load_solomon
solve_cvrptw      = solver.solve_cvrptw
SOLOMON_REFERENCE = solver.SOLOMON_REFERENCE

# Configuração
TIME_LIMITS = [
    300,    # 5 min
    600,    # 10 min
    900,    # 15 min
    1200,   # 20 min
    1800,   # 30 min
    3600,   # 1 hora
    7200,   # 2 horas
    10800,  # 3 horas
    21600,  # 6 horas
    43200,  # 12 horas (overnight)
]
MIP_GAP = 0.001  # gap muito baixo para não parar cedo

# Correr benchmark para uma instância 
def benchmark_instance(filepath: str):
    instance = load_solomon(filepath)
    ref       = SOLOMON_REFERENCE.get(instance.name.upper())
    ref_dist  = ref[1] if ref else None
    ref_veh   = ref[0] if ref else None

    print("=" * 65)
    print(f"  BENCHMARK DE CONVERGÊNCIA — {instance.name}")
    print(f"  {instance.n} clientes | Capacidade: {instance.vehicle_capacity}")
    if ref:
        print(f"  Referência Solomon: {ref_dist} dist. | {ref_veh} veículos")
    
    total_time_hours = sum(TIME_LIMITS) / 3600
    print(f"\n  ⚠ Tempo estimado total: {total_time_hours:.1f} horas")
    print(f"  Intervalos: ", end="")
    for i, tl in enumerate(TIME_LIMITS):
        if tl < 3600:
            lbl = f"{tl//60}min"
        else:
            lbl = f"{tl//3600}h"
        print(lbl, end="" if i == len(TIME_LIMITS)-1 else ", ")
    print()
    
    print("=" * 65)
    print(f"  {'Limite':>8} | {'Distância':>10} | {'Gap Solomon':>12} | {'MIP Gap':>8} | {'Veículos':>9} | {'Tempo real':>10}")
    print(f"  {'-'*8}-+-{'-'*10}-+-{'-'*12}-+-{'-'*8}-+-{'-'*9}-+-{'-'*10}")

    results = []

    for tl in TIME_LIMITS:
        if tl < 3600:
            label = f"{tl//60} min"
        else:
            hours = tl // 3600
            label = f"{hours}h" if tl % 3600 == 0 else f"{hours}h{(tl % 3600)//60}m"
        
        print(f"  {label:>8} | ", end="", flush=True)

        result = solve_cvrptw(instance, time_limit=float(tl),
                              mip_gap=MIP_GAP, verbose=False)

        if result["obj_value"] is None:
            print("Sem solução")
            results.append(None)
            continue

        dist     = result["obj_value"]
        mip_gap  = result["mip_gap"] * 100
        n_veh    = result["num_vehicles"]
        runtime  = result["runtime"]

        if ref_dist:
            sol_gap     = (dist - ref_dist) / ref_dist * 100
            sol_gap_str = f"{sol_gap:+.2f}%"
        else:
            sol_gap_str = "N/A"

        # Marcar se atingiu ótimo antes do tempo
        status_mark = " ✓" if result["status"] == "OPTIMAL" else ""  

        # Formatar tempo real de execução
        if runtime < 3600:
            runtime_str = f"{runtime:.1f}s"
        else:
            h = int(runtime // 3600)
            m = int((runtime % 3600) // 60)
            s = int(runtime % 60)
            runtime_str = f"{h}h{m:02d}m{s:02d}s"

        print(f"{dist:>10.2f} | {sol_gap_str:>12} | {mip_gap:>7.2f}% | {n_veh:>9} | {runtime_str:>10}{status_mark}")

        results.append({
            "time_limit": tl,
            "distance":   dist,
            "sol_gap":    (dist - ref_dist) / ref_dist * 100 if ref_dist else None,
            "mip_gap":    mip_gap,
            "num_veh":    n_veh,
            "runtime":    runtime,
            "optimal":    result["status"] == "OPTIMAL",
        })

        # Quando chegamos ao otimo não e necessário continuar
        if result["status"] == "OPTIMAL":
            print(f"\n  ✓ Ótimo global encontrado aos {label}! A parar benchmark.")
            break

    # Resumo final 
    valid = [r for r in results if r is not None]
    if len(valid) >= 2:
        first = valid[0]
        last  = valid[-1]
        delta_dist = first["distance"] - last["distance"]
        delta_gap  = first["mip_gap"]  - last["mip_gap"]
        
        last_tl = TIME_LIMITS[len(valid)-1]
        if last_tl < 3600:
            last_label = f"{last_tl//60} min"
        else:
            hours = last_tl // 3600
            last_label = f"{hours}h"
        
        print()
        print(f"  Melhoria total (5 min → {last_label}):")
        print(f"    Distância:  {first['distance']:.2f} → {last['distance']:.2f}  ({'-' if delta_dist >= 0 else '+'}{abs(delta_dist):.2f})")
        print(f"    MIP Gap:    {first['mip_gap']:.2f}% → {last['mip_gap']:.2f}%  (-{delta_gap:.2f}%)")

    print("=" * 65)
    print()
    return results


#  Ponto de entrada 
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python benchmark_time.py <instancia> [<instancia2> ...]")
        print("Exemplo: python benchmark_time.py solomon/R201.txt solomon/RC201.txt")
        sys.exit(1)

    total_start = time.time()
    all_results = {}

    for filepath in sys.argv[1:]:
        try:
            r = benchmark_instance(filepath)
            all_results[filepath] = r
        except FileNotFoundError:
            print(f"  ⚠ Ficheiro não encontrado: {filepath}")
        except Exception as e:
            print(f"  ⚠ Erro em {filepath}: {e}")

    total_elapsed = time.time() - total_start
    print(f"\n  Tempo total do benchmark: {total_elapsed/60:.1f} min")
