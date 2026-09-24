"""Auswertung: Netzbau, Schranken der drei Formulierungen, Optimum, obere Schranke, Urteil, Verteilungen über feste Netze und die Experiment-Tabellen."""

import statistics as st
from dataclasses import dataclass
from math import isfinite
from typing import NamedTuple

import fcn_bnb as bnb
import fcn_constants as C
import fcn_cuts as cu
import fcn_formulation as fm
import fcn_model as md

EXACT_TOL = 1e-6


class NetParams(NamedTuple):
    net: str
    k: int
    p: int
    d: int
    s: int
    density: int
    spread: int
    load: int
    fix: int
    seed: int
    gw: int
    gh: int
    gdensity: int
    gcap: int
    gdem: int
    gseed: int


class Opts(NamedTuple):
    coupling: str
    cuts: str


DEFAULT_PARAMS = NetParams(C.DEFAULT_NET, C.DEFAULT_K, C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, C.DEFAULT_FIX, C.DEFAULT_SEED,
                           C.DEFAULT_GW, C.DEFAULT_GH, C.DEFAULT_GDENSITY, C.DEFAULT_GCAP, C.DEFAULT_GDEM, C.DEFAULT_GSEED)
DEFAULT_OPTS = Opts(C.DEFAULT_COUPLING, C.DEFAULT_CUT_MODE)
LEVELS = {"weak": fm.WEAK, "strong": fm.STRONG}
MODES_OF = {"plain": ("plain",), "cap": ("plain", "cap"), "round": cu.MODES, "wrong": cu.MODES}


def normalise(p):
    """Feste Netze ignorieren alle Regler der Zufallsnetze; das Streckennetz die des Distributionsnetzes und umgekehrt (gleicher Schlüssel für den Zwischenspeicher)."""
    if p.net in C.FIXED_NETS:
        return DEFAULT_PARAMS._replace(net=p.net, k={"bigm": 1, "rounding": 1, "bundle": 2}[p.net])
    if p.net == "grid":
        return p._replace(p=C.DEFAULT_P, d=C.DEFAULT_D, s=C.DEFAULT_S, density=C.DEFAULT_DENSITY, spread=C.DEFAULT_SPREAD, load=C.DEFAULT_LOAD, seed=C.DEFAULT_SEED)
    return p._replace(gw=C.DEFAULT_GW, gh=C.DEFAULT_GH, gdensity=C.DEFAULT_GDENSITY, gcap=C.DEFAULT_GCAP, gdem=C.DEFAULT_GDEM, gseed=C.DEFAULT_GSEED)


def build(p):
    if p.net == "bigm":
        return md.bigm_net()
    if p.net == "rounding":
        return md.rounding_net()
    if p.net == "bundle":
        return md.bundle_net()
    if p.net == "grid":
        return md.generate_design_grid(p.gw, p.gh, p.gdensity, p.gcap, p.gdem, p.k, p.gseed, p.fix)
    return md.generate_design(p.p, p.d, p.s, p.density, p.spread, p.load, p.seed, p.k, p.fix)


def with_seed(p, seed):
    return p._replace(gseed=seed) if p.net == "grid" else p._replace(seed=seed)


@dataclass(frozen=True)
class Analysis:
    params: NetParams
    opts: Opts
    design: object
    feasible: bool
    weak: object = None            # Solution der schwachen LP-Relaxation
    strong: object = None
    cuts: object = None            # CutResult (None ohne Schnitte)
    opt: object = None             # Solution des exakten MIP
    upper: float = None            # obere Schranke durch Aufrunden
    upper_open: frozenset = frozenset()

    @property
    def shown(self):
        """Die LP-Lösung der gewählten Formulierung (Kopplung + Schnitte) und ihre Schranke."""
        if self.cuts is not None:
            return self.cuts.final
        return self.weak if self.opts.coupling == "weak" else self.strong

    @property
    def bound(self):
        return self.cuts.bound if self.cuts is not None else self.shown.objective


def analyse(params, opts=DEFAULT_OPTS):
    params = normalise(params)
    design = build(params)
    try:
        weak, strong, opt = fm.solve_lp(design, fm.WEAK), fm.solve_lp(design, fm.STRONG), fm.solve_mip(design)
    except fm.Infeasible:
        return Analysis(params, opts, design, False)
    cuts = None
    if opts.cuts != "none":
        cuts = cu.cut_and_solve(design, modes=MODES_OF[opts.cuts], wrong=opts.cuts == "wrong", level=LEVELS[opts.coupling])
    upper, opened = fm.round_up(design, strong)
    return Analysis(params, opts, design, True, weak, strong, cuts, opt, upper, frozenset(opened))


def gap_closed(bound, weak, opt):
    return fm.gap_closed(bound, weak, opt)


def verdict(a):
    """(Stufe, Code, Daten): ok / trivial (die schwache Schranke ist schon exakt) / wrong (Schranke über dem Optimum: ungültige Schnitte) / nothing (nicht lieferbar)."""
    if not a.feasible:
        return "warning", "nothing", {}
    opt, weak, strong = a.opt.objective, a.weak.objective, a.strong.objective
    d = {"opt": opt, "weak": weak, "strong": strong, "bound": a.bound, "ratio_weak": weak / opt, "ratio_strong": strong / opt, "ratio_bound": a.bound / opt if isfinite(a.bound) else float("inf"),
         "closed_strong": gap_closed(strong, weak, opt), "closed_bound": gap_closed(a.bound, weak, opt) if isfinite(a.bound) else float("inf"), "upper": a.upper, "ratio_upper": a.upper / opt,
         "groups": a.design.G, "open": a.opt.n_open, "fractional_weak": a.weak.n_fractional, "fractional_strong": a.strong.n_fractional,
         "rounds": len(a.cuts.rounds) - 1 if a.cuts else 0, "n_cuts": len(a.cuts.cuts) if a.cuts else 0, "converged": a.cuts.converged if a.cuts else True, "infeasible_cuts": bool(a.cuts and a.cuts.infeasible)}
    if a.cuts is not None and (a.cuts.infeasible or a.bound > opt + 1e-6):
        return "error", "wrong", d
    if weak > opt - EXACT_TOL:
        return "success", "trivial", d
    return "success", "ok", d


# --- Verteilung über feste Netze ------------------------------------------------------------------------------------------------------

def distribution(params, seeds=C.QUALITY_SEEDS):
    """Schranken (Anteil am Optimum) von schwach, stark und stark + gerundeten Schnitten über feste Netze derselben Art (nur die Seeds ändern sich). Nicht lieferbare Netze werden gezählt, nicht gemittelt."""
    rows, infeasible = [], 0
    for seed in seeds:
        a = analyse(with_seed(params, seed), Opts("strong", "round"))
        if not a.feasible:
            infeasible += 1
            continue
        opt = a.opt.objective
        rows.append(dict(seed=seed, weak=a.weak.objective / opt, strong=a.strong.objective / opt, cuts=a.bound / opt, upper=a.upper / opt, rounds=len(a.cuts.rounds) - 1, n_cuts=len(a.cuts.cuts),
                         closed_strong=gap_closed(a.strong.objective, a.weak.objective, opt), closed_cuts=gap_closed(a.bound, a.weak.objective, opt), groups=a.design.G))
    col = lambda key: [r[key] for r in rows]
    mean = lambda key: st.mean(col(key)) if rows else float("nan")
    return dict(n_seeds=len(seeds), n_feasible=len(rows), n_infeasible=infeasible, cols={k: col(k) for k in ("weak", "strong", "cuts", "upper", "rounds", "n_cuts", "closed_strong", "closed_cuts")},
                weak_mean=mean("weak"), strong_mean=mean("strong"), cuts_mean=mean("cuts"), upper_mean=mean("upper"), cuts_min=min(col("cuts")) if rows else float("nan"),
                weak_min=min(col("weak")) if rows else float("nan"), closed_strong_mean=mean("closed_strong"), closed_cuts_mean=mean("closed_cuts"), rounds_mean=mean("rounds"), n_cuts_mean=mean("n_cuts"),
                exact_share=(sum(1 for r in rows if r["cuts"] > 1 - EXACT_TOL) / len(rows)) if rows else float("nan"), closed_cuts_median=st.median(col("closed_cuts")) if rows else float("nan"))


# --- Experimente ---------------------------------------------------------------------------------------------------------------------

def tree_table(params, seeds=C.TREE_SEEDS, node_limit=C.NODE_LIMIT):
    """Größe des Suchbaums im eigenen Branch-and-Bound je Formulierung (gleiche obere Schranke aus dem Aufrunden als Startlösung): schwach, stark, stark + Schnitte (Cut-and-Branch)."""
    names = ("weak", "strong", "cuts")
    per = {n: {"nodes": [], "proven": 0} for n in names}
    used = 0
    for seed in seeds:
        p = normalise(with_seed(params, seed))
        design = build(p)
        try:
            strong = fm.solve_lp(design, fm.STRONG)
        except fm.Infeasible:
            continue
        used += 1
        inc = fm.round_up(design, strong)[0] + 1e-6
        cr = cu.cut_and_solve(design)
        for name, (level, cuts) in zip(names, ((fm.WEAK, ()), (fm.STRONG, ()), (fm.STRONG, cr.cuts))):
            r = bnb.branch_and_bound(design, level, cuts, node_limit=node_limit, incumbent=inc)
            per[name]["nodes"].append(r.nodes)
            per[name]["proven"] += int(r.proven)
    out = {"n": used}
    for name in names:
        nodes = per[name]["nodes"]
        out[name] = dict(median=st.median(nodes) if nodes else float("nan"), mean=st.mean(nodes) if nodes else float("nan"), proven=per[name]["proven"], nodes=nodes)
    return out


def sweep_table(params, key, values, seeds=C.SWEEP_SEEDS):
    """Schranken (Anteil am Optimum, Mittel über die lieferbaren Netze) bei wachsendem `key` (\"fix\" oder \"load\")."""
    rows = []
    for v in values:
        p = params._replace(**{key: v})
        d = distribution(p, seeds)
        rows.append(dict(value=v, n=d["n_feasible"], weak=d["weak_mean"], strong=d["strong_mean"], cuts=d["cuts_mean"], closed=d["closed_cuts_mean"]))
    return rows


def mode_table(params, seeds=C.SWEEP_SEEDS):
    """Was jede Schnittform leistet (starke Kopplung): Mittel des Anteils am Optimum, Anteil exakter Netze, Schnitte und Runden; dazu die ungültige Form (Anteil der Netze, in denen das LP unlösbar oder die Schranke über dem Optimum ist)."""
    rows = {m: dict(ratio=[], exact=0, cuts=[], rounds=[], invalid=0) for m in ("none", "plain", "cap", "round", "wrong")}
    n = 0
    for seed in seeds:
        p = with_seed(params, seed)
        design = build(normalise(p))
        try:
            strong, opt = fm.solve_lp(design, fm.STRONG), fm.solve_mip(design)
        except fm.Infeasible:
            continue
        n += 1
        for mode in rows:
            if mode == "none":
                bound, cuts, rounds, invalid = strong.objective, 0, 0, False
            else:
                r = cu.cut_and_solve(design, modes=MODES_OF[mode], wrong=mode == "wrong")
                bound, cuts, rounds = r.bound, len(r.cuts), len(r.rounds) - 1
                invalid = r.infeasible or bound > opt.objective + 1e-6
            r_ = rows[mode]
            r_["invalid"] += int(invalid)
            if isfinite(bound):
                r_["ratio"].append(bound / opt.objective)
                r_["exact"] += int(bound > opt.objective - EXACT_TOL)
            r_["cuts"].append(cuts)
            r_["rounds"].append(rounds)
    out = {"n": n}
    for mode, r in rows.items():
        out[mode] = dict(ratio=st.mean(r["ratio"]) if r["ratio"] else float("nan"), exact=r["exact"], cuts=st.mean(r["cuts"]) if r["cuts"] else 0.0, rounds=st.mean(r["rounds"]) if r["rounds"] else 0.0, invalid=r["invalid"])
    return out


def separation_table(seeds=C.SEPARATION_SEEDS):
    """Kandidatenmengen mit lokaler Suche gegen exaktes Aufzählen aller Knotenmengen (kleine Netze 2 Werke, 2 Verteilzentren, 3 Filialen, 2 Güter)."""
    heur, exact, better, n = [], [], 0, 0
    for seed in seeds:
        design = md.generate_design(2, 2, 3, 70, 50, 50, seed, 2, C.DEFAULT_FIX)
        try:
            opt = fm.solve_mip(design)
            h = cu.cut_and_solve(design)
        except fm.Infeasible:
            continue
        lp, cuts = fm.solve_lp(design, fm.STRONG), []
        for _ in range(80):
            c = cu.separate_exact(design, lp.y)
            if c is None:
                break
            cuts.append(c)
            lp = fm.solve_lp(design, fm.STRONG, cuts)
        n += 1
        heur.append(h.bound / opt.objective)
        exact.append(lp.objective / opt.objective)
        better += int(lp.objective > h.bound + 1e-6)
    return dict(n=n, heuristic=st.mean(heur) if heur else float("nan"), exact=st.mean(exact) if exact else float("nan"), exact_better=better)


def size_table(sizes=C.SIZES, seeds=C.SWEEP_SEEDS[:8], fix=C.DEFAULT_FIX):
    """Entwurfsgruppen, Lückenschluss und Rechenaufwand je Netzgröße (Mittel über lieferbare Netze)."""
    out = []
    for P, D, S in sizes:
        rows = []
        for seed in seeds:
            design = md.generate_design(P, D, S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, seed, C.DEFAULT_K, fix)
            try:
                weak, opt = fm.solve_lp(design, fm.WEAK), fm.solve_mip(design)
            except fm.Infeasible:
                continue
            r = cu.cut_and_solve(design)
            rows.append(dict(groups=design.G, closed=gap_closed(r.bound, weak.objective, opt.objective), cuts=len(r.cuts), rounds=len(r.rounds) - 1, ratio=r.bound / opt.objective))
        out.append(dict(size=(P, D, S), n=len(rows), groups=st.mean(x["groups"] for x in rows) if rows else float("nan"), closed=st.mean(x["closed"] for x in rows) if rows else float("nan"),
                        cuts=st.mean(x["cuts"] for x in rows) if rows else float("nan"), rounds=st.mean(x["rounds"] for x in rows) if rows else float("nan"), ratio=st.mean(x["ratio"] for x in rows) if rows else float("nan")))
    return out


# --- Anzeige-Helfer ------------------------------------------------------------------------------------------------------------------

def arc_name(design, e):
    net = design.net
    return f"{net.names[net.arcs[e][0]]} → {net.names[net.arcs[e][1]]}"


def group_name(design, g):
    return arc_name(design, design.arcs_of(g)[0])


def cut_words(design, cut):
    """Der Schnitt in Worten: Menge W, Bedarf und die Ungleichung über die betretenden Kanten."""
    net = design.net
    nodes = ", ".join(sorted(net.labels[v] or net.names[v] for v in cut.W))
    terms = " + ".join(f"{a}·y({group_name(design, g)})" if a != 1 else f"y({group_name(design, g)})" for g, a in sorted(cut.coef.items()))
    return f"In die Knoten {{{nodes}}} müssen mindestens {cut.need} Einheiten hinein. Also: {terms} ≥ {cut.rhs}"
