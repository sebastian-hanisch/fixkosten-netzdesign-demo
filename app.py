"""Fixkosten-Netzdesign – warum die Schranke schwach ist und was Schnitte ändern – interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo EINE Frage - warum die LP-Schranke beim Netzwerkdesign mit Fixkosten so schwach ist und was stärkere Formulierung
und Schnittungleichungen daran ändern - und lässt stattdessen das Beispiel wachsen.
Zehntes Stück der Netzwerkfluss-Linie der "Konzepte"-Reihe, erstes im Netzwerkdesign-Ast: dasselbe Mehrgütermodell wie die Vorgänger, aber jede Kante muss erst geöffnet werden (Fixkosten, Ja/Nein). Siehe README für die Einordnung.

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import fcn_constants as C
import fcn_evaluation as ev
from fcn_presets import (
    KEPT,
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    seed_widget,
    sync_query_params,
)
from fcn_visualization import (
    build_design_map,
    build_dist,
    build_levels,
    build_modes,
    build_rounds,
    build_sizes,
    build_sweep,
    build_tree,
)

st.set_page_config(page_title="Fixkosten-Netzdesign – Sebastian Hanisch", layout="wide")


def _pct(x, digits=1):
    return "–" if x is None or x != x else f"{100 * x:.{digits}f} %".replace(".", ",")


def _f(x, digits=1):
    return "–" if x is None or x != x else f"{x:.{digits}f}".replace(".", ",")


def _n(x):
    return f"{int(round(x)):,}".replace(",", " ")


@st.cache_resource(show_spinner=False, max_entries=48)
def _analysis(params, opts):
    return ev.analyse(params, opts)


@st.cache_resource(show_spinner=False, max_entries=8)
def _distribution(params):
    return ev.distribution(params)


st.title("🏗️ Fixkosten-Netzdesign – warum die Schranke schwach ist")
st.markdown(
    """
Welche Lanes und Verteilzentren soll ein Netz **öffnen**, damit die Nachfrage aller Güter gedeckt wird - zu den geringsten Gesamtkosten aus **Fixkosten** (offen oder nicht) und Stückkosten? Das ist ein gemischt-ganzzahliges Programm, und sein Kern ist der Mehrgüterfluss der Vorgänger.
Die übliche Relaxation lässt eine Kante zu einem Bruchteil $y\\in[0,1]$ offen sein - und zahlt dann nur diesen Bruchteil der Fixkosten. Eine Lane, die im Fluss zu 10 % ausgelastet ist, kostet im LP nur 10 % ihrer Fixkosten: **die Schranke ist schwach**.
Diese Demo misst, wie schwach sie ist, und was zwei Verbesserungen bringen: eine **stärkere Kopplung** zwischen Fluss und Entscheidung und **Schnittungleichungen**, die aus den Min-Cuts des Netzes entstehen - gemessen an der Größe des Suchbaums, den ein Branch-and-Bound danach braucht.
"""
)
st.caption(
    "Anders als die Fall-Demos im Portfolio, die an einem Anwendungsfall mehrere Verfahren vergleichen, zeigt diese Demo - zehntes Stück der Netzwerkfluss-Linie der \"Konzepte\"-Reihe, erstes im Netzwerkdesign-Ast - **eine Frage** an einem wachsenden Beispiel. "
    "Verwandt: [linehaul-demo](https://github.com/sebastian-hanisch/linehaul-demo) (dasselbe Modell, dort Heuristiken gegen SCIP) und die Schnittebenen am Rucksack in cutting-planes-demo und branch-cut-demo. "
    "Die Folgestücke: **Benders-Zerlegung** (gebaut: [benders-demo](https://github.com/sebastian-hanisch/benders-demo)) und **Slope Scaling** (gebaut: [slope-scaling-demo](https://github.com/sebastian-hanisch/slope-scaling-demo); Heuristik für große Netze)."
)

with st.expander("So entsteht die Schranke", expanded=True):
    st.markdown(
        r"""
1. **Modell:** Entwurf $y_g\in\{0,1\}$ je Lane (im Streckennetz je Strecke), Fluss $x^k_e\ge 0$ je Gut. Minimiere $\sum_g f_g y_g+\sum_{k,e}c^k_e x^k_e$, Flusserhaltung je Gut, die volle Nachfrage wird geliefert.
2. **Schwach:** $\sum_k x^k_e\le u_e\,y_g$ - im LP genügt $y=\text{Fluss}/u$: Fixkosten nur anteilig.
3. **Stark:** zusätzlich $x^k_e\le\min(u_e,d_k)\,y_g$ je Gut ($d_k$ = Nachfrage des Guts, mehr kann nie fließen). Das schließt die Big-M-Lücke einzelner Kanten.
4. **Schnitte:** für eine Knotenmenge $W$ muss mindestens $R(W)$ Einheiten hineinfließen (Nachfrage in $W$ minus Angebot in $W$). Alles läuft über die Kanten, die $W$ betreten - und nur offene Kanten tragen: $\sum_e \min(u_e,R)\,y_e\ge R$ (**gekappt**), mit Teiler $\delta$ gerundet $\sum_e\lceil\min(u_e,R)/\delta\rceil\,y_e\ge\lceil R/\delta\rceil$ (**Chvátal-Gomory**). Gültig für jeden ganzzahligen Entwurf.
5. **Trennung:** verletzte Schnitte finden wir über Min-Cuts zu den Nachfrageknoten (Kapazität $u_e y_e$), deren Vereinigungen und eine lokale Suche - eine Heuristik, denn die exakte Trennung über alle Knotenmengen wächst exponentiell.
6. **Schleife:** LP lösen, verletzte Schnitte hinzufügen, neu lösen - bis keine mehr verletzt ist. Danach beweist das Optimum ein Branch-and-Bound (hier auch ein eigener, damit man die Knoten zählen kann).
        """
    )

st.caption("🎯 Schnellstart – ein Beispielnetz laden:")
names = list(C.PRESETS.keys())
for row in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[row:row + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()


def _kept(key, default):
    return int(st.session_state.get(KEPT[key], default))


def _slider(label, key, help, step=None):
    kw = {"step": step} if step else {}
    seed_widget(key)
    value = st.slider(label, *bounds(key), key=key, help=help, **kw)
    st.session_state[KEPT[key]] = value
    return value


with st.sidebar:
    st.header("⚙️ Einstellungen")
    net_key = st.selectbox(
        "Netz", list(C.NETS), key="net_select", format_func=lambda k: C.NETS[k],
        help="Das Distributionsnetz der Vorgänger (dreistufig: Werke, Verteilzentren, Filialen), ein Streckennetz (Gitter mit Start-Ziel-Aufträgen) oder eines von drei festen Lehrnetzen, an denen sich je ein Effekt von Hand nachrechnen lässt.",
    )
    show_dist, show_grid = net_key == "random", net_key == "grid"
    if show_dist or show_grid:
        K = _slider("Zahl der Güter", "k_slider", "Frische, Trocken, Kühl, Getränke, Tiefkühl (in dieser Reihenfolge). Im Distributionsnetz stellt jedes Werk jedes Gut her; im Streckennetz hat jedes Gut einen eigenen Start und ein eigenes Ziel.")
        fix = _slider("Fixkosten je Lane (Basis)", "fix_slider", "Jede Lane (im Streckennetz jede Strecke) kostet die Basis mal 1 bis 3, ein Verteilzentrum das Doppelte. Zum Vergleich: die Stückkosten je Einheit liegen bei 1 bis 9.", step=5)
    else:
        K = _kept("k_slider", C.DEFAULT_K)
        fix = _kept("fix_slider", C.DEFAULT_FIX)
    if show_dist:
        p = _slider("Werke", "p_slider", "Anzahl der Werke (oben im Netz).")
        d = _slider("Verteilzentren", "d_slider", "Anzahl der Verteilzentren; Durchsatz gemeinsam für alle Güter.")
        s = _slider("Filialen", "s_slider", "Anzahl der Filialen (unten im Netz).")
        density = _slider("Netzdichte [%]", "density_slider", "Anteil der möglichen Lanes, die es gibt.", step=10)
        spread = _slider("Streuung der Lane-Breiten [%]", "spread_slider", "0 = alle Lanes einer Stufe gleich breit, 100 = Kapazitäten gleichverteilt von 1 bis zum Doppelten der Grundbreite.", step=25)
        load = _slider("Auslastung [% der Werkskapazität]", "load_slider", "Gesamtnachfrage der Filialen (alle Güter zusammen) in Prozent der Werkskapazität. Je kleiner, desto mehr Reserve haben die Lanes - und desto schwächer die Kopplung.", step=10)
        seed_widget("seed_input")
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.session_state[KEPT["seed_input"]] = seed
        st.button("🎲 Neues Netz generieren", width="stretch", on_click=randomize_seed, args=("seed_input",), help="Würfelt einen neuen Zufalls-Seed. Die Verteilungen über 40 feste Netze weiter unten ändern sich dabei nicht - nur die Marke „Ihre Ziehung“.")
    else:
        p, d, s = _kept("p_slider", C.DEFAULT_P), _kept("d_slider", C.DEFAULT_D), _kept("s_slider", C.DEFAULT_S)
        density, spread, load, seed = _kept("density_slider", C.DEFAULT_DENSITY), _kept("spread_slider", C.DEFAULT_SPREAD), _kept("load_slider", C.DEFAULT_LOAD), _kept("seed_input", C.DEFAULT_SEED)
    if show_grid:
        gw = _slider("Breite des Gitters", "gw_slider", "Knoten je Zeile.")
        gh = _slider("Höhe des Gitters", "gh_slider", "Knoten je Spalte.")
        gdensity = _slider("Anteil der Gitterkanten [%]", "gdensity_slider", "Ein zufälliger Spannbaum hält das Netz zusammenhängend; jede weitere Gitterkante gibt es mit diesem Anteil. 100 % = volles Gitter.", step=10)
        gcap = _slider("Größte Kapazität je Kante", "gcap_slider", "Jede Kante trägt in beide Richtungen 1 bis zu diesem Wert, gemeinsam für alle Güter.")
        gdem = _slider("Größte Menge je Gut", "gdem_slider", "Jedes Gut fährt 1 bis zu diesem Wert von seinem Start zu seinem Ziel.")
        seed_widget("gseed_input")
        gseed = st.number_input("Zufalls-Seed (Streckennetz)", *bounds("gseed_input"), key="gseed_input", step=1)
        st.session_state[KEPT["gseed_input"]] = gseed
        st.button("🎲 Neues Netz generieren", width="stretch", on_click=randomize_seed, args=("gseed_input",), key="rand_grid", help="Würfelt einen neuen Zufalls-Seed für das Streckennetz.")
    else:
        gw, gh, gdensity = _kept("gw_slider", C.DEFAULT_GW), _kept("gh_slider", C.DEFAULT_GH), _kept("gdensity_slider", C.DEFAULT_GDENSITY)
        gcap, gdem, gseed = _kept("gcap_slider", C.DEFAULT_GCAP), _kept("gdem_slider", C.DEFAULT_GDEM), _kept("gseed_input", C.DEFAULT_GSEED)
    if not (show_dist or show_grid):
        st.caption("Dieses Netz ist fest - es gibt nichts zu erzeugen. Die Regler für Güter, Größe, Fixkosten und Seed gehören zu den zufälligen Netzen.")
    st.subheader("Formulierung")
    coupling = st.radio("Kopplung", list(C.COUPLINGS), key="coupling_radio", format_func=lambda k: C.COUPLINGS[k],
                        help="Wie eng der Fluss an die Entscheidung gebunden ist. Schwach: nur die Summe der Güter je Kante. Stark: zusätzlich jedes Gut einzeln gegen min(Kapazität, Nachfrage). Beide haben dasselbe ganzzahlige Optimum.")
    cuts_mode = st.radio("Schnitte", list(C.CUT_MODES), key="cuts_radio", format_func=lambda k: C.CUT_MODES[k],
                         help="Welche Schnittform die Schleife benutzt. Nur der Kapazitätsschnitt ist schon im schwachen LP enthalten (bringt nichts); gekappt und gerundet sind gültig und stärker. Die Negativkontrolle rundet falsch und macht das Problem unlösbar.")

sync_query_params({"net_select": net_key, "k_slider": int(K), "p_slider": int(p), "d_slider": int(d), "s_slider": int(s), "density_slider": int(density), "spread_slider": int(spread),
                   "load_slider": int(load), "fix_slider": int(fix), "seed_input": int(seed), "gw_slider": int(gw), "gh_slider": int(gh), "gdensity_slider": int(gdensity), "gcap_slider": int(gcap),
                   "gdem_slider": int(gdem), "gseed_input": int(gseed), "coupling_radio": coupling, "cuts_radio": cuts_mode})

params = ev.normalise(ev.NetParams(net_key, int(K), int(p), int(d), int(s), int(density), int(spread), int(load), int(fix), int(seed), int(gw), int(gh), int(gdensity), int(gcap), int(gdem), int(gseed)))
opts = ev.Opts(coupling, cuts_mode)
with st.spinner("Rechne..."):
    a = _analysis(params, opts)
design = a.design
level, code, dat = ev.verdict(a)
is_fixed = net_key in C.FIXED_NETS

# --- Die Schranke Stufe für Stufe ---------------------------------------------------------------------------------------------------

st.markdown("## 🏗️ Die Schranke Stufe für Stufe")
if not a.feasible:
    st.warning("⚠️ Dieses Netz kann die Nachfrage nicht decken, auch wenn alle Kanten offen sind - es gibt nichts zu entwerfen. Weniger Auslastung, mehr Lanes oder ein anderer Seed hilft.")
    st.stop()

opt = dat["opt"]
lab = C.CUT_MODES[cuts_mode].split(" (")[0]
m1, m2, m3, m4 = st.columns(4)
m1.metric("Optimum (ganzzahlig)", _f(opt, 1), delta=f"{dat['open']} von {dat['groups']} Kanten offen", delta_color="off", help="Die beste Wahl der offenen Kanten samt Fluss: das exakte MIP (HiGHS). Fixkosten + Stückkosten.")
m2.metric("Schwach", _pct(dat["ratio_weak"]), delta=f"{dat['fractional_weak']} Kanten gebrochen", delta_color="off", help="LP-Schranke der schwachen Kopplung als Anteil am Optimum.")
m3.metric("Stark", _pct(dat["ratio_strong"]), delta=f"schließt {_pct(dat['closed_strong'], 0)} der Lücke", delta_color="off", help="Zusätzlich x ≤ min(u, d)·y je Gut. Anteil am Optimum; darunter der Anteil der Lücke zwischen schwach und Optimum, den sie schließt.")
if a.cuts is not None:
    m4.metric("Mit Schnitten", _pct(dat["ratio_bound"]) if dat["ratio_bound"] != float("inf") else "unlösbar", delta=f"{dat['n_cuts']} Schnitte in {dat['rounds']} Runden", delta_color="off",
              help=f"Schnittform: {lab}. Anteil am Optimum nach der Schnittschleife.")
else:
    m4.metric("Mit Schnitten", "–", delta="Schnitte aus", delta_color="off", help="Unter „Schnitte“ links eine Form wählen.")

if code == "ok":
    text = (f"✅ Optimum {_f(opt, 1)} ({dat['open']} von {dat['groups']} Kanten offen). Die schwache Schranke liegt bei **{_pct(dat['ratio_weak'])}**, die starke bei {_pct(dat['ratio_strong'])}"
            + (f", mit Schnitten ({lab}) bei **{_pct(dat['ratio_bound'])}** - sie schließen {_pct(dat['closed_bound'], 0)} der Lücke ({dat['n_cuts']} Schnitte, {dat['rounds']} Runden). " if a.cuts is not None else ". ")
            + f"Aufrunden (jede angebrochene Kante öffnen, Fluss neu wählen) liefert eine Lösung {_pct(dat['ratio_upper'] - 1)} über dem Optimum.")
    st.success(text)
elif code == "trivial":
    st.info(f"Hier ist schon die schwache Schranke exakt ({_f(dat['weak'], 1)}): jede offene Kante ist voll ausgelastet oder der Fluss braucht sie ganz. Die Lücke, um die es geht, entsteht bei Kanten mit Reserve.")
else:
    why = "macht das LP unlösbar" if dat["infeasible_cuts"] else f"treibt die Schranke auf {_pct(dat['ratio_bound'])} des Optimums"
    st.error(f"❌ Die falsch gerundeten Schnitte schneiden zulässige Entwürfe ab: die Schleife {why}. Eine Schnittungleichung muss für **jeden** ganzzahligen Entwurf gelten - hier fordert sie eine Einheit mehr, als es je zu decken gibt.")

lp_shown = a.shown
opt_open = {g for g in range(design.G) if a.opt.y[g] > 0.5}
c1, c2 = st.columns([3, 2])
with c1:
    st.markdown(f"**Der LP-Entwurf** ({C.COUPLINGS[coupling].split(':')[0]}{', mit Schnitten' if a.cuts is not None else ''}) und das ganzzahlige Optimum (rote Unterlage)")
    st.plotly_chart(build_design_map(design, lp_shown, opt_open), width="stretch", key="design_map")
with c2:
    st.markdown("**Schranken je Stufe** als Anteil am Optimum")
    values = [("schwach", dat["weak"]), ("stark", dat["strong"])]
    if a.cuts is not None:
        values.append(("stark + Schnitte" if coupling == "strong" else "schwach + Schnitte", a.bound if dat["ratio_bound"] != float("inf") else 10 * opt))
    st.plotly_chart(build_levels(values, opt, a.upper), width="stretch", key="levels_chart")
st.caption("Blau = ganz offen, orange gestrichelt = anteilig offen (Beschriftung: y), grau = geschlossen; rote Unterlage = im ganzzahligen Optimum offen. Im LP sind viele Kanten nur anteilig offen und zahlen entsprechend wenig Fixkosten - das ist die Lücke. "
           "Rechts: jede Stufe ist eine gültige untere Schranke, das Optimum liegt bei 100 %; gepunktet die obere Schranke aus dem Aufrunden.")

st.markdown("---")

# --- Schnittrunden -------------------------------------------------------------------------------------------------------------------

st.markdown("## ✂️ Schnittrunde für Schnittrunde")
if a.cuts is None:
    st.info("Links unter „Schnitte“ eine Form wählen, dann läuft die Schleife und ihre Runden erscheinen hier.")
elif a.cuts.infeasible:
    st.info(f"Schon die ersten {len(a.cuts.cuts)} Schnitte machen das LP unlösbar: sie fordern mehr, als bei geöffneten Kanten je zu liefern ist. Es gibt keine weitere Runde.")
elif len(a.cuts.rounds) < 2:
    st.info("Hier gab es nichts zu schneiden: kein Schnitt der gewählten Form ist verletzt.")
else:
    R = len(a.cuts.rounds) - 1
    owner = (params, opts)
    if st.session_state.get("fcn_owner") != owner:
        st.session_state["fcn_round"] = R
        st.session_state["fcn_owner"] = owner
    rd = st.slider("Schnittrunde", 0, R, key="fcn_round", help="Runde 0 ist das LP ohne Schnitte; jede weitere fügt die am stärksten verletzten Schnitte hinzu und löst neu. Die Marke im Diagramm rechts folgt dem Regler.") if R > 0 else 0
    rnd = a.cuts.rounds[rd]
    cut = rnd.added[0] if rnd.added else None
    d1, d2 = st.columns([3, 2])
    with d1:
        st.markdown(f"**Nach Runde {rd}:** der LP-Entwurf" + (f" (violett: die Menge des ersten Schnitts dieser Runde und die Kanten, die sie betreten)" if cut else ""))
        st.plotly_chart(build_design_map(design, rnd.solution, opt_open, cut), width="stretch", key=f"round_map_{rd}")
    with d2:
        st.markdown("**Schranke je Runde**")
        st.plotly_chart(build_rounds(a.cuts.rounds, opt, rd), width="stretch", key=f"rounds_chart_{rd}")
    if rnd.added:
        st.markdown(f"**Runde {rd}: {len(rnd.added)} neue Schnitte** - die ersten drei in Worten:")
        for c in rnd.added[:3]:
            st.markdown(f"- `{c.kind}`{f' (Teiler {c.delta})' if c.delta else ''}: " + ev.cut_words(design, c))
    else:
        st.caption("Runde 0: das LP ohne Schnitte.")
    st.caption(f"Die Schranke steigt von {_pct(a.cuts.rounds[0].bound / opt)} auf {_pct(a.cuts.rounds[-1].bound / opt)} des Optimums. Die Schleife endet, wenn keine der gefundenen Mengen mehr verletzt ist" + (" - hier ist sie damit fertig." if a.cuts.converged else " - Rundengrenze erreicht."))

st.markdown("---")

# --- Verteilung ------------------------------------------------------------------------------------------------------------------------

st.markdown("## 📊 Nicht nur dieses eine Netz")
if is_fixed:
    st.info("Festes Netz: es gibt nur diese eine Ziehung. Für die Verteilungen über viele Netze ein zufälliges Netz wählen.")
    dist = None
else:
    with st.spinner("Rechne die 40 festen Netze..."):
        dist = _distribution(params)
    kind = "Streckennetze" if net_key == "grid" else "Distributionsnetze"
    st.markdown(f"**{dist['n_seeds']} feste {kind}** mit denselben Einstellungen (Güter {K}, Fixkosten {fix}), getrennt vom Seed oben; {dist['n_infeasible']} davon sind nicht lieferbar und zählen nicht. Kopplung stark, Schnitte gekappt und gerundet.")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Schwach", _pct(dist["weak_mean"]), delta=f"schlechtestes Netz {_pct(dist['weak_min'])}", delta_color="off", help="Mittel über die lieferbaren Netze: Schranke / Optimum.")
    p2.metric("Stark", _pct(dist["strong_mean"]), delta=f"schließt {_pct(dist['closed_strong_mean'], 0)} der Lücke", delta_color="off", help="Mittel über die Netze.")
    p3.metric("Mit Schnitten", _pct(dist["cuts_mean"]), delta=f"schließt {_pct(dist['closed_cuts_mean'], 0)} der Lücke", delta_color="off", help="Mittel über die Netze: stark + gekappte und gerundete Schnitte.")
    p4.metric("Exakt", _pct(dist["exact_share"], 0), delta=f"{_f(dist['n_cuts_mean'], 0)} Schnitte, {_f(dist['rounds_mean'], 1)} Runden", delta_color="off", help="Anteil der Netze, in denen die Schranke mit Schnitten schon das Optimum trifft; im Mittel so viele Schnitte und Runden.")
    mine = {"weak": dat["ratio_weak"], "strong": dat["ratio_strong"], "cuts": dat["ratio_bound"]} if a.cuts is not None and code != "wrong" else None
    st.plotly_chart(build_dist(dist, mine), width="stretch", key="dist_chart")
    st.caption(f"Über {dist['n_feasible']} lieferbare Netze liegt die schwache Schranke im Mittel bei {_pct(dist['weak_mean'])} des Optimums, die starke bei {_pct(dist['strong_mean'])}, mit Schnitten bei {_pct(dist['cuts_mean'])} "
               f"(schlechtestes Netz {_pct(dist['cuts_min'])}). Raute = die Ziehung oben (nur mit gewählten Schnitten). Nach Schnitten bleibt eine Restlücke; sie schließt der Branch-and-Bound.")

st.markdown("---")

# --- Experimente -----------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Was die Schranke für den Suchbaum bedeutet")
st.caption("HiGHS löst diese Netze fast immer schon an der Wurzel (eigene Schnitte, Vorverarbeitung) und taugt nicht zum Vergleich der Formulierungen. Deshalb hier ein **eigener Branch-and-Bound** ohne diese Hilfen: an jedem Knoten das LP der gewählten Formulierung, verzweigt auf der gebrochensten Kante, abgeschnitten an der besten bekannten Lösung. Zehn feste Netze.")
if is_fixed:
    st.info("Für dieses Experiment ein zufälliges Netz wählen.")
else:
    if st.button("Suchbaum zählen (10 Netze, 3 Formulierungen)", key="tree_start"):
        st.session_state["tree_on"] = True
    if st.session_state.get("tree_on"):
        with st.spinner("Rechne (das dauert eine halbe Minute)..."):
            tt = ev.tree_table(params)
        st.plotly_chart(build_tree(tt), width="stretch", key="tree_chart")
        st.table({"Formulierung": ["schwach", "stark", "stark + Schnitte"], "Knoten (Median)": [_n(tt[k]["median"]) for k in ("weak", "strong", "cuts")],
                  "Knoten (Mittel)": [_n(tt[k]["mean"]) for k in ("weak", "strong", "cuts")], "bewiesen": [f"{tt[k]['proven']} von {tt['n']}" for k in ("weak", "strong", "cuts")]})
        st.caption(f"Die Schnitte kommen einmalig an der Wurzel (Cut-and-Branch); danach wird verzweigt. Aus im Median {_n(tt['weak']['median'])} Knoten (schwach) werden {_n(tt['cuts']['median'])} - der Baum schrumpft auf {_pct(tt['cuts']['median'] / tt['weak']['median'], 0)}. "
                   f"Die starke Kopplung allein bringt wenig ({_n(tt['strong']['median'])}). Alle Läufe starten mit derselben oberen Schranke aus dem Aufrunden; bewiesen heißt: der Baum wurde leer, bevor die Knotengrenze ({_n(C.NODE_LIMIT)}) griff.")

st.subheader("🔬 Wovon hängt die Lücke ab?")
st.caption("Schranken (Anteil am Optimum) bei wachsenden Fixkosten und wachsender Auslastung, 16 feste Netze je Wert, Kopplung stark, Schnitte gekappt und gerundet.")
if is_fixed:
    st.info("Für dieses Experiment ein zufälliges Netz wählen.")
else:
    if st.button("Fixkosten und Auslastung durchrechnen", key="sweep_start"):
        st.session_state["sweep_on"] = True
    if st.session_state.get("sweep_on"):
        with st.spinner("Rechne..."):
            fx = ev.sweep_table(params, "fix", C.FIXES)
            ld = ev.sweep_table(params, "load", C.LOADS) if net_key == "random" else None
        s1, s2 = st.columns(2)
        s1.markdown("**Fixkosten-Basis wächst**")
        s1.plotly_chart(build_sweep(fx, "Fixkosten-Basis"), width="stretch", key="sweep_fix")
        if ld is not None:
            s2.markdown("**Auslastung wächst** (in % der Werkskapazität)")
            s2.plotly_chart(build_sweep(ld, "Auslastung [%]"), width="stretch", key="sweep_load")
        else:
            s2.caption("Die Auslastungsreihe gibt es nur im Distributionsnetz.")
        st.table({"Fixkosten": [str(r["value"]) for r in fx], "schwach": [_pct(r["weak"]) for r in fx], "stark": [_pct(r["strong"]) for r in fx], "mit Schnitten": [_pct(r["cuts"]) for r in fx], "lieferbare Netze": [str(r["n"]) for r in fx]})
        st.caption("Je höher die Fixkosten im Verhältnis zu den Stückkosten, desto mehr zählt die Entscheidung - und desto schwächer die LP-Schranke. Mit Schnitten bleibt sie dagegen fast gleich hoch.")

st.subheader("🔬 Welche Schnittform leistet was?")
st.caption("Negativkontrolle und Aufschlüsselung: keine Schnitte, nur der Kapazitätsschnitt, gekappt, gekappt und gerundet - und die falsch gerundete Form. 16 feste Netze, Kopplung stark.")
if is_fixed:
    st.info("Für dieses Experiment ein zufälliges Netz wählen.")
else:
    if st.button("Schnittformen durchrechnen (16 Netze)", key="modes_start"):
        st.session_state["modes_on"] = True
    if st.session_state.get("modes_on"):
        with st.spinner("Rechne..."):
            mt = ev.mode_table(params)
        st.plotly_chart(build_modes(mt), width="stretch", key="modes_chart")
        labels_ = {"none": "keine Schnitte", "plain": "Kapazitätsschnitt", "cap": "gekappt", "round": "gekappt + gerundet", "wrong": "falsch gerundet"}
        st.table({"Schnittform": [labels_[k] for k in labels_], "Anteil am Optimum": [_pct(mt[k]["ratio"]) if mt[k]["ratio"] == mt[k]["ratio"] else "unlösbar" for k in labels_],
                  "Schnitte je Netz": [_f(mt[k]["cuts"], 1) for k in labels_], "ungültig (Netze)": [f"{mt[k]['invalid']} von {mt['n']}" for k in labels_]})
        st.caption("Der Kapazitätsschnitt ist schon im schwachen LP enthalten und bringt nichts. Das Kappen der Kapazitäten auf den Bedarf leistet fast alles; die Rundung fügt in diesen Netzen kaum etwas hinzu (sie ist in den Lehrnetzen unentbehrlich: Rundungs-Falle). "
                   "Die falsch gerundete Form macht die Schleife unlösbar oder treibt die Schranke über das Optimum - ein Schnitt muss für jeden ganzzahligen Entwurf gelten.")

st.subheader("🔬 Wo die Schnitte aufhören")
st.caption("Zwei Grenzen: die Trennung ist eine Heuristik (exaktes Aufzählen aller Knotenmengen findet mehr), und mit der Netzgröße schließen die Schnitte weniger der Lücke.")
if st.button("Trennung und Größe durchrechnen", key="limits_start"):
    st.session_state["limits_on"] = True
if st.session_state.get("limits_on"):
    with st.spinner("Rechne..."):
        sp = ev.separation_table()
        sz = ev.size_table()
    st.table({"Trennung": ["Kandidatenmengen + lokale Suche (die Demo)", "exakt (alle Knotenmengen aufzählen)"], "Anteil am Optimum": [_pct(sp["heuristic"]), _pct(sp["exact"])]})
    st.caption(f"Kleine Netze (2 Werke, 2 Verteilzentren, 3 Filialen, zwei Güter), {sp['n']} lieferbare Netze: das Aufzählen aller Knotenmengen findet in {sp['exact_better']} von ihnen mehr Schnitte und erreicht im Mittel {_pct(sp['exact'])} statt {_pct(sp['heuristic'])}. Es wächst mit 2^Knoten und ist für die Netze oben nicht machbar.")
    st.plotly_chart(build_sizes(sz), width="stretch", key="sizes_chart")
    st.table({"Werke/Verteilzentren/Filialen": [f"{r['size'][0]}/{r['size'][1]}/{r['size'][2]}" for r in sz], "Entwurfsgruppen": [_f(r["groups"], 0) for r in sz], "Anteil am Optimum": [_pct(r["ratio"]) for r in sz],
              "Lücke geschlossen": [_pct(r["closed"], 0) for r in sz], "Schnitte": [_f(r["cuts"], 0) for r in sz]})
    st.caption("Mit wachsender Größe bleibt nach den Schnitten mehr Lücke: die Kandidatenmengen decken einen kleineren Teil der Knotenmengen ab, und es fehlen Schnittfamilien (Flow Cover, Mengen mit mehreren Gütern). Den Rest muss die Suche erledigen.")

st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist - und wer setzt an |
|---|---|
| **Nur Cut-Set-Schnitte** | Flow-Cover-, MIR- und Mengen mit mehreren Gütern fehlen; sie schließen einen Teil der Restlücke, den diese Demo nicht misst. Solver wie HiGHS bringen sie mit. |
| **Trennung ist eine Heuristik** | Die exakte Trennung über alle Knotenmengen wächst exponentiell (Experiment); die Restlücke ist zum Teil ein Trennungsfehler. |
| **Cut-and-Branch** | Schnitte nur an der Wurzel; ein echtes Branch-and-Cut (`branch-cut-demo` am Rucksack) schneidet in jedem Knoten. |
| **Feste Nachfrage, ein Zeitpunkt** | Fixkosten gelten je Kante und Tag; wer Fahrpläne plant, braucht ein Zeit-Raum-Netz (`leercontainer-demo`). |
| **Alles auf einmal lösen** | Große Netze lösen das MIP nicht mehr direkt. **Ansatzpunkt:** **Benders-Zerlegung** (gebaut: benders-demo; Entwurf im Master, Fluss im Teilproblem) und **Slope Scaling** (gebaut: slope-scaling-demo; Heuristik) - die Folgestücke. |
"""
)
st.caption("Die Netzwerkfluss-Linie ist als Ganzes geplant: Edmonds-Karp, Dinic, Push-Relabel, Successive Shortest Paths, Cycle-Canceling, Cost Scaling, Mehrgüterfluss, Column Generation, Garg-Könemann, Fixkosten-Netzwerkdesign (dieses Stück), Benders-Zerlegung (gebaut) und Slope Scaling (gebaut).")

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Entwurf.** Kanten $E$, Entwurfsgruppen $g$ mit Fixkosten $f_g$, Güter $k$ mit Nachfrage $d_k$, Kapazitäten $u_e$, Stückkosten $c^k_e$:
$$\min\ \sum_g f_g y_g+\sum_{k,e}c^k_e x^k_e\quad\text{u.d.N.}\quad \text{Flusserhaltung je Gut},\ \ \sum_k x^k_e\le u_e\,y_{g(e)},\ \ x^k_e\le\min(u_e,d_k)\,y_{g(e)},\ \ y\in\{0,1\}^G.$$
Die LP-Relaxation lässt $y\in[0,1]$ zu. Die schwache Kopplung ($\sum_k x^k_e\le u_e y$) erlaubt $y=\text{Fluss}/u_e$; die starke ($x^k_e\le\min(u_e,d_k)y$) zwingt $y\ge x^k_e/\min(u_e,d_k)$.

**Schnitt.** Für $W\subseteq V\setminus\{s,t\}$ sei $R(W)=\max\{\sum_k\max(0,d_k(W)-a_k(W)),\ d(W)-c(W)\}$ mit Nachfrage $d_k(W)$, Angebot $a_k(W)$ und Werkskapazität $c(W)$ in $W$. Aus der Flusserhaltung folgt $\sum_{e\in\delta^-(W)}\sum_k x^k_e\ge R(W)$, also für ganzzahliges $y$
$$\sum_{e\in\delta^-(W)}\min(u_e,R)\,y_e\ge R,\qquad \sum_{e\in\delta^-(W)}\Big\lceil\tfrac{\min(u_e,R)}{\delta}\Big\rceil y_e\ \ge\ \Big\lceil\tfrac{R}{\delta}\Big\rceil\quad(\delta>0),$$
die zweite Form ist die Chvátal-Gomory-Rundung der ersten. Die Tests prüfen für kleine Netze durch Aufzählen aller Entwürfe, dass jede Form von jedem zulässigen Entwurf erfüllt wird.

**Suchbaum.** Branch-and-Bound mit LP-Schranke (beste zuerst), Verzweigung auf der Kante mit $y$ am nächsten an $0{,}5$; Schnitte einmalig an der Wurzel (Cut-and-Branch).

Implementiert in `fcn_formulation.py` (LP-Stufen, MIP, Aufrunden, Aufzählen), `fcn_cuts.py` (Schnitte, Trennung, Schleife), `fcn_bnb.py` (eigener Branch-and-Bound), `fcn_model.py` und `fcn_scenario.py` (Netze), `fcn_evaluation.py`, `fcn_visualization.py`; das Vergleichs-MIP löst HiGHS über `scipy`.
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [Netzwerkfluss: vom Max-Flow zum Netzdesign](https://sebastianhanisch.net/konzepte-netzwerkfluss.html)."
)
