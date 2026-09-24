"""Auswertung: Netzbau, Urteil, Verteilungen, Experiment-Tabellen, Anzeige-Helfer."""

import pytest

import fcn_constants as C
import fcn_cuts as cu
import fcn_evaluation as ev
import fcn_formulation as fm
import fcn_model as md

P = ev.DEFAULT_PARAMS
GRID = P._replace(net="grid", k=3, fix=10)


def test_build_dispatches_on_the_net_and_ignores_the_random_settings_for_fixed_nets():
    assert ev.build(P) == md.generate_design(3, 3, 8, 60, 50, 50, 155, 3, 30)
    assert ev.build(GRID) == md.generate_design_grid(4, 3, 60, 4, 2, 3, 6, 10)
    assert ev.build(P._replace(net="bigm")) == md.bigm_net() and ev.build(P._replace(net="rounding")) == md.rounding_net() and ev.build(P._replace(net="bundle")) == md.bundle_net()
    assert ev.normalise(P._replace(net="rounding", k=5, seed=9, fix=77)) == ev.normalise(P._replace(net="rounding", fix=5))
    assert ev.normalise(P._replace(net="grid", p=6, seed=9)) == ev.normalise(P._replace(net="grid", p=2, seed=77))       # das Streckennetz ignoriert die Regler des Distributionsnetzes
    assert ev.normalise(P._replace(gw=6, gseed=9)) == ev.normalise(P._replace(gw=3, gseed=1))                             # und umgekehrt


def test_with_seed_changes_only_the_seed_of_the_shown_net():
    assert ev.with_seed(P, 5).seed == 5 and ev.with_seed(P, 5).gseed == P.gseed
    assert ev.with_seed(GRID, 5).gseed == 5 and ev.with_seed(GRID, 5).seed == P.seed


def test_verdict_codes_and_data():
    lvl, code, d = ev.verdict(ev.analyse(P))
    assert (lvl, code) == ("success", "ok") and d["opt"] == 1784.0 and d["groups"] == 27 and d["open"] == 15
    assert d["weak"] <= d["strong"] + 1e-6 <= d["bound"] + 1e-6 <= d["opt"] + 1e-6 and d["ratio_upper"] >= 1 and d["converged"] and not d["infeasible_cuts"]
    assert d["closed_bound"] == pytest.approx((d["bound"] - d["weak"]) / (d["opt"] - d["weak"])) and d["ratio_bound"] == pytest.approx(d["bound"] / d["opt"])
    lvl, code, d = ev.verdict(ev.analyse(P, ev.Opts("strong", "wrong")))
    assert (lvl, code) == ("error", "wrong") and d["infeasible_cuts"]
    lvl, code, d = ev.verdict(ev.analyse(P, ev.Opts("weak", "none")))
    assert code == "ok" and d["n_cuts"] == 0 and d["rounds"] == 0 and d["ratio_bound"] == pytest.approx(d["ratio_weak"])
    assert ev.verdict(ev.analyse(P._replace(seed=13)))[:2] == ("warning", "nothing")


def test_trivial_verdict_when_the_weak_bound_is_already_exact(monkeypatch):
    net = md._teaching(["Quelle S", "Senke T", "A", "B"], ["S", "T", "A", "B"], [(50, 96), (50, 4), (14, 50), (86, 50)], [(2, 3, 1, 1)], [5], [(0, 1, 1)])
    monkeypatch.setattr(ev, "build", lambda p: net)
    lvl, code, d = ev.verdict(ev.analyse(P))
    assert (lvl, code) == ("success", "trivial") and d["ratio_weak"] == pytest.approx(1.0)


def test_shown_solution_follows_the_chosen_formulation():
    weak, strong, cuts = ev.analyse(P, ev.Opts("weak", "none")), ev.analyse(P, ev.Opts("strong", "none")), ev.analyse(P)
    assert weak.shown is weak.weak and strong.shown is strong.strong and cuts.shown is cuts.cuts.final
    assert weak.bound == pytest.approx(weak.weak.objective) and cuts.bound == pytest.approx(cuts.cuts.bound)
    from_weak = ev.analyse(P, ev.Opts("weak", "round"))
    assert from_weak.cuts.rounds[0].bound == pytest.approx(from_weak.weak.objective) and from_weak.bound >= from_weak.weak.objective


def test_distribution_is_consistent_with_single_runs():
    seeds = tuple(range(100000, 100004))
    dist = ev.distribution(P, seeds=seeds)
    feasible = [s for s in seeds if ev.analyse(ev.with_seed(P, s)).feasible]
    assert dist["n_seeds"] == 4 and dist["n_feasible"] == len(feasible) and dist["n_infeasible"] == 4 - len(feasible)
    for i, seed in enumerate(feasible):
        d = ev.verdict(ev.analyse(ev.with_seed(P, seed)))[2]
        assert dist["cols"]["weak"][i] == pytest.approx(d["ratio_weak"]) and dist["cols"]["cuts"][i] == pytest.approx(d["ratio_bound"]) and dist["cols"]["n_cuts"][i] == d["n_cuts"]
    assert dist["weak_mean"] <= dist["strong_mean"] + 1e-9 <= dist["cuts_mean"] + 1e-9 <= 1 + 1e-9
    assert ev.distribution(GRID, seeds=seeds)["n_seeds"] == 4


def test_mode_table_shapes_and_orderings():
    t = ev.mode_table(P, seeds=C.SWEEP_SEEDS[:4])
    assert set(t) == {"n", "none", "plain", "cap", "round", "wrong"} and t["n"] >= 2
    assert t["plain"]["ratio"] == pytest.approx(t["none"]["ratio"]) and t["plain"]["cuts"] == 0 and t["cap"]["ratio"] > t["none"]["ratio"] + 0.1 and t["round"]["ratio"] >= t["cap"]["ratio"] - 1e-9
    assert t["wrong"]["invalid"] == t["n"] and t["round"]["invalid"] == 0


def test_sweep_and_size_tables_have_the_documented_shape():
    fx = ev.sweep_table(P, "fix", (10, 40), seeds=C.SWEEP_SEEDS[:3])
    assert [r["value"] for r in fx] == [10, 40] and fx[0]["weak"] > fx[1]["weak"]                     # mehr Fixkosten: schwächere Schranke
    sz = ev.size_table(sizes=((2, 2, 4), (3, 3, 8)), seeds=C.SWEEP_SEEDS[:8])
    assert [r["size"] for r in sz] == [(2, 2, 4), (3, 3, 8)] and sz[0]["groups"] < sz[1]["groups"]


def test_tree_table_counts_nodes():
    t = ev.tree_table(P, seeds=C.TREE_SEEDS[:3], node_limit=1500)
    assert t["n"] >= 2 and set(t) == {"n", "weak", "strong", "cuts"} and t["cuts"]["median"] < t["weak"]["median"] and t["cuts"]["proven"] == t["n"]


def test_separation_table():
    t = ev.separation_table(seeds=C.SEPARATION_SEEDS[:6])
    assert t["n"] >= 3 and t["exact"] >= t["heuristic"] - 1e-9 and 0.9 < t["heuristic"] <= 1 + 1e-9


def test_cut_words_and_names():
    a = ev.analyse(P._replace(net="rounding"))
    cut = next(c for c in a.cuts.cuts)
    text = ev.cut_words(a.design, cut)
    assert "mindestens 3 Einheiten" in text and "≥ 2" in text and "y(A → B)" in text
    assert ev.arc_name(a.design, 0) == "A → B" and ev.group_name(a.design, 1) == "A → B"


def test_teaching_nets_have_no_random_dependency_in_the_cache_key():
    assert ev.analyse(P._replace(net="bigm", seed=1)).opt.objective == ev.analyse(P._replace(net="bigm", seed=2)).opt.objective == 15.0
