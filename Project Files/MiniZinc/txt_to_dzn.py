import os
from pathlib import Path
from dotenv import load_dotenv
import math
load_dotenv()
SOLOMON_DIRECTORY = Path(__file__).parent.parent / "solomon"
OUTPUT_DIRECTORY = SOLOMON_DIRECTORY / "dzn"
PRECISION_LEVEL = 100

def converter(solomon,number,size,vehicount):
    with open(SOLOMON_DIRECTORY / (solomon + number +"01.txt"),'r') as f:
        lines = f.readlines()
        veh_info = lines[4].split()
        data = [line.split() for line in lines[9:] if line.strip()]
    cust_no, x, y, demand, ready, due, service = [], [], [], [], [], [], []
    depot_row = data[0]
    xdepot = int(depot_row[1])
    ydepot = int(depot_row[2])
    customers = data[1:int(size) + 1]
    #Priority ordering, might just be the most important thing for this god-forsaken model.
    if "R" in solomon:
        customers.sort(key=lambda row: ((int(row[5]) - int(row[4])) * PRECISION_LEVEL) - (math.hypot(int(row[1]) - xdepot, int(row[2]) - ydepot) * PRECISION_LEVEL))
            
    sorted = [depot_row] + customers

    for row in sorted:
        cust_no.append(row[0])
        x.append(row[1])
        y.append(row[2])
        demand.append(str(int(row[3])*PRECISION_LEVEL))
        ready.append(str(int(row[4])*PRECISION_LEVEL))
        due.append(str(int(row[5])*PRECISION_LEVEL))
        service.append(str(int(row[6])*PRECISION_LEVEL))
    with open(OUTPUT_DIRECTORY / (number + solomon + str(size) + ".dzn"), 'w') as dzn:
        dzn.write(f"custcount = {len(cust_no) - 1};\n")
        dzn.write(f"vehicount = {vehicount if vehicount else veh_info[0]};\n")
        dzn.write(f"capacity = {int(veh_info[1])*PRECISION_LEVEL};\n\n")
        dzn.write(f"x = [{', '.join(x)}];\n")
        dzn.write(f"y = [{', '.join(y)}];\n")
        dzn.write(f"demand = [{', '.join(demand)}];\n")
        dzn.write(f"ready = [{', '.join(ready)}];\n")
        dzn.write(f"due = [{', '.join(due)}];\n")
        dzn.write(f"service = [{', '.join(service)}];\n")
def start_converter():
    solomon = input('Insert file name (c/r/rc)\n ->')
    number = input('Insert set (1-3): ? \n ->')
    size = input('Insert ammount of customers you wish to have: \n ->') 
    size = size or 101
    vehicount = input('Insert ammount of vehicles you wish to have: \n ->') 
    vehicount = vehicount or 25
    converter(solomon,number,size,vehicount)
if __name__ == "__main__":
    start_converter()