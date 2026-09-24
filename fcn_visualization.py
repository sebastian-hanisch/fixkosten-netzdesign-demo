"""Plotly-Abbildungen: Netz mit den Entwurfswerten y, Schranken je Stufe, Schnittrunden, Verteilung der Schranken, Suchbaum, Fixkosten-/Auslastungsreihe und Größe.
Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen. Kanten haben über unsichtbare Marker einen Hover-Text
(Plotly-Linien reagieren nur an ihren Stützpunkten)."""

from math import atan2, degrees, hypot

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import fcn_constants as C


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.08), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _layout(fig, net, height, skip=()):
    xs = [p[0] for v, p in enumerate(net.pos) if v not in skip]
    ys = [p[1] for v, p in enumerate(net.pos) if v not in skip]
    pad = 9
    fig.update_xaxes(visible=False, range=[min(xs) - pad, max(xs) + pad], scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False, range=[min(ys) - pad, max(ys) + pad])
    return _base(fig, height)


def _curve(p0, p1, bulge, steps=8):
    """Punkte von p0 nach p1; mit `bulge` > 0 als flacher Bogen nach rechts (so trennen sich Vorwärts- und Rückkante). Dazu der Pfeilwinkel bei 65 %."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length = hypot(dx, dy) or 1.0
    cx, cy = (x0 + x1) / 2 + bulge * length * dy / length, (y0 + y1) / 2 - bulge * length * dx / length
    ts = [k / steps for k in range(steps + 1)]
    xs = [(1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1 for t in ts]
    ys = [(1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1 for t in ts]
    t = 0.65
    tx = 2 * (1 - t) * (cx - x0) + 2 * t * (x1 - cx)
    ty = 2 * (1 - t) * (cy - y0) + 2 * t * (y1 - cy)
    ax = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1
    ay = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1
    return xs, ys, (ax, ay, degrees(atan2(tx, ty))), (xs[steps // 2], ys[steps // 2])


def _segments(curves):
    x, y = [], []
    for xs, ys, _, _ in curves:
        x += xs + [None]
        y += ys + [None]
    return x, y


def _lines(fig, curves, color, width, name, dash=None, showlegend=True):
    if not curves:
        return
    x, y = _segments(curves)
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=color, width=width, dash=dash), hoverinfo="skip", name=name, showlegend=showlegend))


def _arrows(fig, curves, color, size=9):
    if not curves:
        return
    fig.add_trace(go.Scatter(x=[c[2][0] for c in curves], y=[c[2][1] for c in curves], mode="markers", hoverinfo="skip", showlegend=False,
                             marker=dict(symbol="arrow", size=size, color=color, angle=[c[2][2] for c in curves])))


def _hover_points(fig, net, entries):
    """Unsichtbare Marker entlang jeder Kante, damit der Hover-Text überall auf der Kante erscheint. entries: [(Kurve, Text)]"""
    x, y, text = [], [], []
    for curve, label in entries:
        xs, ys = curve[0], curve[1]
        for k in range(1, len(xs) - 1):
            x.append(xs[k]); y.append(ys[k]); text.append(label)
    if x:
        fig.add_trace(go.Scatter(x=x, y=y, mode="markers", marker=dict(size=9, opacity=0), hovertext=text, hoverinfo="text", showlegend=False))


def _labels(fig, points):
    """points: [(x, y, Text)] - als Annotationen mit heller Hinterlegung, damit sie Kanten, Pfeile und Knotenbeschriftungen nicht unlesbar machen."""
    for x, y, text in points:
        fig.add_annotation(x=x, y=y, text=text, showarrow=False, xanchor="left", font=dict(size=11, color="#111"), bgcolor="rgba(255,255,255,0.88)", borderpad=1)


def _arc_name(net, i):
    u, v = net.arcs[i][0], net.arcs[i][1]
    return f"{net.names[u]} → {net.names[v]}"


def _wscale(net):
    return max(c for _, _, c, _, _ in net.arcs)


def _width(amount, top, lo=1.0, hi=6.0):
    return lo + (hi - lo) * amount / top if top else lo


def _node_text_positions(net, idx):
    if net.logistic:
        return ["top center" if (v == 0 or net.names[v].startswith("Werk")) else "bottom center" if (v == 1 or net.names[v].startswith("Filiale")) else "middle left" for v in idx]
    return ["top center" if v == net.s else "bottom center" if v == net.t else "middle left" for v in idx]


TOL = 1e-6


def _shift(curve, dx, dy):
    xs, ys, (ax, ay, ang), (mx, my) = curve
    return [x + dx for x in xs], [y + dy for y in ys], (ax + dx, ay + dy, ang), (mx + dx, my + dy)


def _fmt(x):
    return f"{x:.1f}".replace(".", ",") if abs(x - round(x)) > TOL else f"{round(x)}"


def _is_terminal(net, e):
    return net.arcs[e][0] == net.s or net.arcs[e][1] == net.t


def _num(x, digits=2):
    return f"{x:.{digits}f}".replace(".", ",")


def build_design_map(design, solution, opt_open=None, cut=None, height=480):
    """Netz mit dem Entwurf der LP-Lösung: Blau = Kante ganz offen (y = 1), orange gestrichelt = nur anteilig offen (Dicke ~ y, beschriftet), grau = geschlossen. Rote Unterlage: die Kanten des ganzzahligen
    Optimums. Violett: die Knotenmenge eines Schnitts (Ringe) und die Kanten, die sie betreten. Im Streckennetz sind die Kanten von S und zu T ausgeblendet."""
    net = design.net
    grid = design.mcf.layout == "grid"
    fig = go.Figure()
    bulge = 0.0 if net.logistic else 0.12
    y = solution.y
    cut_groups = set(cut.coef) if cut is not None else set()
    curves = {"open": [], "frac": [], "closed": [], "opt": [], "cut": [], "fixed": []}
    hover, labels = [], []
    seen = set()
    drawn = {}                                                    # (u, v) -> Zahl schon gezeichneter paralleler Kanten (versetzt sie gegeneinander)
    for e, (u, v, cap, cost, kind) in enumerate(net.arcs):
        if grid and _is_terminal(net, e):
            continue
        g = design.group[e]
        if grid and g in seen:
            continue                                              # beide Richtungen einer Strecke gehören zusammen: nur eine zeichnen
        par = drawn.get((u, v), 0)
        drawn[(u, v)] = par + 1
        base = _curve(net.pos[u], net.pos[v], 0.0 if grid else bulge + 0.2 * par)
        load = float(solution.x[:, e].sum())
        if g < 0:
            curves["fixed"].append(base)
            hover.append((base, f"{_arc_name(net, e)} (Kapazität {cap}, immer offen): Fluss {_fmt(load)}"))
            continue
        yg = float(y[g])
        state = "open" if yg > 1 - TOL else "closed" if yg < TOL else "frac"
        curves[state].append((base, yg))
        if opt_open is not None and g in opt_open:
            curves["opt"].append(base)
        if g in cut_groups and cut is not None and net.arcs[e][1] in cut.W and net.arcs[e][0] not in cut.W:
            curves["cut"].append(base)
        opt_txt = "" if opt_open is None else (", im Optimum offen" if g in opt_open else ", im Optimum geschlossen")
        hover.append((base, f"{_arc_name(net, e)}: y = {_num(yg, 2)}, Fixkosten {design.fixed[g]}, Kapazität {cap}, Fluss {_fmt(load)}{opt_txt}"))
        if state == "frac" and design.m <= 60 and g not in seen and yg >= 0.1:
            labels.append((base[0][3] + 1.5, base[1][3], _num(yg, 2)))
        seen.add(g)
    _lines(fig, curves["opt"], "rgba(214,39,40,0.35)", 11, "Optimum (ganzzahlig)")
    _lines(fig, curves["cut"], "rgba(148,103,189,0.55)", 9, "Schnitt: betretende Kanten")
    _lines(fig, curves["fixed"], C.COLORS["closed"], 1.0, "Werks-/Nachfragekanten", showlegend=False)
    _lines(fig, [c for c, _ in curves["closed"]], C.COLORS["closed"], 1.0, "geschlossen")
    _lines(fig, [c for c, _ in curves["open"]], C.COLORS["open"], 3.5, "offen (y = 1)")
    for c, yg in curves["frac"]:
        _lines(fig, [c], C.COLORS["frac"], 1.5 + 4 * yg, "anteilig (0 < y < 1)", dash="dash", showlegend=False)
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color=C.COLORS["frac"], width=3, dash="dash"), name="anteilig (0 < y < 1)"))
    if net.m <= 80:
        _arrows(fig, [c for c, _ in curves["open"]] + [c for c, _ in curves["frac"]], "rgba(60,60,60,0.55)", 7)
    _hover_points(fig, net, hover)
    _labels(fig, labels)
    idx = [v for v in range(net.n) if not (grid and v in (net.s, net.t))]
    in_w = [cut is not None and v in cut.W for v in idx]
    fig.add_trace(go.Scatter(x=[net.pos[v][0] for v in idx], y=[net.pos[v][1] for v in idx], mode="markers+text", showlegend=False, text=[net.labels[v] for v in idx],
                             textposition=_node_text_positions(net, idx), hovertext=[net.names[v] for v in idx], hoverinfo="text",
                             marker=dict(symbol=["square" if v in (net.s, net.t) else "circle" for v in idx], size=[15 if w else (13 if v in (net.s, net.t) else 10) for v, w in zip(idx, in_w)],
                                         color=[C.COLORS["cut"] if w else C.COLORS["node"] for w in in_w], line=dict(width=1.5, color="#333"))))
    return _layout(fig, net, height, skip=(net.s, net.t) if grid else ())


def build_levels(values, opt, upper, height=330):
    """Schranken je Formulierung als Anteil am Optimum (100 % = Optimum); gepunktet die obere Schranke aus dem Aufrunden. `values`: [(Name, Schranke)]."""
    fig = go.Figure()
    names = [n for n, _ in values]
    ratios = [v / opt for _, v in values]
    colors = ["#c7c7c7", "#7f7f7f", "#1f77b4", "#9467bd"][:len(values)]
    finite = [r for r in ratios if r < 10]
    fig.add_trace(go.Bar(x=names, y=[100 * min(r, 10) for r in ratios], marker_color=colors, text=[f"{100 * r:.1f} %".replace(".", ",") if r < 10 else "unlösbar" for r in ratios],
                         textposition="inside", insidetextanchor="end", textfont=dict(color="#ffffff", size=13), showlegend=False,
                         hovertext=[f"{n}: {_num(v, 1)} von {_num(opt, 1)}" for n, v in values], hoverinfo="text"))
    fig.add_hline(y=100, line=dict(color=C.COLORS["opt"], width=2))
    fig.add_hline(y=100 * upper / opt, line=dict(color="#555", width=1.5, dash="dot"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color=C.COLORS["opt"], width=2), name="Optimum (100 %)"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="#555", width=1.5, dash="dot"), name="aufgerundet (obere Schranke)"))
    hi = max([100 * upper / opt] + [100 * r for r in finite])
    fig.update_yaxes(range=[0, hi + 14], title="Anteil am Optimum [%]")
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.22), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def build_rounds(rounds, opt, i, height=300):
    """Schranke nach jeder Schnittrunde (Runde 0 = ohne Schnitte); Marke bei der gezeigten Runde."""
    xs = list(range(len(rounds)))
    ys = [100 * r.bound / opt for r in rounds]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", line=dict(color=C.COLORS["open"], width=2), marker=dict(size=7), name="Schranke",
                             hovertext=[f"Runde {k}: {_num(rounds[k].bound, 1)} ({len(rounds[k].added)} neue Schnitte)" for k in xs], hoverinfo="text"))
    fig.add_trace(go.Scatter(x=[i], y=[ys[i]], mode="markers", marker=dict(size=14, color="rgba(0,0,0,0)", line=dict(width=3, color=C.COLORS["cut"])), name="gezeigte Runde", hoverinfo="skip"))
    fig.add_hline(y=100, line=dict(color=C.COLORS["opt"], width=2), annotation_text="Optimum", annotation_position="bottom right")
    fig.update_xaxes(title="Schnittrunde", dtick=1)
    fig.update_yaxes(title="Anteil am Optimum [%]", range=[min(ys + [90]) - 5, 104])
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.3), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def build_dist(dist, mine, height=360):
    """Verteilung der drei Schranken (Anteil am Optimum) über die festen Netze; Raute = die gezeigte Ziehung. `mine`: {weak, strong, cuts} als Anteile."""
    fig = go.Figure()
    for key, name, color in (("weak", "schwach", "#7f7f7f"), ("strong", "stark", "#1f77b4"), ("cuts", "stark + Schnitte", "#9467bd")):
        fig.add_trace(go.Box(y=[100 * v for v in dist["cols"][key]], name=name, marker_color=color, boxpoints="all", jitter=0.4, pointpos=0, marker_size=4, showlegend=False))
    if mine:
        fig.add_trace(go.Scatter(x=["schwach", "stark", "stark + Schnitte"], y=[100 * mine[k] for k in ("weak", "strong", "cuts")], mode="markers", name="Ihre Ziehung",
                                 marker=dict(symbol="diamond", size=13, color=C.COLORS["opt"], line=dict(width=1.5, color="#111"))))
    fig.add_hline(y=100, line=dict(color=C.COLORS["opt"], width=1.5, dash="dot"))
    fig.update_yaxes(title="Anteil am Optimum [%]")
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.1), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def build_tree(table, height=320):
    """Knoten im eigenen Branch-and-Bound je Formulierung (Median und Mittel über die Netze), logarithmische Achse."""
    names = [("weak", "schwach"), ("strong", "stark"), ("cuts", "stark + Schnitte")]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[n for _, n in names], y=[table[k]["median"] for k, _ in names], name="Median", marker_color="#1f77b4", text=[f"{table[k]['median']:.0f}" for k, _ in names], textposition="outside"))
    fig.add_trace(go.Bar(x=[n for _, n in names], y=[table[k]["mean"] for k, _ in names], name="Mittel", marker_color="#aec7e8", text=[f"{table[k]['mean']:.0f}" for k, _ in names], textposition="outside"))
    fig.update_yaxes(type="log", title="Knoten im Suchbaum (logarithmisch)")
    fig.update_layout(height=height, barmode="group", margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.15), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def build_sweep(rows, xlabel, height=320):
    """Schranken (Anteil am Optimum) bei wachsendem Fixkosten- bzw. Auslastungswert."""
    fig = go.Figure()
    xs = [str(r["value"]) for r in rows]
    for key, name, color in (("weak", "schwach", "#7f7f7f"), ("strong", "stark", "#1f77b4"), ("cuts", "stark + Schnitte", "#9467bd")):
        fig.add_trace(go.Scatter(x=xs, y=[100 * r[key] for r in rows], mode="lines+markers", name=name, line=dict(color=color, width=2)))
    fig.add_hline(y=100, line=dict(color=C.COLORS["opt"], width=1.5, dash="dot"))
    fig.update_xaxes(title=xlabel, type="category")
    fig.update_yaxes(title="Anteil am Optimum [%]", range=[40, 102])
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.25), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def build_modes(table, height=300):
    """Mittlerer Anteil am Optimum je Schnittform (ohne die ungültige)."""
    keys = [("none", "keine"), ("plain", "Kapazität"), ("cap", "gekappt"), ("round", "gekappt + gerundet")]
    fig = go.Figure(go.Bar(x=[n for _, n in keys], y=[100 * table[k]["ratio"] for k, _ in keys], marker_color=["#7f7f7f", "#aec7e8", "#1f77b4", "#9467bd"],
                           text=[f"{100 * table[k]['ratio']:.1f} %".replace(".", ",") for k, _ in keys], textposition="outside"))
    fig.update_yaxes(title="Anteil am Optimum [%]", range=[50, 108])
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    return lock_axes(fig)


def build_sizes(rows, height=300):
    """Anteil der Lücke, den die Schnitte schließen, je Netzgröße (Beschriftung: Zahl der Entwurfsgruppen)."""
    xs = [f"{P}/{D}/{S}" for P, D, S in (r["size"] for r in rows)]
    fig = go.Figure(go.Bar(x=xs, y=[100 * r["closed"] for r in rows], marker_color="#9467bd", text=[f"{r['groups']:.0f} Gruppen" for r in rows], textposition="outside"))
    fig.update_xaxes(title="Werke / Verteilzentren / Filialen", type="category")
    fig.update_yaxes(title="Lücke geschlossen [%]", range=[0, 115])
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    return lock_axes(fig)
