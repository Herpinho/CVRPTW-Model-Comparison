"""
Usar:
    python visualize_routes.py solomon/C101.txt
"""

import sys
import json
import math
from BigM import load_solomon, solve_cvrptw

# Paleta de cores para as rotas 
COLORS = [
    "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
    "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
    "#AEC7E8", "#FFBB78", "#98DF8A", "#FF9896", "#C5B0D5",
    "#C49C94", "#F7B6D2", "#C7C7C7", "#DBDB8D", "#9EDAE5",
    "#393B79", "#637939", "#8C6D31", "#843C39", "#7B4173",
]

def get_color(k: int) -> str:
    return COLORS[k % len(COLORS)]


# Construir dados Plotly 

def build_plotly_data(instance, result: dict) -> dict:
    depot    = instance.depot
    clients  = {c.id: c for c in instance.customers}
    node_map = {0: depot, **clients}

    traces   = []
    route_info = []

    #  Traços das rotas 
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

    # Clientes 
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
            f"Janela: [{c.ready_time}, {c.due_time}]<br>"
            f"Serviço: {c.service_time}<br>"
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

    # Depósito 
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
                      f"Janela: [{depot.ready_time}, {depot.due_time}]"],
        "hoverinfo": "text",
        "showlegend": True,
    })

    return {"traces": traces, "route_info": route_info}


# Gerar HTML 

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
    {ref_box}
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


def build_ref_box(instance, result):
    from BigM import SOLOMON_REFERENCE
    ref = SOLOMON_REFERENCE.get(instance.name.upper())
    if not ref or result["obj_value"] is None:
        return ""
    ref_v, ref_d = ref
    gap = (result["obj_value"] - ref_d) / ref_d * 100
    gap_class = "gap-good" if abs(gap) < 0.1 else ("gap-ok" if gap < 5 else "gap-bad")
    optimal = " ✓ Ótimo global!" if abs(gap) < 0.01 else ""
    return f"""
    <div class="ref-box">
      <h3>Referência Solomon</h3>
      Distância ref.: <b>{ref_d}</b><br>
      Distância obtida: <b>{result['obj_value']:.2f}</b><br>
      Gap: <span class="{gap_class}">{gap:+.2f}%{optimal}</span><br>
      Veículos ref.: <b>{ref_v}</b> (obtidos: <b>{result['num_vehicles']}</b>)
    </div>"""


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
        runtime      = f"{result['runtime']:.1f}",
        ref_box      = build_ref_box(instance, result),
        route_cards  = build_route_cards(data["route_info"]),
        traces_json  = json.dumps(data["traces"]),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Visualização guardada em: {output_path}")


# Ponto de entrada 

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python visualize_routes.py <ficheiro_solomon>")
        print("Exemplo: python visualize_routes.py solomon/C101.txt")
        sys.exit(1)

    filepath = sys.argv[1]
    instance = load_solomon(filepath)

    print(f"A resolver {instance.name}...")
    result = solve_cvrptw(instance, time_limit=300.0, mip_gap=0.01, verbose=False)

    if result["obj_value"] is None:
        print("Nenhuma solução encontrada — não é possível visualizar.")
        sys.exit(1)

    output = filepath.replace(".txt", "_routes.html").replace("solomon/", "")
    generate_html(instance, result, output)
    print(f"  Abre o ficheiro '{output}' no browser!")
