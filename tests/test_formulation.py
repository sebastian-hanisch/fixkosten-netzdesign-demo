"""Formulierungen: Lehrnetze von Hand, Schranken-Reihenfolge, MIP gegen Aufzählen aller Entwürfe, Aufrunden, Suchbaum."""

import numpy as np
import pytest

import fcn_bnb as bnb
import fcn_formulation as fm
import fcn_model as md


def tiny_nets(count=2, groups=(6, 11)):
    """Kleine lieferbare Distributionsnetze (wenige Entwurfsgruppen), damit das Aufzählen aller 2^G Entwürfe reicht."""
    out = []
    for seed in range(100000, 100200):
        d = md.generate_design(2, 2, 2, 60, 50, 40, seed, 2, 30)
        if groups[0] <= d.G <= groups[1]:
            try:
                fm.solve_lp(d, fm.WEAK)
            except fm.Infeasible:
                continue
            out.append(d)
            if len(out) == count:
                return out
    raise AssertionError("keine passenden Kleinstnetze")


def test_teaching_nets_by_hand():
    big = md.bigm_net()
    assert fm.solve_lp(big, fm.WEAK).objective == pytest.approx(4.0) and fm.solve_lp(big, fm.STRONG).objective == pytest.approx(15.0) and fm.solve_mip(big).objective == pytest.approx(15.0)
    assert list(fm.solve_lp(big, fm.WEAK).y) == pytest.approx([0.1, 0.0])
    rnd = md.rounding_net()
    assert fm.solve_lp(rnd, fm.WEAK).objective == pytest.approx(18.0) and fm.solve_lp(rnd, fm.STRONG).objective == pytest.approx(18.0) and fm.solve_mip(rnd).objective == pytest.approx(23.0)
    bun = md.bundle_net()
    assert fm.solve_lp(bun, fm.WEAK).objective == pytest.approx(6.5) and fm.solve_lp(bun, fm.STRONG).objective == pytest.approx(11.0) and fm.solve_mip(bun).objective == pytest.approx(11.0)
    assert list(fm.solve_mip(bun).y) == [0, 0, 1, 1, 1]


def test_design_structure():
    d = md.generate_design(3, 3, 8, 60, 50, 50, 155, 3, 30)
    kinds = {d.net.arcs[e][4] for e in range(d.m) if d.group[e] >= 0}
    assert kinds == {md.sc.K_LANE_IN, md.sc.K_THROUGHPUT, md.sc.K_LANE_OUT} and all(d.group[e] == -1 for e in range(d.m) if d.net.arcs[e][4] in (md.sc.K_SUPPLY, md.sc.K_DEMAND))
    assert d.G == len([1 for e in range(d.m) if d.group[e] >= 0]) and len(d.fixed) == d.G and min(d.fixed) >= 30
    assert all(f % 30 == 0 for f in d.fixed) and d == md.generate_design(3, 3, 8, 60, 50, 50, 155, 3, 30)      # ganzzahlig, reproduzierbar
    g = md.generate_design_grid(4, 3, 60, 3, 3, 3, 7, 8)
    assert g.G * 2 == len([1 for e in range(g.m) if g.group[e] >= 0]) and all(len(g.arcs_of(i)) == 2 for i in range(g.G))       # beide Richtungen einer Strecke gehören zusammen


def test_bounds_are_ordered_and_below_the_optimum():
    for seed in (155, 100000, 100001, 100002):
        d = md.generate_design(3, 3, 8, 60, 50, 50, seed, 3, 30)
        try:
            weak, strong, opt = fm.solve_lp(d, fm.WEAK), fm.solve_lp(d, fm.STRONG), fm.solve_mip(d)
        except fm.Infeasible:
            continue
        assert weak.objective <= strong.objective + 1e-6 <= opt.objective + 1e-6
        assert weak.n_fractional >= 1 and opt.n_fractional == 0 and opt.objective == pytest.approx(opt.flow_cost + opt.fixed_cost)
        assert fm.round_up(d, strong)[0] >= opt.objective - 1e-6


def test_mip_equals_brute_force_over_all_designs():
    for d in tiny_nets() + [md.bigm_net(), md.rounding_net(), md.bundle_net()]:
        best, bits, feasible = fm.brute_force(d)
        opt = fm.solve_mip(d)
        assert opt.objective == pytest.approx(best.objective, abs=1e-6) and len(feasible) >= 1
        assert fm.solve_mip(d, fm.WEAK).objective == pytest.approx(opt.objective, abs=1e-6)          # die Formulierung ändert das Optimum nicht


def test_mip_solution_is_a_valid_design():
    d = md.generate_design(3, 3, 8, 60, 50, 50, 155, 3, 30)
    opt = fm.solve_mip(d)
    net, K = d.net, d.K
    for k in range(K):
        for v in range(net.n):
            if v in (net.s, net.t):
                continue
            inflow = sum(opt.x[k, e] for e in range(d.m) if net.arcs[e][1] == v)
            outflow = sum(opt.x[k, e] for e in range(d.m) if net.arcs[e][0] == v)
            assert inflow == pytest.approx(outflow, abs=1e-6)
    for e in range(d.m):
        g = d.group[e]
        assert opt.x[:, e].sum() <= net.arcs[e][2] * (1 if g < 0 else opt.y[g]) + 1e-6
    assert all(v in (0.0, 1.0) for v in opt.y)
    for k in range(K):
        assert sum(opt.x[k, e] for e in d.demand_arcs()) == pytest.approx(d.mcf.demand(k))       # volle Nachfrage


def test_infeasible_net_is_detected():
    for seed in range(100000, 100060):
        d = md.generate_design(3, 3, 8, 60, 50, 50, seed, 3, 30)
        try:
            fm.solve_lp(d, fm.WEAK)
        except fm.Infeasible:
            with pytest.raises(fm.Infeasible):
                fm.solve_mip(d)
            return
    raise AssertionError("kein nicht lieferbares Netz gefunden")


def test_own_branch_and_bound_finds_the_optimum_and_cuts_shrink_the_tree():
    import fcn_cuts as cu
    for d in (md.bigm_net(), md.rounding_net(), md.bundle_net()) + tuple(tiny_nets()):
        opt = fm.solve_mip(d).objective
        strong = fm.solve_lp(d, fm.STRONG)
        inc = fm.round_up(d, strong)[0] + 1e-6
        r = bnb.branch_and_bound(d, fm.WEAK, incumbent=inc)
        assert r.proven and min(r.objective, inc) == pytest.approx(opt, abs=1e-4) and r.root_bound <= opt + 1e-6
        cuts = cu.cut_and_solve(d).cuts
        with_cuts = bnb.branch_and_bound(d, fm.STRONG, cuts, incumbent=inc)
        assert with_cuts.proven and min(with_cuts.objective, inc) == pytest.approx(opt, abs=1e-4) and with_cuts.nodes <= r.nodes
    limited = bnb.branch_and_bound(md.generate_design(3, 3, 8, 60, 50, 50, 100000, 3, 30), fm.WEAK, node_limit=5, incumbent=1e9)
    assert not limited.proven and limited.nodes <= 7           # Knotengrenze wird eingehalten (ein Knoten Überhang je Verzweigung)


def test_gap_closed():
    assert fm.gap_closed(15, 4, 15) == 1.0 and fm.gap_closed(4, 4, 15) == 0.0 and fm.gap_closed(9.5, 4, 15) == pytest.approx(0.5) and fm.gap_closed(10, 10, 10) == 1.0
    assert np.isclose(fm.gap_closed(20, 4, 15), 16 / 11)           # über dem Optimum: > 1
