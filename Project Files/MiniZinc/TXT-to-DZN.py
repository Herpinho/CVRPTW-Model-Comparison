import os
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()
SOLOMON_DIRECTORY = Path(__file__).parent.parent / "solomon"
OUTPUT_DIRECTORY = SOLOMON_DIRECTORY / "dzn"
PRECISION_LEVEL = int(os.getenv("PRECISION_LEVEL"))

def converter(solomon):
    with open(SOLOMON_DIRECTORY / solomon,'r') as f:
        lines = f.readlines()
        veh_info = lines[4].split()
        data = [line.split() for line in lines[9:] if line.strip()]
    cust_no, x, y, demand, ready, due, service = [], [], [], [], [], [], []
    for row in data:
        cust_no.append(row[0])
        x.append(row[1])
        y.append(row[2])
        demand.append(str(int(row[3])*PRECISION_LEVEL))
        ready.append(str(int(row[4])*PRECISION_LEVEL))
        due.append(str(int(row[5])*PRECISION_LEVEL))
        service.append(str(int(row[6])*PRECISION_LEVEL))
    with open(OUTPUT_DIRECTORY / solomon.replace(".txt", ".dzn"), 'w') as dzn:
        dzn.write(f"custcount = {len(cust_no) - 1};\n")
        dzn.write(f"vehicount = {veh_info[0]};\n")
        dzn.write(f"capacity = {int(veh_info[1])*PRECISION_LEVEL};\n\n")
        dzn.write(f"x = [{', '.join(x)}];\n")
        dzn.write(f"y = [{', '.join(y)}];\n")
        dzn.write(f"demand = [{', '.join(demand)}];\n")
        dzn.write(f"ready = [{', '.join(ready)}];\n")
        dzn.write(f"due = [{', '.join(due)}];\n")
        dzn.write(f"service = [{', '.join(service)}];\n")

if __name__ == "__main__":
    solomon = input('Insert file name (c/r/rc)\n ->') + "101.txt"
    converter(solomon)