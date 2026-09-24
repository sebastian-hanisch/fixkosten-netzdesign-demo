"""Ein eigener kleiner Branch-and-Bound (beste Schranke zuerst) für den Entwurf: zeigt, was die Schranke am Ende bringt - die Größe des Suchbaums.

HiGHS (`solve_mip`) löst diese Netze fast immer schon an der Wurzel (eigene Schnitte, Vorverarbeitung) und taugt deshalb nicht, um Formulierungen zu vergleichen. Hier gibt es keine
Vorverarbeitung und keine verdeckten Schnitte: an jedem Knoten wird das LP der gewählten Formulierung gelöst (mit den festgelegten y als Grenzen), verzweigt wird auf dem Entwurf mit dem
gebrochensten Wert (nächster an 0,5), abgeschnitten, sobald die Schranke die beste bekannte Lösung nicht mehr unterbietet.
"""

import heapq
from dataclasses import dataclass
from time import perf_counter

import numpy as np
from scipy.optimize import linprog

import fcn_formulation as fm

INT_TOL = 1e-6


@dataclass(frozen=True)
class BnbResult:
    objective: float       # beste gefundene Lösung
    proven: bool           # True: Optimalität bewiesen (Suchbaum leer), False: Knotengrenze erreicht
    nodes: int             # gelöste LPs (Wurzel eingeschlossen)
    root_bound: float
    seconds: float


def branch_and_bound(design, level=fm.STRONG, cuts=(), node_limit=5000, incumbent=None):
    """`level`/`cuts` bestimmen die Formulierung (Schnitte fest an der Wurzel: Cut-and-Branch). `incumbent`: bekannte obere Schranke (z. B. aus dem Aufrunden), spart Knoten am Anfang."""
    c, a_eq, b_eq, a_ub, b_ub, lo0, hi0 = fm._build(design, level, cuts)
    nx = design.K * design.m
    bounds_of = lambda lo, hi: list(zip(lo, np.where(np.isinf(hi), None, hi)))
    a_ub_arg, b_ub_arg = (a_ub, b_ub) if a_ub.shape[0] else (None, None)
    t0 = perf_counter()
    best = incumbent if incumbent is not None else float("inf")
    nodes = 0

    def solve(lo, hi):
        nonlocal nodes
        nodes += 1
        res = linprog(c, A_ub=a_ub_arg, b_ub=b_ub_arg, A_eq=a_eq, b_eq=b_eq, bounds=bounds_of(lo, hi), method="highs")
        return res if res.status == 0 else None

    root = solve(lo0, hi0)
    if root is None:
        raise fm.Infeasible("keine Lieferung möglich")
    heap = [(root.fun, 0, lo0, hi0, root.x)]
    counter = 1
    while heap and nodes < node_limit:
        bound, _, lo, hi, x = heapq.heappop(heap)
        if bound >= best - 1e-9:
            continue
        y = x[nx:]
        frac = np.abs(y - np.round(y))
        if frac.max() < INT_TOL:
            best = bound
            continue
        g = int(np.argmax(np.minimum(y, 1 - y)))
        for value in (0.0, 1.0):
            lo2, hi2 = lo.copy(), hi.copy()
            lo2[nx + g] = hi2[nx + g] = value
            res = solve(lo2, hi2)
            if res is not None and res.fun < best - 1e-9:
                heapq.heappush(heap, (res.fun, counter, lo2, hi2, res.x))
                counter += 1
    proven = not any(b < best - 1e-9 for b, *_ in heap)
    return BnbResult(best, proven, nodes, float(root.fun), perf_counter() - t0)
