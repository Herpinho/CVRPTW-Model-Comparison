import sys
import json
import math
import re


def load_dzn(filename):
    with open(f'Project Files/solomon/dzn/{filename}.dzn', 'r') as f:
        code = f.read()
        data = {}
        pattern = r"(\w+)\s*=\s*\[(.*?)\];"
        for match in re.finditer(pattern, code, re.DOTALL):
            var_name = match.group(1)
            raw_values = match.group(2)
            data[var_name] = [int(v.strip()) for v in raw_values.split(',')]
            num_nodes= len(data['x'])
        nodes = []
        
    for i in range(num_nodes):
        node = Node(
            id = i,
            x = data['x'][i],
            y = data['y'][i],
            demand = data['demand'][i],
            ready = data['ready'][i],
            due = data['due'][i],
            service = data['service'][i]
        )
        nodes.append(node)
    depot = nodes[0]
    customers = nodes[1:]
    return Instance(name=filename, depot=depot, customers=customers)
class Node:
    def __init__(self, id, x, y, demand, ready, due, service):
        self.id = id
        self.x = x
        self.y = y
        self.demand = demand
        self.ready = ready
        self.due = due
        self.service = service
    def __repr__(self):
        return f"Node(id={self.id}, x={self.x}, y={self.y})"
class Instance:
    def __init__(self, name, depot, customers):
        self.name = name
        self.depot = depot
        self.customers = customers
        self.n = len(customers)
    def __repr__(self):
        return f"Instance(name={self.name}, clients={self.n})"


# ── Paleta de cores para as rotas ─────────────────────────────────────────────

COLORS = [
    "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
    "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
    "#AEC7E8", "#FFBB78", "#98DF8A", "#FF9896", "#C5B0D5",
    "#C49C94", "#F7B6D2", "#C7C7C7", "#DBDB8D", "#9EDAE5",
    "#393B79", "#637939", "#8C6D31", "#843C39", "#7B4173",
]

def get_color(k: int) -> str:
    return COLORS[k % len(COLORS)]


# ── Construir dados Plotly ────────────────────────────────────────────────────

def build_plotly_data(instance, result: dict) -> dict:
    depot    = instance.depot
    clients  = {c.id: c for c in instance.customers}
    node_map = {0: depot, **clients}

    traces   = []
    route_info = []

    # ── Traços das rotas ──────────────────────────────────────────────────────
    for r in result["routes"]:
        route   = r["route"]
        color   = get_color(r["vehicle"])
        xs, ys  = [], []
        for node in route:
            c = node_map[node]
            xs.append(c.x)
            ys.append(c.y)

        traces.append({
            "type":  "scatter",
            "mode":  "lines",
            "x":     xs,
            "y":     ys,
            "name":  f"Veículo {r['vehicle']}",
            "line":  {"color": color, "width": 2},
            "hoverinfo": "skip",
            "legendgroup": f"v{r['vehicle']}",
        })

        # Setas de direcção a meio da rota
        for i in range(len(route) - 1):
            a = node_map[route[i]]
            b = node_map[route[i+1]]
            mx = (a.x + b.x) / 2
            my = (a.y + b.y) / 2
            dx = b.x - a.x
            dy = b.y - a.y
            traces.append({
                "type": "scatter", "mode": "markers",
                "x": [mx], "y": [my],
                "marker": {
                    "symbol": "arrow", "size": 10,
                    "color":  color,
                    "angle":  math.degrees(math.atan2(dy, dx)) - 90,
                    "line":   {"width": 0}
                },
                "showlegend": False,
                "hoverinfo":  "skip",
                "legendgroup": f"v{r['vehicle']}",
            })

        route_info.append({
            "vehicle":  r["vehicle"],
            "route":    " → ".join(str(n) for n in route),
            "load":     r["load"],
            "distance": round(r["distance"], 2),
            "color":    color,
        })

    # ── Clientes ──────────────────────────────────────────────────────────────
    # Determinar a qual veículo pertence cada cliente
    client_vehicle = {}
    for r in result["routes"]:
        for node in r["route"]:
            if node != 0:
                client_vehicle[node] = r["vehicle"]

    cx = [c.x for c in instance.customers]
    cy = [c.y for c in instance.customers]
    ctext = []
    ccolors = []
    for c in instance.customers:
        v = client_vehicle.get(c.id, -1)
        col = get_color(v) if v >= 0 else "#AAAAAA"
        ccolors.append(col)
        ctext.append(
            f"<b>Cliente {c.id}</b><br>"
            f"Pos: ({c.x}, {c.y})<br>"
            f"Procura: {c.demand}<br>"
            f"Janela: [{c.ready}, {c.due}]<br>"
            f"Serviço: {c.service}<br>"
            f"Veículo: {v if v >= 0 else 'N/A'}"
        )

    traces.append({
        "type": "scatter", "mode": "markers+text",
        "x": cx, "y": cy,
        "name": "Clientes",
        "marker": {
            "size": 10, "color": ccolors,
            "line": {"color": "white", "width": 1.5}
        },
        "text":     [str(c.id) for c in instance.customers],
        "textposition": "top center",
        "textfont": {"size": 7, "color": "#333"},
        "hovertext": ctext,
        "hoverinfo": "text",
        "showlegend": True,
    })

    # ── Depósito ──────────────────────────────────────────────────────────────
    traces.append({
        "type": "scatter", "mode": "markers+text",
        "x": [depot.x], "y": [depot.y],
        "name": "Depósito",
        "marker": {
            "size": 18, "color": "#1F4E79",
            "symbol": "star",
            "line": {"color": "white", "width": 2}
        },
        "text": ["D"], "textposition": "top center",
        "textfont": {"size": 10, "color": "white"},
        "hovertext": [f"<b>Depósito</b><br>Pos: ({depot.x}, {depot.y})<br>"
                      f"Janela: [{depot.ready}, {depot.due}]"],
        "hoverinfo": "text",
        "showlegend": True,
    })

    return {"traces": traces, "route_info": route_info}


# ── Gerar HTML ────────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CVRPTW — {name}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f4f8; color: #222; }}
  header {{
    background: #1F4E79; color: white; padding: 16px 24px;
    display: flex; align-items: center; gap: 16px;
  }}
  header h1 {{ font-size: 1.3rem; font-weight: 700; }}
  header span {{ font-size: 0.9rem; opacity: 0.8; }}
  .container {{ display: flex; height: calc(100vh - 60px); }}
  #chart {{ flex: 1; }}
  .sidebar {{
    width: 280px; background: white; overflow-y: auto;
    border-left: 1px solid #dde3ea; padding: 16px;
  }}
  .summary {{
    background: #EBF3FB; border-radius: 8px; padding: 12px; margin-bottom: 16px;
  }}
  .summary h3 {{ color: #1F4E79; font-size: 0.85rem; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .summary-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
  .metric {{ text-align: center; }}
  .metric .val {{ font-size: 1.4rem; font-weight: 700; color: #1F4E79; }}
  .metric .lbl {{ font-size: 0.7rem; color: #666; }}
  .routes-title {{ font-size: 0.85rem; font-weight: 700; color: #1F4E79; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }}
  .route-card {{
    border-radius: 6px; padding: 10px; margin-bottom: 8px;
    border-left: 4px solid; background: #fafafa;
    font-size: 0.78rem; cursor: pointer; transition: background 0.15s;
  }}
  .route-card:hover {{ background: #f0f4f8; }}
  .route-card .rhead {{ display: flex; justify-content: space-between; margin-bottom: 4px; }}
  .route-card .rnum {{ font-weight: 700; }}
  .route-card .rpath {{ color: #555; word-break: break-all; line-height: 1.4; margin-top: 4px; }}
  .ref-box {{
    background: #FFF8E7; border: 1px solid #F0C040; border-radius: 6px;
    padding: 10px; margin-bottom: 16px; font-size: 0.78rem;
  }}
  .ref-box h3 {{ color: #7A5200; font-size: 0.8rem; margin-bottom: 6px; }}
  .gap-good {{ color: #2CA02C; font-weight: 700; }}
  .gap-ok   {{ color: #FF7F0E; font-weight: 700; }}
  .gap-bad  {{ color: #D62728; font-weight: 700; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>CVRPTW — Instância {name}</h1>
    <span>Gurobi MIP · Laboratório de Projeto 2025/2026 · UAL</span>
  </div>
</header>
<div class="container">
  <div id="chart"></div>
  <div class="sidebar">
    <div class="summary">
      <h3>Resumo da Solução</h3>
      <div class="summary-grid">
        <div class="metric"><div class="val">{num_vehicles}</div><div class="lbl">Veículos</div></div>
        <div class="metric"><div class="val">{num_clients}</div><div class="lbl">Clientes</div></div>
        <div class="metric"><div class="val">{total_dist}</div><div class="lbl">Distância</div></div>
        <div class="metric"><div class="val">{runtime}s</div><div class="lbl">Tempo</div></div>
      </div>
    </div>
    <div class="routes-title">Rotas ({num_vehicles})</div>
    {route_cards}
  </div>
</div>
<script>
const traces = {traces_json};
const layout = {{
  margin: {{ t: 20, l: 40, r: 20, b: 40 }},
  paper_bgcolor: "#f0f4f8",
  plot_bgcolor: "#ffffff",
  xaxis: {{ title: "X", gridcolor: "#e8edf2", zeroline: false }},
  yaxis: {{ title: "Y", gridcolor: "#e8edf2", zeroline: false, scaleanchor: "x" }},
  legend: {{ orientation: "v", x: 1.01, y: 1, bgcolor: "rgba(0,0,0,0)" }},
  hovermode: "closest",
  font: {{ family: "Segoe UI, Arial, sans-serif" }},
}};
const config = {{ responsive: true, displayModeBar: true,
  modeBarButtonsToRemove: ["lasso2d", "select2d"] }};
Plotly.newPlot("chart", traces, layout, config);
</script>
</body>
</html>"""


def build_route_cards(route_info):
    cards = ""
    for r in route_info:
        cards += f"""
    <div class="route-card" style="border-left-color:{r['color']}">
      <div class="rhead">
        <span class="rnum" style="color:{r['color']}">Veículo {r['vehicle']}</span>
        <span>Carga: {r['load']:.0f} | {r['distance']} km</span>
      </div>
      <div class="rpath">{r['route']}</div>
    </div>"""
    return cards


def generate_html(instance, result: dict, output_path: str):
    data = build_plotly_data(instance, result)

    html = HTML_TEMPLATE.format(
        name         = instance.name,
        num_vehicles = result["num_vehicles"],
        num_clients  = instance.n,
        total_dist   = f"{result['obj_value']:.2f}" if result["obj_value"] else "N/A",
        runtime      = f"{result['runtime'].total_seconds()}",
        route_cards  = build_route_cards(data["route_info"]),
        traces_json  = json.dumps(data["traces"]),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Visualização guardada em: {output_path}")


# ── Ponto de entrada ──────────────────────────────────────────────────────────
optimize=True
if __name__ == "__main__":
    from Minizinc import start_minizinc
    filename = input("Insira o nome do ficheiro: (c25/r25/rc25)")
    option = input("optimize(1) or satisfy(2)?")
    if option== "1":
        optimize=True
    elif option == "2":
        optimize=False
    else: sys.exit()
    instance = load_dzn(filename)
    print(instance)

    print(f"A resolver {instance.name}...")
    result = start_minizinc(uinput=filename,optimize=optimize)
    if result["obj_value"] is None:
        print("Nenhuma solução encontrada — não é possível visualizar.")
        sys.exit(1)

    output = filename + "_routes.html"
    generate_html(instance, result, output)
    print(f"  Abre o ficheiro '{output}' no browser!")
