"""Konstanten, Regler-Grenzen, Presets und feste Seed-Mengen der Demo "Fixkosten-Netzdesign: warum die Schranke schwach ist"."""

# --- Regler Distributionsnetz -----------------------------------------------------------------------------------------------------
P_MIN, P_MAX, DEFAULT_P = 2, 6, 3            # Werke
D_MIN, D_MAX, DEFAULT_D = 2, 6, 3            # Verteilzentren
S_MIN, S_MAX, DEFAULT_S = 3, 12, 8           # Filialen
DENSITY_MIN, DENSITY_MAX, DEFAULT_DENSITY = 20, 100, 60   # Anteil vorhandener Lanes in ganzen Prozent, Schritt 10
SPREAD_MIN, SPREAD_MAX, DEFAULT_SPREAD = 0, 100, 50       # Streuung der Lane-Breiten in ganzen Prozent, Schritt 25
LOAD_MIN, LOAD_MAX, DEFAULT_LOAD = 30, 90, 50             # Gesamtnachfrage in Prozent der Werkskapazität, Schritt 10
FIX_MIN, FIX_MAX, DEFAULT_FIX = 5, 150, 30                # Fixkosten-Basis je Lane (mal 1 bis 3; Verteilzentrum doppelt), Schritt 5
DEFAULT_SEED = 155
SEED_MAX = 2_000_000_000

# --- Regler Streckennetz ------------------------------------------------------------------------------------------------------------
GW_MIN, GW_MAX, DEFAULT_GW = 3, 6, 4                      # Breite des Gitters
GH_MIN, GH_MAX, DEFAULT_GH = 3, 5, 3                      # Höhe des Gitters
GDENSITY_MIN, GDENSITY_MAX, DEFAULT_GDENSITY = 40, 100, 60   # Anteil der Gitterkanten (über den Spannbaum hinaus), Schritt 10
GCAP_MIN, GCAP_MAX, DEFAULT_GCAP = 1, 4, 4                # größte Kapazität je Kante und Richtung
GDEM_MIN, GDEM_MAX, DEFAULT_GDEM = 1, 5, 2                # größte Menge je Gut
DEFAULT_GSEED = 6

K_MIN, K_MAX, DEFAULT_K = 1, 5, 3            # Zahl der Güter

NETS = {
    "random": "Distributionsnetz (wie im Vorgänger)",
    "grid": "Streckennetz (Gitter mit Start-Ziel-Aufträgen)",
    "bigm": "Big-M-Falle: eine Menge von 1, eine Kante mit Kapazität 10",
    "rounding": "Rundungs-Falle: 3 Einheiten über zwei Kanten der Kapazität 2",
    "bundle": "Bündelung: zwei Güter teilen eine Stammstrecke",
}
DEFAULT_NET = "random"
FIXED_NETS = ("bigm", "rounding", "bundle")

COUPLINGS = {"weak": "schwach: Σ x ≤ u · y", "strong": "stark: zusätzlich x ≤ min(u, Nachfrage) · y je Gut"}
DEFAULT_COUPLING = "strong"
CUT_MODES = {
    "none": "keine Schnitte",
    "plain": "nur Kapazitätsschnitt (Σ u·y ≥ Bedarf)",
    "cap": "Kapazitäten auf den Bedarf gekappt",
    "round": "gekappt und gerundet (Chvátal–Gomory)",
    "wrong": "Negativkontrolle: falsch gerundet (rechte Seite + 1)",
}
DEFAULT_CUT_MODE = "round"

# --- feste Seed-Mengen (dieselben wie in den Vorgänger-Demos; unabhängig vom Nutzer-Seed) ------------------------------------------
DIST_SEEDS = tuple(range(100000, 100100))
QUALITY_SEEDS = DIST_SEEDS[:40]                     # Verteilung der Schranken
TREE_SEEDS = DIST_SEEDS[:10]                        # Suchbaum (eigener Branch-and-Bound, je Netz einige Sekunden)
SWEEP_SEEDS = DIST_SEEDS[:16]                       # Fixkosten- und Auslastungs-Reihe, Schnittformen
SEPARATION_SEEDS = DIST_SEEDS[:30]                  # Trennung: Heuristik gegen Aufzählen (kleine Netze)
FIXES = (5, 10, 20, 40, 80, 150)
LOADS = (30, 50, 70, 90)
SIZES = ((2, 2, 4), (3, 3, 8), (4, 4, 12), (5, 5, 16))     # Werke, Verteilzentren, Filialen
NODE_LIMIT = 2500

COLORS = {"open": "#1f77b4", "frac": "#ff7f0e", "closed": "rgba(150,150,150,0.45)", "opt": "#d62728", "cut": "#9467bd", "node": "#111111"}

# --- Presets -----------------------------------------------------------------------------------------------------------------
_BASE = dict(net="random", k=DEFAULT_K, p=DEFAULT_P, d=DEFAULT_D, s=DEFAULT_S, density=DEFAULT_DENSITY, spread=DEFAULT_SPREAD, load=DEFAULT_LOAD, fix=DEFAULT_FIX, seed=DEFAULT_SEED,
             gw=DEFAULT_GW, gh=DEFAULT_GH, gdensity=DEFAULT_GDENSITY, gcap=DEFAULT_GCAP, gdem=DEFAULT_GDEM, gseed=DEFAULT_GSEED,
             coupling=DEFAULT_COUPLING, cuts=DEFAULT_CUT_MODE)
PRESETS = {
    "🚚 Zufallsnetz": {**_BASE},
    "🗺️ Streckennetz": {**_BASE, "net": "grid", "k": 3, "fix": 10},
    "💸 Big-M-Falle": {**_BASE, "net": "bigm", "k": 1, "coupling": "weak", "cuts": "none"},
    "🔁 Rundungs-Falle": {**_BASE, "net": "rounding", "k": 1},
    "📦 Bündelung": {**_BASE, "net": "bundle", "k": 2, "coupling": "weak", "cuts": "none"},
    "🏗️ Hohe Fixkosten": {**_BASE, "fix": 120},
    "🧊 Schwache Formulierung": {**_BASE, "coupling": "weak", "cuts": "none"},
    "🚫 Falsche Schnitte": {**_BASE, "cuts": "wrong"},
}
PRESET_HELP = {
    "🚚 Zufallsnetz": "Das Netz der Vorgänger (Seed 155, drei Güter, Fixkosten 30): Optimum 1 784 mit 15 von 27 Kanten offen. Die schwache Schranke liegt bei 69,8 % davon (16 Kanten nur anteilig offen), die starke bei 71,7 %, mit gekappten und gerundeten Schnitten bei 93,4 % - sie schließen 78 % der Lücke (26 Schnitte, 3 Runden).",
    "🗺️ Streckennetz": "Gitter 4 × 3 mit drei Gütern (Seed 6, Fixkosten 10): hier trägt die starke Kopplung - schwach 82,7 %, stark 91,7 %, mit fünf Schnitten in einer Runde 98,0 % des Optimums 245. Auf Gittern sind die Mengen klein gegen die Kapazität; die Lücke sitzt bei den Einzelkanten.",
    "💸 Big-M-Falle": "Eine Einheit, zwei Wege: die breite Kante (Kapazität 10, Fixkosten 30) sieht im schwachen LP fast kostenlos aus - y = 0,1 genügt, Gesamtkosten 4. Ganzzahlig ist die schmale Kante billiger: 15. Die schwache Schranke liegt bei 26,7 % des Optimums; die starke Kopplung x ≤ min(u, Nachfrage)·y setzt y = 1 und trifft 15 exakt.",
    "🔁 Rundungs-Falle": "Drei Einheiten über zwei gleiche Kanten (Kapazität 2, Fixkosten 10): das LP öffnet beide zu 0,75 (Kosten 18), ganzzahlig braucht es beide (23). Die starke Kopplung hilft nicht (min(2, 3) = 2); erst der gerundete Schnitt y₁ + y₂ ≥ 2 schließt die Lücke ganz.",
    "📦 Bündelung": "Zwei Güter, entweder direkt (je Strecke 8 Fixkosten) oder gebündelt über einen Umschlagpunkt mit gemeinsamer Stammstrecke (2 + 2 + 5): Optimum 11 mit drei offenen Kanten. Das schwache LP sieht 6,5 (59,1 %), die starke Kopplung 11.",
    "🏗️ Hohe Fixkosten": "Fixkosten 120 statt 30 im Zufallsnetz: die schwache Schranke fällt auf 56,2 % des Optimums 3 996, die starke liegt bei 58,3 %, mit Schnitten bei 96,7 % - je wichtiger die Entscheidung, desto schwächer das LP und desto mehr bringen die Schnitte (sie schließen 93 % der Lücke).",
    "🧊 Schwache Formulierung": "Nur die schwache Kopplung, keine Schnitte: die Schranke liegt bei 69,8 % des Optimums, 16 der 27 Kanten sind nur anteilig offen. So sieht die Relaxation aus, wenn man sie nicht verbessert.",
    "🚫 Falsche Schnitte": "Negativkontrolle: die Rundung fordert jeweils eine Einheit zu viel (rechte Seite + 1). Die Schnitte schneiden zulässige Entwürfe ab, schon nach der ersten Runde wird das LP unlösbar - eine Schnittungleichung muss für jeden ganzzahligen Entwurf gelten.",
}
