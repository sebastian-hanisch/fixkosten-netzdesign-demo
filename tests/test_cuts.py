"""Schnitte: Bedarf und Formen von Hand, jeder Schnitt gilt für alle zulässigen Entwürfe (Aufzählen), ungültige Formen schneiden das Optimum ab, Schnittschleife."""

from itertools import chain, combinations

import pytest

import fcn_cuts as cu
import fcn_formulation as fm
import fcn_model as md
from test_formulation import tiny_nets


def _all_sets(design):
    inner = cu.inner_nodes(design)
    return chain.from_iterable(combinations(inner, r) for r in range(1, len(inner) + 1))


def test_required_and_forms_by_hand_on_the_rounding_net():
    d = md.rounding_net()
    B = 3                                                    # Knoten B: die 3 Einheiten Nachfrage
    assert cu.required(d, {B}) == 3 and cu.required(d, {2}) == 0 and cu.required(d, {2, B}) == 0
    assert cu.entering(d, {B}) == {0: 2, 1: 2}
    forms = {(f.kind, f.delta): (f.coef, f.rhs) for f in cu.forms(d, {B})}
    assert forms[("plain", 0)] == ({0: 2, 1: 2}, 3) and forms[("cap", 0)] == ({0: 2, 1: 2}, 3) and forms[("round", 2)] == ({0: 1, 1: 1}, 2)
    lp = fm.solve_lp(d, fm.STRONG)
    assert cu.separate(d, lp.y, modes=("plain", "cap")) == []            # gekappt, aber ungerundet: bei y = (0,75, 0,75) nicht verletzt
    top = cu.separate(d, lp.y)[0]
    assert (top.kind, top.delta, top.rhs) == ("round", 2, 2) and top.violation == pytest.approx(0.5)


def test_every_cut_holds_for_every_feasible_design():
    """Das Kernargument: jede Form (plain, cap, round) jeder Knotenmenge wird von jedem zulässigen Entwurf erfüllt - über Aufzählen aller Entwürfe kleiner Netze."""
    for d in tiny_nets() + [md.bigm_net(), md.rounding_net(), md.bundle_net()]:
        _, _, feasible = fm.brute_force(d)
        checked = 0
        for W in _all_sets(d):
            for cut in cu.forms(d, frozenset(W)):
                checked += 1
                assert all(cut.holds(bits) for bits in feasible), (cut.kind, cut.delta, sorted(cut.W), cut.coef, cut.rhs)
        assert checked >= 2


def test_wrong_cuts_cut_off_designs():
    d = md.rounding_net()
    _, _, feasible = fm.brute_force(d)
    wrong = [c for W in _all_sets(d) for c in cu.forms(d, frozenset(W), wrong=True) if c.kind == "round"]
    assert wrong and all(any(not c.holds(bits) for bits in feasible) for c in wrong)        # jede falsche Form schneidet mindestens einen zulässigen Entwurf ab


def test_cut_loop_is_monotone_valid_and_converges():
    for d in tiny_nets() + [md.rounding_net(), md.generate_design(3, 3, 8, 60, 50, 50, 155, 3, 30)]:
        opt = fm.solve_mip(d).objective
        strong = fm.solve_lp(d, fm.STRONG).objective
        r = cu.cut_and_solve(d)
        bounds = [x.bound for x in r.rounds]
        assert r.converged and not r.infeasible and bounds == sorted(bounds) and bounds[0] == pytest.approx(strong, abs=1e-6)
        assert strong - 1e-6 <= r.bound <= opt + 1e-6
        assert all(all(c.holds(r.final.y, tol=1e-6) for c in r.cuts) for _ in (0,))
        assert len({c.key() for c in r.cuts}) == len(r.cuts)                  # keine doppelten Schnitte


def test_plain_cuts_are_never_violated_but_capped_ones_are():
    d = md.generate_design(3, 3, 8, 60, 50, 50, 155, 3, 30)
    assert cu.cut_and_solve(d, modes=("plain",)).cuts == ()                   # schon im schwachen LP enthalten
    assert len(cu.cut_and_solve(d, modes=("plain", "cap")).cuts) > 0


def test_wrong_cuts_break_the_lp_or_exceed_the_optimum():
    for d in tiny_nets():
        r = cu.cut_and_solve(d, wrong=True)
        assert r.infeasible or r.bound > fm.solve_mip(d).objective + 1e-6


def test_separation_finds_at_most_what_exact_separation_finds():
    for d in tiny_nets(count=2, groups=(8, 11)):
        y = fm.solve_lp(d, fm.STRONG).y
        exact = cu.separate_exact(d, y)
        heur = cu.separate(d, y, limit=1)
        if exact is None:
            assert heur == []
        else:
            assert not heur or heur[0].score <= exact.score + 1e-9


def test_infinite_flow_arc_blocks_a_cut():
    """Eine immer offene innere Kante betritt die Menge: kein Schnitt über y möglich."""
    d = md.generate_design(2, 2, 2, 60, 50, 40, 100000, 2, 30)
    fixed_arc = next(e for e in range(d.m) if d.group[e] >= 0)
    hacked = md.Design(d.mcf, tuple(-1 if e == fixed_arc else g for e, g in enumerate(d.group)), d.fixed)
    v = d.net.arcs[fixed_arc][1]
    assert cu.entering(hacked, {v}) is None and cu.forms(hacked, {v}) == []
