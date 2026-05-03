import minizinc, threading, time, os
from datetime import timedelta
from pathlib import Path

def timer(done):
    start = time.time()
    while not done.wait(timeout=1):
        print(f"{int(time.time() - start)}s elapsed.", end="\r")
def solve_cvrptw(mzn_file, dzn_file,size):
    if not mzn_path.exists() or not dzn_path.exists():
        print(f"Error: Could not find files.\nMZN: {mzn_path}\nDZN: {dzn_path}")
        return
    model = minizinc.Model(mzn_file)
    model.add_file(dzn_file)
#   if int(size) < 50:
#        model.add_string("""
#        solve :: seq_search([
#            int_search(array1d(successor), first_fail, indomain_min),
 #           int_search(arrival, smallest, indomain_min) 
#        ])
#          :: restart_luby(250)
#          minimize score;
#        """)
 #   else:
  #      model.add_string("solve minimize score;") 
    solver = minizinc.Solver.lookup("chuffed")
    instance = minizinc.Instance(solver, model)
    done = threading.Event()
    threading.Thread(target=timer, args = (done, ), daemon=True).start()

    result = instance.solve(timeout=timedelta(seconds = 1800))
    done.set()
    if result.solution is not None:
        print("\nSuccess!")
        used_vehicles = 0
        for v_route in result.solution.successor:

            if v_route[0] != 1: 
                used_vehicles += 1
        for v in range(len(result.solution.successor)):
            raw_score = result.objective
            actual_score = raw_score - (used_vehicles * 20000)
            
           
            successors = result.solution.successor[v]

            if successors[0] != 1:
                route = []
                curr = successors[0]
                while curr != 1:
                    route.append(curr)
                    curr = successors[curr - 1]
            
                print(f"Vehicle {v+1}: Depot -> {' -> '.join(map(str, route))} -> Depot")
        print(f"Final Score: {actual_score}\n")
    else:
        print("\nNo solution found.")

if __name__ == "__main__":
    mzn_file = (input("Insert the model you wish to use (BigM/PH/PH): \n ->"))
    mzn_file = mzn_file + '.mzn' if mzn_file else 'bigm.mzn'
    dzn_file = input("Insert the Solomon file to use : \n -> ") + ".dzn" 
    dzn_path = Path(__file__).parent.parent / "solomon" / "dzn" / dzn_file
    mzn_path = Path(__file__).parent / mzn_file
    solve_cvrptw(mzn_path,dzn_path,size= "".join(filter(str.isdigit, dzn_file)))
