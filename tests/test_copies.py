"""Die aus den Vorgänger-Demos kopierten Netzgeneratoren (`fcn_scenario.py`, `fcn_model.py`) sind bewacht: dieselben Zahlen wie in garg-koenemann-demo und multicommodity-demo."""

import fcn_model as md
import fcn_scenario as sc


def test_splitmix64_stream_is_the_portfolio_standard():
    rng = sc.SplitMix64(1)
    assert [rng.next() for _ in range(2)] == [10451216379200822465, 13757245211066428519]


def test_distribution_net_of_the_predecessors():
    """Standardnetz mit Auslastung 90 % (Seed 155, drei Güter): 76 Einheiten Nachfrage, 38 Kanten, 19 Knoten - wie in garg-koenemann-demo."""
    m = md.generate_mcf(3, 3, 8, 60, 50, 90, 155, 3)
    assert (m.total_demand(), m.net.m, m.net.n, m.K) == (76, 38, 19, 3)


def test_grid_of_the_predecessors():
    """Gitter 5 x 4 (Dichte 70 %, Kapazität 2, Menge 4, vier Güter, Seed 7): 64 Kanten einschließlich der Auftragskanten, 22 Knoten."""
    g = md.generate_grid(5, 4, 70, 2, 4, 4, 7)
    assert (g.net.m, g.net.n, g.K, g.total_demand()) == (64, 22, 4, 12)
