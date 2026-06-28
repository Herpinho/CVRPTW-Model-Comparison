import minizinc, threading, time, os
from datetime import timedelta
from pathlib import Path
runtime = 0
def timer(done):
    start = time.time()
    while not done.wait(timeout=1):
        print(f"{int(time.time() - start)}s elapsed.", end="\r")
    runtime = time.time() - start
    return runtime
def start_minizinc(uinput,optimize=True):
    mzn_file = 'BigM'
    mzn_file = mzn_file + '.mzn' if mzn_file else 'bigm.mzn'
    dzn_file = input("Insert the Solomon file to use : \n -> ") + ".dzn" if not uinput else uinput + ".dzn"
    dzn_path = Path(__file__).parent.parent / "solomon" / "dzn" / dzn_file
    mzn_path = Path(__file__).parent / mzn_file
    return solve_cvrptw(mzn_path,dzn_path,optimize)
    
def solve_cvrptw(mzn_file, dzn_file,optimize=True):
    routes = []
    if not mzn_file.exists() or not dzn_file.exists():
        print(f"Error: Could not find files.\nMZN: {mzn_file}\nDZN: {dzn_file}")
        return
    model = minizinc.Model(mzn_file)
    model.add_file(dzn_file)
    if optimize:
        model.add_string("solve minimize score;")
    else:
        model.add_string("solve satisfy;")
    solver = minizinc.Solver.lookup("chuffed")
    instance = minizinc.Instance(solver, model)
    done = threading.Event()
    threading.Thread(target=timer, args = (done, ), daemon=True).start()

    result = instance.solve(timeout=timedelta(seconds = 300))
    done.set()
    if result.solution is not None:
        print("\nSuccess!")
        used_vehicles = 0
        for v_route in result.solution.successor:

            if v_route[0] != 1: 
                used_vehicles += 1
        for v in range(len(result.solution.successor)):
            raw_score = result.objective
            actual_score = sum(result.solution.distance)/1000
            
           
            successors = result.solution.successor[v]

            if successors[0] != 1:
                route = []
                
                curr = successors[0]
                while curr != 1:
                    route.append(curr)
                    curr = successors[curr - 1]
                    
            
                print(f"Vehicle {v+1}: Depot -> {' -> '.join(map(str, route))} -> Depot")
                print(route)
                routes.append({
                "vehicle": v,
                "route": [0] + [route[i]-1 for i in range(len(route))] + [0] ,
                "load": max(result.solution.load[v]),
                "distance": result.solution.distance[v]
                })
        print(f"Final Score: {actual_score}\n")
        print(f"Score: {sum(result.solution.distance)}")
    else:
        print("No result found.")
        return {"obj_value": None}
        
    
    return {
        "obj_value": actual_score,
        "num_vehicles": used_vehicles,
        "runtime" : result.statistics.get("time"),
        "routes" : routes
    }

if __name__ == "__main__":
    start_minizinc(uinput=None)