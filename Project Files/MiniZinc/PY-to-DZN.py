
import os
from pathlib import Path
import sys
from dotenv import load_dotenv
import math
import importlib
load_dotenv()
speed = 83 #meters / minute (idk)
SOLOMON_DIRECTORY = Path(__file__).parent.parent / "solomon"
OUTPUT_DIRECTORY = SOLOMON_DIRECTORY / "dzn"
PRECISION_LEVEL = int(os.getenv("PRECISION_LEVEL") if os.getenv("PRECISION_LEVEL") else 10000)
def cartesian_coords(lat, lon, latdepot, londepot): 
    r = 6371000
    x = math.radians(lon - londepot) * r * math.cos(math.radians(londepot))
    y = math.radians(lat - latdepot) * r
    return x, y
def converter(filename):
    sys.path.append(str(Path(__file__).parent.parent / "solomon"))
    c = importlib.import_module(filename) 
    latdepot = c.DEPOSITO["lat"]
    londepot = c.DEPOSITO["lon"]

    cust_no, x, y, demand, ready, due, service = [], [], [], [], [], [], []
    cust_no.append(str(int(c.DEPOSITO["id"])))
    x.append(str(0))
    y.append(str(0))
    demand.append(str(int(c.DEPOSITO["demand"])))
    ready.append(str(int(c.DEPOSITO["ready_time"])*speed))
    due.append(str(int(c.DEPOSITO["due_time"])*speed))
    service.append(str(int(c.DEPOSITO["service_time"])*speed))
    #priority ordering with stackoverflow's help because god forbid it would work on 2 different files
    c.CLIENTES.sort(key=lambda cliente: (
    (cliente["due_time"] - cliente["ready_time"]) - 
    math.hypot(*cartesian_coords(cliente["lat"], cliente["lon"], latdepot, londepot))
    ))
    for customer in range(len(c.CLIENTES)):
        x_cord,y_cord = cartesian_coords(c.CLIENTES[customer]["lat"],c.CLIENTES[customer]["lon"],latdepot,londepot)
        cust_no.append(str(int(c.CLIENTES[customer]["id"]+1)))
        x.append(str(int(x_cord)))
        y.append(str(int(y_cord)))
        demand.append(str(int(c.CLIENTES[customer]["demand"])))
        ready.append(str(int(c.CLIENTES[customer]["ready_time"])*speed))
        due.append(str(int(c.CLIENTES[customer]["due_time"])*speed))
        service.append(str(int(c.CLIENTES[customer]["service_time"])*speed))
        capacity = str(int(c.VEHICLE_CAPACITY))
        vehicount = str(int(c.NUM_VEHICLES))
    with open(OUTPUT_DIRECTORY / ( filename + ".dzn"), 'w') as dzn:
        dzn.write(f"custcount = {len(cust_no) - 1};\n")
        dzn.write(f"vehicount = {vehicount};\n")
        dzn.write(f"capacity = {capacity};\n\n")
        dzn.write(f"x = [{', '.join(x)}];\n")
        dzn.write(f"y = [{', '.join(y)}];\n")
        dzn.write(f"demand = [{', '.join(demand)}];\n")
        dzn.write(f"ready = [{', '.join(ready)}];\n")
        dzn.write(f"due = [{', '.join(due)}];\n")
        dzn.write(f"service = [{', '.join(service)}];\n")
if __name__ == "__main__":
    filename = input('Insert file name\n ->')
    clean_name = filename.strip().replace(".py", "")
    converter(clean_name)