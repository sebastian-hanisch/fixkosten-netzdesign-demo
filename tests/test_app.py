"""Rauchtests der Streamlit-Oberfläche per AppTest: Standard, jedes Preset, alle Optionen, Randgrößen, Schnittrunden-Regler, ausgeblendete Regler, Permalink, Experimente auf Abruf, Schlüssel und Achsensperre."""

import itertools
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import fcn_constants as C
from fcn_presets import PRESET_KEYS

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"

# Anfang der Meldung zum gezeigten Netz (Streamlit legt das führende Emoji in `icon`, nicht in `value`)
EXPECTED = {
    "🚚 Zufallsnetz": "Optimum 1784,0 (15 von 27 Kanten offen). Die schwache Schranke liegt bei **69,8 %**",
    "🗺️ Streckennetz": "Optimum 245,0 (9 von 16 Kanten offen). Die schwache Schranke liegt bei **82,7 %**",
    "💸 Big-M-Falle": "Optimum 15,0 (1 von 2 Kanten offen). Die schwache Schranke liegt bei **26,7 %**",
    "🔁 Rundungs-Falle": "Optimum 23,0 (2 von 2 Kanten offen). Die schwache Schranke liegt bei **78,3 %**",
    "📦 Bündelung": "Optimum 11,0 (3 von 5 Kanten offen). Die schwache Schranke liegt bei **59,1 %**",
    "🏗️ Hohe Fixkosten": "Optimum 3996,0 (12 von 27 Kanten offen). Die schwache Schranke liegt bei **56,2 %**",
    "🧊 Schwache Formulierung": "Optimum 1784,0 (15 von 27 Kanten offen). Die schwache Schranke liegt bei **69,8 %**",
    "🚫 Falsche Schnitte": "Die falsch gerundeten Schnitte schneiden zulässige Entwürfe ab:",
}
OPTION_LABELS = {"Kopplung", "Schnitte"}


def _run(setup=None, timeout=900):
    at = AppTest.from_file(str(APP), default_timeout=timeout)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    if setup is not None:
        setup(at)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def _apply(at, p):
    for key, state_key in PRESET_KEYS.items():
        at.session_state[state_key] = p[key]


def _labels(at):
    return {w.label for w in list(at.sidebar.slider) + list(at.sidebar.selectbox) + list(at.sidebar.number_input) + list(at.sidebar.radio)}


def _texts(at):
    return [e.value for e in list(at.success) + list(at.warning) + list(at.info) + list(at.error)]


def _has(at, prefix):
    return any(t.startswith(prefix) for t in _texts(at))


def _metric(at, label):
    return [m.value for m in at.metric if m.label == label]


def _round_slider(at):
    found = [s for s in at.slider if s.key == "fcn_round"]
    return found[0] if found else None


def test_default_renders_without_exception():
    at = _run()
    assert any("Die Schranke Stufe für Stufe" in m.value for m in at.markdown)
    assert _has(at, EXPECTED["🚚 Zufallsnetz"]) and not at.error
    assert _metric(at, "Optimum (ganzzahlig)")[0] == "1784,0" and _metric(at, "Schwach")[0] == "69,8 %" and _metric(at, "Stark")[0] == "71,7 %" and _metric(at, "Mit Schnitten")[0].endswith("%")
    assert _metric(at, "Exakt")[0].endswith("%") and _round_slider(at).value == _round_slider(at).max >= 2


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_renders_with_its_verdicts(name):
    at = _run(lambda a: _apply(a, C.PRESETS[name]))
    assert _has(at, EXPECTED[name]), _texts(at)
    if C.PRESETS[name]["net"] in C.FIXED_NETS:
        assert any(t.startswith("Festes Netz") for t in _texts(at))
    else:
        assert any(m.value.startswith("**40 feste") for m in at.markdown)


@pytest.mark.parametrize("K", range(C.K_MIN, C.K_MAX + 1))
@pytest.mark.parametrize("net", ["random", "grid"])
def test_every_number_of_goods_renders(net, K):
    def setup(at):
        at.session_state["net_select"] = net
        at.session_state["k_slider"] = K
    at = _run(setup)
    assert not at.error and (_has(at, "Optimum") or _has(at, "Dieses Netz kann"))


@pytest.mark.parametrize("coupling,cuts", list(itertools.product(C.COUPLINGS, C.CUT_MODES)))
def test_every_coupling_and_cut_mode_renders(coupling, cuts):
    def setup(at):
        at.session_state["coupling_radio"] = coupling
        at.session_state["cuts_radio"] = cuts
    at = _run(setup)
    assert len(_texts(at)) >= 1 and (cuts == "wrong") == bool(at.error)


def test_extreme_sizes_render():
    for net, vals in (("random", (("p_slider", C.P_MIN), ("d_slider", C.D_MIN), ("s_slider", C.S_MIN), ("density_slider", C.DENSITY_MIN), ("spread_slider", C.SPREAD_MIN), ("load_slider", C.LOAD_MIN), ("k_slider", C.K_MIN), ("fix_slider", C.FIX_MIN))),
                      ("random", (("p_slider", C.P_MAX), ("d_slider", C.D_MAX), ("s_slider", C.S_MAX), ("density_slider", C.DENSITY_MAX), ("spread_slider", C.SPREAD_MAX), ("load_slider", C.LOAD_MAX), ("k_slider", C.K_MAX), ("fix_slider", C.FIX_MAX))),
                      ("grid", (("gw_slider", C.GW_MIN), ("gh_slider", C.GH_MIN), ("gdensity_slider", C.GDENSITY_MIN), ("gcap_slider", C.GCAP_MIN), ("gdem_slider", C.GDEM_MIN), ("k_slider", C.K_MIN))),
                      ("grid", (("gw_slider", C.GW_MAX), ("gh_slider", C.GH_MAX), ("gdensity_slider", C.GDENSITY_MAX), ("gcap_slider", C.GCAP_MAX), ("gdem_slider", C.GDEM_MAX), ("k_slider", C.K_MAX)))):
        def setup(at, net=net, vals=vals):
            at.session_state["net_select"] = net
            for key, value in vals:
                at.session_state[key] = value
        at = _run(setup)
        assert not at.error


def test_a_net_that_cannot_deliver_renders_and_says_so():
    """Seed 13 im Standardnetz: die Nachfrage lässt sich auch mit allen Kanten offen nicht decken - Hinweis, kein Absturz."""
    at = _run(lambda a: a.session_state.__setitem__("seed_input", 13))
    assert any("kann die Nachfrage nicht decken" in t for t in _texts(at))


def test_round_slider_moves_through_all_rounds():
    at = _run()
    top = int(_round_slider(at).max)
    for value in range(top + 1):
        _round_slider(at).set_value(value)
        at.run()
        assert not at.exception and _round_slider(at).value == value


def test_hidden_controls_keep_their_values_across_a_net_switch():
    at = _run()
    at.sidebar.slider(key="fix_slider").set_value(80)
    at.run()
    at.sidebar.selectbox(key="net_select").set_value("bigm")
    at.run()
    assert not at.exception and not [w for w in at.sidebar.slider if w.key == "fix_slider"]
    at.sidebar.selectbox(key="net_select").set_value("random")
    at.run()
    assert at.sidebar.slider(key="fix_slider").value == 80 and not at.exception


def test_permalink_settings_are_loaded_and_clamped():
    at = AppTest.from_file(str(APP), default_timeout=900)
    at.query_params["net"] = "grid"
    at.query_params["k"] = "9"
    at.query_params["fix"] = "12"
    at.query_params["coupling"] = "weak"
    at.query_params["cuts"] = "cap"
    at.run()
    assert not at.exception
    assert at.sidebar.selectbox(key="net_select").value == "grid" and at.sidebar.slider(key="k_slider").value == C.K_MAX and at.sidebar.slider(key="fix_slider").value == 10       # 12 rastet auf den Schritt 5 ein
    assert at.sidebar.radio(key="coupling_radio").value == "weak" and at.sidebar.radio(key="cuts_radio").value == "cap"
    assert at.query_params["net"] == ["grid"] or at.query_params["net"] == "grid"


def test_option_controls_exist():
    assert OPTION_LABELS <= _labels(_run())


@pytest.mark.parametrize("button,text", [("sweep_start", "Fixkosten-Basis wächst"), ("modes_start", "Der Kapazitätsschnitt ist schon im schwachen LP"), ("limits_start", "Mit wachsender Größe bleibt nach den Schnitten mehr Lücke")])
def test_experiments_run_on_demand(button, text, monkeypatch):
    monkeypatch.setattr(C, "SWEEP_SEEDS", C.SWEEP_SEEDS[:4])
    monkeypatch.setattr(C, "SEPARATION_SEEDS", C.SEPARATION_SEEDS[:5])
    monkeypatch.setattr(C, "SIZES", C.SIZES[:2])
    at = _run()
    assert not any(t.startswith(text) for t in [m.value for m in at.markdown])
    next(b for b in at.button if b.key == button).click().run()
    assert not at.exception
    assert any(text in m.value for m in list(at.markdown) + list(at.caption)) or any(text in " ".join(str(c) for c in t.value) for t in at.table) or any(text in str(t.value) for t in at.table)


def test_tree_experiment_runs_on_demand(monkeypatch):
    monkeypatch.setattr(C, "TREE_SEEDS", C.TREE_SEEDS[:2])
    monkeypatch.setattr(C, "NODE_LIMIT", 400)
    at = _run()
    next(b for b in at.button if b.key == "tree_start").click().run()
    assert not at.exception and any("Cut-and-Branch" in c.value for c in at.caption)


def test_experiments_need_a_random_net():
    at = _run(lambda a: a.session_state.__setitem__("net_select", "bundle"))
    assert not [b for b in at.button if b.key in ("tree_start", "sweep_start", "modes_start")] and sum(1 for t in _texts(at) if t.startswith("Für dieses Experiment")) == 3


def test_source_has_explicit_chart_keys_and_locked_axes():
    app = APP.read_text(encoding="utf-8")
    import re
    assert all(re.search(r"plotly_chart\(.*key=", line) for line in app.splitlines() if "st.plotly_chart(" in line)
    viz = (ROOT / "fcn_visualization.py").read_text(encoding="utf-8")
    assert viz.count("return lock_axes(fig)") >= 8 and "def lock_axes" in viz
