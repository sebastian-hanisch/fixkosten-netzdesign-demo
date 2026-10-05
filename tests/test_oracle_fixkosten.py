"""Orakel: das Entwurfsmodell unabhängig neu aufgestellt (OR-Tools: GLOP für die LPs, SCIP für das MIP, eigener Aufbau der Bilanz-, Kopplungs- und Schnittzeilen):
schwache und starke Schranke, Optimum, Aufzählen aller zulässigen Entwürfe, Gültigkeit jeder Schnittform für jeden zulässigen Entwurf, die Schnittschleife (Schranke
nach den Schnitten neu gerechnet), obere Schranke durch Aufrunden. Schnell (< 10 s)."""

import itertools
import random

import pytest

import fcn_cuts as cu
import fcn_formulation as fm
import fcn_model as md

pywraplp = pytest.importorskip("ortools.linear_solver.pywraplp")


def _solve(d, level, opened=None, integer=False, cuts=()):
    s = pywraplp.Solver.CreateSolver("SCIP" if integer else "GLOP")
    mcf, net, K, m, G = d.mcf, d.net, d.K, d.m, d.G
    x = [[s.NumVar(float(mcf.ub[k][e]) if mcf.reward[e] else 0.0, s.infinity() if mcf.ub[k][e] >= md.BIG else float(mcf.ub[k][e]), "") for e in range(m)] for k in range(K)]
    if opened is not None:
        y = [s.NumVar(float(g in opened), float(g in opened), "") for g in range(G)]
    else:
        y = [s.IntVar(0, 1, "") if integer else s.NumVar(0, 1, "") for _ in range(G)]
    for k in range(K):
        for v in range(net.n):
            if v not in (net.s, net.t):
                row = s.Constraint(0, 0)
                for e, (a, b, _, _, _) in enumerate(net.arcs):
                    row.SetCoefficient(x[k][e], row.GetCoefficient(x[k][e]) + (b == v) - (a == v))
    for e, (a, b, cap, _, _) in enumerate(net.arcs):
        if mcf.joint[e]:
            g = d.group[e]
            row = s.Constraint(-s.infinity(), 0.0 if g >= 0 else float(cap))
            for k in range(K):
                row.SetCoefficient(x[k][e], 1)
            if g >= 0:
                row.SetCoefficient(y[g], -float(cap))
    if level >= 1:
        for e in range(m):
            g = d.group[e]
            for k in range(K) if g >= 0 else ():
                bound = min(net.arcs[e][2], sum(mcf.ub[k][f] for f in range(m) if mcf.reward[f]), mcf.ub[k][e])
                row = s.Constraint(-s.infinity(), 0)
                row.SetCoefficient(x[k][e], 1)
                row.SetCoefficient(y[g], -float(bound))
    for c in cuts:
        row = s.Constraint(float(c.rhs), s.infinity())
        for g, a in c.coef.items():
            row.SetCoefficient(y[g], float(a))
    obj = s.Objective()
    for k in range(K):
        for e, (a, b, cap, cost, kind) in enumerate(net.arcs):
            if not mcf.reward[e]:
                obj.SetCoefficient(x[k][e], float(mcf.factors[k] * cost if kind in (md.sc.K_LANE_IN, md.sc.K_LANE_OUT) else cost))
    for g in range(G):
        obj.SetCoefficient(y[g], float(d.fixed[g]))
    obj.SetMinimization()
    status = s.Solve()
    if status == pywraplp.Solver.INFEASIBLE:
        return None
    assert status == pywraplp.Solver.OPTIMAL
    return obj.Value()


def _nets():
    rng = random.Random(4242)
    yield md.bigm_net()
    yield md.rounding_net()
    yield md.bundle_net()
    for _ in range(14):
        yield md.generate_design(2, rng.choice((2, 3)), rng.randint(2, 3), rng.choice((40, 60, 100)), rng.choice((0, 50, 100)), rng.choice((30, 50, 90)), rng.randint(0, 10 ** 6), rng.randint(1, 3), rng.choice((5, 30, 80)))
    for _ in range(6):
        yield md.generate_design_grid(rng.randint(2, 3), 2, rng.choice((40, 100)), rng.randint(1, 4), rng.randint(1, 3), rng.randint(1, 3), rng.randint(0, 10 ** 6), rng.choice((2, 10)))


def test_bounds_optimum_cuts_and_rounding_against_an_independent_model():
    seen = 0
    for d in _nets():
        if _solve(d, 0, opened=set(range(d.G))) is None:
            with pytest.raises(fm.Infeasible):
                fm.solve_lp(d, fm.WEAK)
            continue
        seen += 1
        weak, strong, opt = fm.solve_lp(d, fm.WEAK), fm.solve_lp(d, fm.STRONG), fm.solve_mip(d)
        assert weak.objective == pytest.approx(_solve(d, 0), abs=1e-5) and strong.objective == pytest.approx(_solve(d, 1), abs=1e-5)
        assert opt.objective == pytest.approx(_solve(d, 1, integer=True), abs=1e-5) == pytest.approx(opt.flow_cost + opt.fixed_cost, abs=1e-5)
        upper, opened = fm.round_up(d, strong)
        assert upper >= opt.objective - 1e-6 and upper == pytest.approx(_solve(d, 0, opened=opened), abs=1e-5)
        loop = cu.cut_and_solve(d)
        assert strong.objective - 1e-6 <= loop.bound <= opt.objective + 1e-6
        if loop.cuts:
            assert loop.bound == pytest.approx(_solve(d, 1, cuts=loop.cuts), abs=1e-5)
        if d.G <= 8:
            feasible = [bits for bits in itertools.product((0, 1), repeat=d.G) if _solve(d, 0, opened={g for g, b in enumerate(bits) if b}) is not None]
            assert min(_solve(d, 0, opened={g for g, b in enumerate(bits) if b}) for bits in feasible) == pytest.approx(opt.objective, abs=1e-5)
            inner = cu.inner_nodes(d)
            for r in range(1, len(inner) + 1):
                for W in itertools.combinations(inner, r):
                    for cut in cu.forms(d, frozenset(W)):
                        assert all(cut.holds(bits) for bits in feasible), (cut.kind, sorted(W))
    assert seen >= 15
