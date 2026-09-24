"""Jede Zahl, die README und Hilfetexte nennen, ist hier belegt (Standardeinstellungen, feste Netze, Seeds ab 100000).
Das Optimum kommt aus HiGHS (MIP), die Schranken aus LPs (HiGHS); Anteile, Schnittzahlen und Suchbaum-Knoten werden mit Bändern geprüft (LP-Lösungen mit Gleichständen können auf anderen Plattformen andere Ecken wählen)."""

import pytest

import fcn_constants as C
import fcn_evaluation as ev
import fcn_formulation as fm
import fcn_model as md

P = ev.DEFAULT_PARAMS
GRID = P._replace(net="grid", k=3, fix=10)


@pytest.fixture(scope="module")
def dist():
    return ev.distribution(P)


def test_teaching_nets_by_hand():
    """Big-M-Falle: schwach 4 (26,7 %), stark und Optimum 15. Rundungs-Falle: schwach = stark = 18 (78,3 %), Optimum 23, Schnitt y1 + y2 >= 2 schließt die Lücke. Bündelung: schwach 6,5 (59,1 %), stark = Optimum 11 mit drei offenen Kanten."""
    big = ev.verdict(ev.analyse(P._replace(net="bigm"), ev.Opts("weak", "none")))[2]
    assert big["weak"] == pytest.approx(4.0) and big["ratio_weak"] == pytest.approx(0.2667, abs=1e-3) and big["strong"] == pytest.approx(15.0) and big["opt"] == 15.0
    rnd = ev.analyse(P._replace(net="rounding"))
    d = ev.verdict(rnd)[2]
    assert d["weak"] == pytest.approx(18.0) and d["strong"] == pytest.approx(18.0) and d["ratio_weak"] == pytest.approx(0.7826, abs=1e-3) and d["opt"] == 23.0 and d["ratio_bound"] == pytest.approx(1.0)
    top = rnd.cuts.cuts[0]
    assert (top.kind, top.delta, top.rhs, top.coef) == ("round", 2, 2, {0: 1, 1: 1}) and len(rnd.cuts.cuts) == 1
    bun = ev.analyse(P._replace(net="bundle"), ev.Opts("weak", "none"))
    d = ev.verdict(bun)[2]
    assert d["weak"] == pytest.approx(6.5) and d["ratio_weak"] == pytest.approx(0.5909, abs=1e-3) and d["strong"] == pytest.approx(11.0) and d["opt"] == 11.0 and d["open"] == 3


def test_seed_155_numbers():
    """Zufallsnetz Seed 155 (drei Güter, Fixkosten 30): Optimum 1 784, 15 von 27 Kanten offen; schwach 69,8 % (16 Kanten anteilig), stark 71,7 %, mit Schnitten 93,4 % (78 % der Lücke, 26 Schnitte, 3 Runden);
    Aufrunden liefert 1 826 (2,4 % über dem Optimum); mit Fixkosten 120: schwach 56,2 %, stark 58,3 %, Schnitte 96,7 % (93 % der Lücke)."""
    d = ev.verdict(ev.analyse(P))[2]
    assert d["opt"] == 1784.0 and d["groups"] == 27 and d["open"] == 15 and 14 <= d["fractional_weak"] <= 18
    assert d["ratio_weak"] == pytest.approx(0.698, abs=0.003) and d["ratio_strong"] == pytest.approx(0.717, abs=0.003) and 0.92 <= d["ratio_bound"] <= 0.945
    assert 0.74 <= d["closed_bound"] <= 0.82 and 20 <= d["n_cuts"] <= 32 and 2 <= d["rounds"] <= 4 and d["converged"]
    assert 1800 <= d["upper"] <= 1850 and 1.01 <= d["ratio_upper"] <= 1.04
    h = ev.verdict(ev.analyse(P._replace(fix=120)))[2]
    assert h["opt"] == 3996.0 and h["ratio_weak"] == pytest.approx(0.562, abs=0.003) and h["ratio_strong"] == pytest.approx(0.583, abs=0.003) and 0.95 <= h["ratio_bound"] <= 0.98 and 0.90 <= h["closed_bound"] <= 0.95
    assert 1.12 <= h["ratio_upper"] <= 1.16                       # Aufrunden bei hohen Fixkosten: etwa 14 % über dem Optimum


def test_distribution_default_net(dist):
    """Distributionsnetze (drei Güter, Fixkosten 30, Auslastung 50 %, 40 feste Netze, 34 lieferbar): schwache Schranke im Mittel 70,7 % des Optimums (schlechtestes Netz 61,8 %), stark 73,3 % (schließt 9 % der Lücke),
    mit gekappten und gerundeten Schnitten 96,5 % (schlechtestes 92,6 %, schließt im Mittel 88 %, im Median 89 % der Lücke); im Mittel etwa 28 Schnitte in 3 Runden; nie ganz exakt; Aufrunden 5 % über dem Optimum."""
    assert dist["n_seeds"] == 40 and 33 <= dist["n_feasible"] <= 35
    assert 0.69 <= dist["weak_mean"] <= 0.72 and 0.60 <= dist["weak_min"] <= 0.64 and 0.72 <= dist["strong_mean"] <= 0.745 and 0.06 <= dist["closed_strong_mean"] <= 0.12
    assert 0.955 <= dist["cuts_mean"] <= 0.975 and 0.91 <= dist["cuts_min"] <= 0.94 and 0.86 <= dist["closed_cuts_mean"] <= 0.90 and 0.86 <= dist["closed_cuts_median"] <= 0.92
    assert 24 <= dist["n_cuts_mean"] <= 32 and 2.8 <= dist["rounds_mean"] <= 3.8 and dist["exact_share"] <= 0.06 and 1.03 <= dist["upper_mean"] <= 1.07


def test_highs_solves_these_nets_at_the_root(dist):
    """HiGHS braucht für jedes lieferbare Netz höchstens einen Knoten (eigene Schnitte, Vorverarbeitung): mit ihm lässt sich die Schranke nicht vergleichen."""
    nodes = [ev.analyse(ev.with_seed(P, s), ev.Opts("strong", "none")).opt.nodes for s in C.QUALITY_SEEDS if ev.analyse(ev.with_seed(P, s), ev.Opts("strong", "none")).feasible]
    assert len(nodes) == dist["n_feasible"] and max(nodes) <= 1


def test_grid_numbers():
    """Streckennetz (Gitter 4 x 3, drei Güter, Fixkosten 10, Seed 6): Optimum 245 mit 9 von 16 Strecken offen; schwach 82,7 %, stark 91,7 %, mit fünf Schnitten in einer Runde 98,0 %; Aufrunden 12 % darüber.
    Über 40 feste Streckennetze (30 lieferbar): schwach 73,5 %, stark 95,6 % (schließt 82 % der Lücke), mit Schnitten 96,0 % (im Mittel weniger als ein Schnitt) - auf Gittern trägt die starke Kopplung."""
    d = ev.verdict(ev.analyse(GRID))[2]
    assert d["opt"] == 245.0 and d["groups"] == 16 and d["open"] == 9 and d["ratio_weak"] == pytest.approx(0.827, abs=0.003) and d["ratio_strong"] == pytest.approx(0.917, abs=0.003)
    assert 0.97 <= d["ratio_bound"] <= 0.99 and 3 <= d["n_cuts"] <= 8 and d["rounds"] == 1 and 1.10 <= d["ratio_upper"] <= 1.14
    g = ev.distribution(GRID)
    assert 28 <= g["n_feasible"] <= 32 and 0.72 <= g["weak_mean"] <= 0.75 and 0.94 <= g["strong_mean"] <= 0.97 and 0.78 <= g["closed_strong_mean"] <= 0.85
    assert 0.95 <= g["cuts_mean"] <= 0.975 and g["n_cuts_mean"] < 1.0 and g["cuts_mean"] - g["strong_mean"] < 0.02


def test_fixed_cost_and_load_sweeps():
    """Fixkosten-Basis 5 / 10 / 20 / 40 / 80 / 150 (16 feste Netze): schwache Schranke 90 / 83 / 75 / 67 / 59 / 54 %, mit Schnitten stets 97 bis 98 %. Auslastung 30 / 50 / 70 / 90 %: schwach 50 / 70 / 80 / 85 %, stark 62 / 73 / 81 / 85 %, mit Schnitten 97 bis 98 %."""
    fx = ev.sweep_table(P, "fix", C.FIXES)
    assert [round(100 * r["weak"]) for r in fx] == pytest.approx([90, 83, 75, 67, 59, 54], abs=2)
    assert all(0.96 <= r["cuts"] <= 0.99 for r in fx) and [r["weak"] for r in fx] == sorted((r["weak"] for r in fx), reverse=True)
    assert 0.92 <= fx[-1]["closed"] <= 0.96 and fx[-1]["closed"] > fx[0]["closed"]        # bei Fixkosten 150 schließen die Schnitte 94 % der Lücke, bei 5 weniger
    ld = ev.sweep_table(P, "load", C.LOADS)
    assert [round(100 * r["weak"]) for r in ld] == pytest.approx([50, 70, 80, 85], abs=2) and [round(100 * r["strong"]) for r in ld] == pytest.approx([62, 73, 81, 85], abs=2)
    assert all(0.96 <= r["cuts"] <= 0.99 for r in ld) and [r["weak"] for r in ld] == sorted(r["weak"] for r in ld) and 3 <= ld[-1]["n"] <= 6      # bei 90 % nur wenige lieferbare Netze


def test_cut_modes():
    """Schnittformen (16 feste Netze, stark): keine und Kapazitätsschnitt 72,6 % (der Kapazitätsschnitt ist schon im schwachen LP enthalten, ohne einen einzigen Schnitt), gekappt 96,8 %, gekappt und gerundet 97,0 %;
    die falsch gerundete Form ist in allen 15 Netzen ungültig (LP unlösbar)."""
    t = ev.mode_table(P)
    assert t["n"] == 15 and t["none"]["ratio"] == pytest.approx(0.7256, abs=0.003) and t["plain"]["ratio"] == pytest.approx(t["none"]["ratio"]) and t["plain"]["cuts"] == 0
    assert 0.96 <= t["cap"]["ratio"] <= 0.975 and 0.962 <= t["round"]["ratio"] <= 0.978 and 0.0 <= t["round"]["ratio"] - t["cap"]["ratio"] <= 0.01
    assert t["wrong"]["invalid"] == 15 and t["round"]["invalid"] == 0 and t["cap"]["invalid"] == 0


def test_search_tree():
    """Eigener Branch-and-Bound (10 feste Netze, 9 lieferbar, gleiche Startlösung): Knoten im Median schwach 705, stark 647, stark + Schnitte 23 - der Baum schrumpft auf etwa 3 %; alle bewiesen."""
    t = ev.tree_table(P)
    assert t["n"] == 9 and all(t[k]["proven"] == 9 for k in ("weak", "strong", "cuts"))
    assert 500 <= t["weak"]["median"] <= 900 and 450 <= t["strong"]["median"] <= 850 and 10 <= t["cuts"]["median"] <= 45
    assert t["cuts"]["median"] < 0.08 * t["weak"]["median"] and 0.80 <= t["strong"]["median"] / t["weak"]["median"] <= 0.98      # die starke Kopplung spart im Median nur etwa 8 %


def test_separation_and_sizes():
    """Trennung: Kandidatenmengen mit lokaler Suche erreichen auf kleinen Netzen (13 lieferbare) 95,1 % des Optimums, das Aufzählen aller Knotenmengen 96,8 % (in 9 von 13 mehr). Größe: Gruppen 9 / 23 / 42 / 70,
    Lücke geschlossen 99,8 / 89,8 / 83,2 / 77,7 %, Anteil am Optimum 100 / 97,0 / 94,1 / 91,8 %."""
    s = ev.separation_table()
    assert s["n"] == 13 and 0.94 <= s["heuristic"] <= 0.96 and 0.96 <= s["exact"] <= 0.975 and 7 <= s["exact_better"] <= 12
    sz = ev.size_table()
    assert [round(r["groups"]) for r in sz] == pytest.approx([10, 23, 42, 70], abs=2)
    closed = [r["closed"] for r in sz]
    assert closed[0] >= 0.95 and 0.85 <= closed[1] <= 0.93 and 0.78 <= closed[2] <= 0.88 and 0.70 <= closed[3] <= 0.84 and closed[1] > closed[2] > closed[3]
    assert sz[0]["ratio"] >= 0.99 and 0.95 <= sz[1]["ratio"] <= 0.985 and 0.92 <= sz[2]["ratio"] <= 0.96 and 0.88 <= sz[3]["ratio"] <= 0.94


def test_every_stage_is_a_valid_bound_and_the_round_up_a_valid_solution():
    """Auf allen 40 festen Netzen: schwach <= stark <= mit Schnitten <= Optimum <= aufgerundet."""
    for seed in C.QUALITY_SEEDS:
        a = ev.analyse(ev.with_seed(P, seed))
        if not a.feasible:
            continue
        assert a.weak.objective <= a.strong.objective + 1e-6 <= a.bound + 1e-6 <= a.opt.objective + 2e-6 and a.upper >= a.opt.objective - 1e-6
