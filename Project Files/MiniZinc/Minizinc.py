import minizinc, threading, time, os
from datetime import timedelta
from pathlib import Path

def timer(done):
    start = time.time()
    while not done.wait(timeout=1):
        print(f"{int(time.time() - start)}s elapsed.", end="\r")
def solve_cvrptw(mzn_file, dzn_file):
    if not mzn_path.exists() or not dzn_path.exists():
        print(f"Error: Could not find files.\nMZN: {mzn_path}\nDZN: {dzn_path}")
        return
    model = minizinc.Model(mzn_file)
    model.add_file(dzn_file)
    solver = minizinc.Solver.lookup("chuffed")
    instance = minizinc.Instance(solver, model)
    done = threading.Event()
    threading.Thread(target=timer, args = (done, ), daemon=True).start()

    result = instance.solve(timeout=timedelta(seconds = 300))
    if result:
        best_result = result[-1]
        print(f"Best Score after 5 mins: {best_result.objective}")
    done.set()
    if result.solution is not None:
        print("\nSuccess!")
        for v in range(len(result.solution.successor)):
            successors = result.solution.successor[v]
            if successors[0] != 1:
                route = []
                curr = successors[0]
                while curr != 1:
                    route.append(curr)
                    curr = successors[curr - 1]
            
            print(f"Vehicle {v+1}: Depot -> {' -> '.join(map(str, route))} -> Depot")
    else:
        print("\nNo solution found.")

if __name__ == "__main__":
    mzn_file = input("Insert the model you wish to use (BigM/PH/PH): \n ->") + ".mzn"
    dzn_file = input("Insert the Solomon file to use (c/r/rc): \n -> ") + "101.dzn"
    dzn_path = Path(__file__).parent.parent / "solomon" / "dzn" / dzn_file
    mzn_path = Path(__file__).parent / mzn_file
    solve_cvrptw(mzn_path,dzn_path)
