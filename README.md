# Fixkosten-Netzdesign – warum die Schranke schwach ist – Streamlit-Demo

*(noch nicht deployed)*

Zehntes Stück der **Netzwerkfluss-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning", erstes im Netzwerkdesign-Ast:
anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo **eine Frage** – **warum ist die LP-Schranke beim Netzwerkdesign mit Fixkosten so schwach, und was ändern stärkere Formulierung und Schnitte?** – an einem wachsenden Beispiel.
Das Modell ist der Mehrgüterfluss der Vorgänger, aber jede Lane und jedes Verteilzentrum muss erst **geöffnet** werden (Fixkosten, Ja/Nein): gemischt-ganzzahlig, NP-schwer. Die übliche Relaxation lässt eine Kante zu einem Bruchteil $y\in[0,1]$ offen sein und zahlt nur diesen Bruchteil der Fixkosten – eine Lane, die im Fluss zu 10 % ausgelastet ist, kostet im LP 10 % ihrer Fixkosten.
Die Demo misst, wie schwach die Schranke ist, und was zwei Verbesserungen bringen: die **starke Kopplung** $x^k_e\le\min(u_e,d_k)\,y$ je Gut und **Schnittungleichungen** aus den Min-Cuts des Netzes (gekappt und mit Chvátal-Gomory gerundet) – und, am Ende, was das für die Größe des Suchbaums bedeutet.
Vehikel: das Distributionsnetz der Vorgänger (Standard, Seed 155), ein **Streckennetz** (Gitter mit Start-Ziel-Aufträgen) und drei feste Lehrnetze (Big-M-Falle, Rundungs-Falle, Bündelung), an denen sich je ein Effekt von Hand nachrechnen lässt.

**Einordnung in die Reihe (die Kanten des Graphen):** Das Mehrgütermodell (Flusserhaltung je Gut, gemeinsame Kapazität) stammt aus [multicommodity-demo](https://github.com/sebastian-hanisch/multicommodity-demo); neu ist die Entwurfsentscheidung. Verwandt: [linehaul-demo](https://github.com/sebastian-hanisch/linehaul-demo) hat **dasselbe Modell** (Fixed-Charge-Multicommodity-Network-Design), vergleicht dort aber Heuristiken gegen das SCIP-Optimum – hier steht die *Schranke* im Mittelpunkt und was Schnitte an ihr ändern. Schnittebenen am Rucksack zeigen [cutting-planes-demo](https://github.com/sebastian-hanisch/cutting-planes-demo) und [branch-cut-demo](https://github.com/sebastian-hanisch/branch-cut-demo); hier sind es Schnitte aus der **Netzstruktur** (Knotenmengen, Min-Cuts). Das Folgestück **Benders-Zerlegung** ist gebaut ([benders-demo](https://github.com/sebastian-hanisch/benders-demo): Entwurf im Master, Fluss im Teilproblem), danach kommt **Slope Scaling** (Heuristik für große Netze). Bisher gebaut: die ersten elf Stücke.
```
edmonds-karp-demo (Wurzel: Restgraph, Rückkanten, Max-Flow = Min-Cut)                  [gebaut]
  ├─ dinic-demo (viele kürzeste Wege je Phase: Niveaugraph, blockierender Fluss)        [gebaut]
  ├─ push-relabel-demo (kein Weg: Überschüsse schieben, Höhen anheben)                 [gebaut]
  └─ ssp-demo (Kosten: der billigste Weg im Restgraphen, Potenziale)                    [gebaut]
       ├─ cycle-canceling-demo (negative Kreise löschen) → Netzwerksimplex               [gebaut]
       │    (network-flow-demo)                                                          [gebaut als Fall-Demo]
       ├─ cost-scaling-demo (Push-Relabel + ε-Skalierung, das nutzt OR-Tools)           [gebaut]
       └─ multicommodity-demo (mehrere Güter teilen Kapazität: Kanten-LP, Preise)       [gebaut]
            ├─ mcf-column-generation-demo (Pfade als Spalten, Pricing = Dijkstra)       [gebaut]
            ├─ garg-koenemann-demo (Näherung mit Preisen, ohne LP-Löser)                [gebaut]
            └─ fixkosten-netzdesign-demo (Fixkosten: Schranke und Schnitte)             [dieses Stück]
                 ├─ benders-demo (Entwurf im Master, Fluss im Teilproblem)              [gebaut]
                 └─ Slope Scaling (Heuristik für große Netze)                           [geplant]
```

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` belegt: Beispielnetze über ihre Seeds, Verteilungen über feste Netze (Seeds ab 100000, dieselben wie in den Vorgänger-Demos): 40 Netze für die Schranken, 16 für die Reihen und Schnittformen, 10 für den Suchbaum, 30 für die Trennung. Standard: 3 Güter, 3 Werke, 3 Verteilzentren, 8 Filialen, Netzdichte 60 %, Streuung 50 %, Auslastung 50 %, Fixkosten-Basis 30, Kopplung stark, Schnitte gekappt und gerundet.
Das **Optimum** rechnet HiGHS (MIP), die Schranken sind LPs (HiGHS), die Schnitte und der Branch-and-Bound sind eigener Code. Zahlen stehen gerundet („etwa“), die Tests prüfen Bänder (LP-Lösungen mit Gleichständen können auf anderen Plattformen andere Ecken wählen). Die aus den Vorgängern kopierten Netzgeneratoren sind bewacht (`tests/test_copies.py`).
Von den 40 Distributionsnetzen sind 34 lieferbar (auch mit allen Kanten offen decken sie die Nachfrage nicht in allen), nur diese zählen.

**Die Schranke.** Auf dem Standardnetz liegt die **schwache Schranke im Mittel bei 70,7 % des Optimums** (schlechtestes Netz 61,8 %), die **starke bei 73,3 %** – sie schließt nur **9 %** der Lücke –, und **mit Schnitten bei 96,5 %** (schlechtestes Netz 92,6 %): die Schnitte schließen im Mittel **88 %** der Lücke (Median 89 %), mit im Mittel etwa 28 Schnitten in 3 Runden. Nie ganz exakt: der Rest bleibt dem Branch-and-Bound. Aufrunden (jede angebrochene Kante öffnen, Fluss neu wählen) liefert eine Lösung 5 % über dem Optimum.
Im Beispielnetz (Seed 155): Optimum 1 784 mit 15 von 27 Kanten offen; schwach 69,8 % (16 Kanten nur anteilig offen), stark 71,7 %, mit Schnitten 93,4 % (78 % der Lücke, 26 Schnitte, 3 Runden). Mit Fixkosten 120: schwach 56,2 %, stark 58,3 %, Schnitte 96,7 %.

**Der Suchbaum.** Ein eigener Branch-and-Bound (beste Schranke zuerst, gleiche Startlösung aus dem Aufrunden, 9 lieferbare Netze) braucht im Median **705 Knoten mit der schwachen, 647 mit der starken Formulierung und 23 mit Schnitten** – der Baum schrumpft auf etwa 3 %. **HiGHS** dagegen löst jedes dieser Netze an der Wurzel (höchstens ein Knoten: eigene Schnitte, Vorverarbeitung) und taugt nicht, um Formulierungen zu vergleichen – deshalb der eigene.

**Wovon die Lücke abhängt.** Fixkosten-Basis 5 / 10 / 20 / 40 / 80 / 150: die schwache Schranke fällt von 90 auf 54 %, mit Schnitten bleibt sie bei 97 bis 98 %. Auslastung 30 / 50 / 70 / 90 %: schwach 50 / 70 / 80 / 85 %, stark 62 / 73 / 81 / 85 %, mit Schnitten 97 bis 98 % – je mehr Reserve die Lanes haben, desto schwächer die Kopplung (bei nur 4 lieferbaren Netzen bei 90 %).

**Welche Schnittform leistet was.** Ohne Schnitte und mit dem bloßen Kapazitätsschnitt Σ u·y ≥ Bedarf: 72,6 % – dieser Schnitt ist schon im schwachen LP enthalten und wird nie verletzt. **Gekappt** (Kapazitäten auf den Bedarf begrenzt): 96,8 %. Gekappt und **gerundet**: 97,0 %. Falsch gerundet (rechte Seite + 1): in allen 15 Netzen unlösbar.
Auf dem **Streckennetz** (Gitter 4 × 3, drei Güter, Fixkosten 10, 30 von 40 Netzen lieferbar) ist es umgekehrt: schwach 73,5 %, **stark 95,6 %** (schließt 82 % der Lücke), mit Schnitten 96,0 % – im Mittel weniger als ein Schnitt. Preset-Netz (Seed 6): Optimum 245, schwach 82,7 %, stark 91,7 %, mit fünf Schnitten in einer Runde 98,0 %.
Lehrnetze: **Big-M-Falle** schwach 26,7 % (Kosten 4 gegen 15), stark exakt; **Rundungs-Falle** schwach = stark = 78,3 % (18 gegen 23), erst der gerundete Schnitt y₁ + y₂ ≥ 2 schließt die Lücke; **Bündelung** schwach 59,1 % (6,5 gegen 11), stark exakt.

**Grenzen der Schnitte.** Die Trennung ist eine Heuristik (Kandidatenmengen aus Min-Cuts plus lokale Suche): auf kleinen Netzen erreicht sie 95,1 % des Optimums, das Aufzählen aller Knotenmengen 96,8 % (in 9 von 13 Netzen mehr). Und mit der Netzgröße schließen die Schnitte weniger: Netze mit 9 / 23 / 42 / 70 Entwurfsgruppen (2/2/4 bis 5/5/16 Werke/Verteilzentren/Filialen) – Lücke geschlossen 99,8 / 89,8 / 83,2 / 77,7 %, Anteil am Optimum 100 / 97,0 / 94,1 / 91,8 %.

## Was nicht funktioniert hat / Vorab-Hypothesen

Vor dem Bau standen sieben Vermutungen im Plan. Gemessen:

- **„Die starke Kopplung schließt den Großteil der Lücke“ – auf Distributionsnetzen widerlegt.** Sie schließt nur 9 % (70,7 → 73,3 %). Sie trägt dort, wo die Mengen klein gegen die Kapazität sind: auf dem Streckennetz schließt sie 82 %, in den Lehrnetzen (Big-M, Bündelung) alles. Im Distributionsnetz bündeln sich viele Güter auf jeder Lane, und die Kapazität ist die eigentliche Grenze – die Lücke sitzt dort bei den Knotenmengen, nicht bei den Einzelkanten.
- **„Ohne Rundung bringen die Schnitte nichts“ – widerlegt, aber anders als gedacht.** Der bloße Kapazitätsschnitt bringt tatsächlich nichts (schon im schwachen LP enthalten); das **Kappen** der Kapazitäten auf den Bedarf leistet fast alles (96,8 %), die **Rundung** fügt in diesen Netzen nur 0,2 Prozentpunkte hinzu. Sie ist unentbehrlich in der Rundungs-Falle, aber im Zufallsnetz kaum sichtbar.
- **„HiGHS braucht mit der starken Formulierung weniger Knoten“ – nicht messbar.** HiGHS löst alle diese Netze in einem Knoten; die Formulierung ändert dort nichts. Erst der eigene Branch-and-Bound ohne Vorverarbeitung zeigt es: die starke Kopplung spart im Median nur 8 % der Knoten (705 → 647), die Schnitte 97 %.
- **„Die Lücke wächst mit Fixkosten und Reserve“ – nur ohne Schnitte.** Die schwache Schranke fällt mit den Fixkosten von 90 auf 54 % und steigt mit der Auslastung von 50 auf 85 %; mit Schnitten bleibt sie bei 97 bis 98 % *unabhängig* von beiden. Je schlechter die Relaxation, desto mehr holen die Schnitte heraus (bei Fixkosten 150: 94 % der Lücke).
- **„Schnitte schließen die Lücke“ – nur zum Teil, und weniger bei wachsender Größe.** Auf dem Standardnetz bleiben 3,5 % (nie exakt), bei 70 Entwurfsgruppen 8 %. Ein Teil davon ist die heuristische Trennung (das Aufzählen findet mehr), der Rest fehlende Schnittfamilien (Flow Cover, Mengen mit mehreren Gütern, die hier nicht gebaut sind).
- **Bestätigt:** die schwache Schranke ist schwach (Lücke 29 %, im schlechtesten Netz 38 %); Aufrunden ist eine brauchbare, aber grobe obere Schranke (5 % im Mittel, 12 % im Streckennetz-Beispiel, 14 % bei hohen Fixkosten).
- **Negativkontrolle:** falsch gerundete Schnitte (rechte Seite + 1) machen das LP unlösbar; ein Schnitt muss für **jeden** ganzzahligen Entwurf gelten. Die Tests prüfen das durch Aufzählen aller 2^G Entwürfe kleiner Netze für jede Form jeder Knotenmenge.
- **Abweichung vom Plan:** Flow-Cover-Ungleichungen sind nicht gebaut; statt ihrer die gekappte und gerundete Cut-Set-Form. Die Restlücke ist im README benannt, nicht wegdiskutiert.

## Was die Demo zeigt

- **Die Schranke Stufe für Stufe:** schwach, stark, mit Schnitten – als Anteil am Optimum, dazu die Netzkarte mit dem LP-Entwurf (Blau = ganz offen, orange gestrichelt = anteilig, Beschriftung y) und dem ganzzahligen Optimum (rote Unterlage).
- **Schnittrunde für Schnittrunde:** ein Regler durch die Runden der Schleife; je Runde der Entwurf, die gewählte Knotenmenge und die betretenden Kanten (violett), die Schranke je Runde und die ersten Schnitte in Worten.
- **Nicht nur dieses Netz:** Verteilung der drei Schranken über 40 feste Netze mit der „Ihre Ziehung“-Marke.
- **Experimente (auf Abruf):** Suchbaum je Formulierung (eigener Branch-and-Bound), Fixkosten- und Auslastungsreihe, Schnittformen mit Negativkontrolle, Grenzen (Trennung, Größe).
- **Wo die Annahmen enden:** nur Cut-Set-Schnitte, Trennung ist Heuristik, Cut-and-Branch, feste Nachfrage, große Netze (Benders, Slope Scaling).

## Modell und Verfahren

Entwurf $y_g\in\{0,1\}$ je Lane (im Streckennetz je Strecke, beide Richtungen zusammen) und je Verteilzentrum (Durchsatzkante, doppelte Fixkosten), Fluss $x^k_e\ge0$ je Gut. Minimiere Fixkosten plus Stückkosten; Flusserhaltung je Gut, volle Nachfrage.
- **schwach:** $\sum_k x^k_e\le u_e y_g$; **stark:** zusätzlich $x^k_e\le\min(u_e,d_k)\,y_g$.
- **Schnitt:** für eine Knotenmenge $W$ sei $R(W)$ der Bedarf (Nachfrage minus Angebot in $W$, je Gut oder gesamt gegen die Werkskapazität, das größere). Dann muss über die Kanten, die $W$ betreten, mindestens $R$ hinein: $\sum \min(u_e,R)\,y_e\ge R$ (gekappt) und mit Teiler $\delta$ $\sum\lceil\min(u_e,R)/\delta\rceil y_e\ge\lceil R/\delta\rceil$ (Chvátal-Gomory).
- **Trennung:** Kandidatenmengen aus Einzelknoten, den Senkenseiten der Min-Cuts zu jedem Nachfrageknoten (Kapazität $u_e y_e$, alle Güter gemeinsam und je Gut), deren Vereinigungen und Komplementen; die stärksten werden per lokaler Suche (Knoten hinzu/heraus) verbessert. Bewertet wird die Verletzung relativ zur rechten Seite.
- **Schleife:** LP lösen, verletzte Schnitte (bis zu zehn je Runde) hinzufügen, neu lösen – bis keiner verletzt ist (höchstens 30 Runden).
- **Branch-and-Bound:** LP-Schranke je Knoten, beste zuerst, Verzweigung auf der Kante mit $y$ am nächsten an 0,5, Schnitte einmalig an der Wurzel (Cut-and-Branch), Startlösung aus dem Aufrunden.

## Dateien

```
app.py                  Oberfläche (Streamlit)
fcn_model.py            Entwurfsmodell: Design, Netze (Distribution, Gitter, Lehrnetze); Mehrgütermodell aus den Vorgängern
fcn_scenario.py         Distributionsnetz und Zufallsgenerator (SplitMix64), aus den Vorgängern
fcn_formulation.py      LP-Stufen, MIP (HiGHS), Aufrunden, Aufzählen aller Entwürfe
fcn_cuts.py             Schnitte, Trennung, Schnittschleife
fcn_bnb.py              eigener Branch-and-Bound
fcn_evaluation.py       Auswertung, Verteilungen, Experiment-Tabellen
fcn_visualization.py    Plotly-Abbildungen
fcn_presets.py          Permalink, Presets, Zufalls-Seed
fcn_constants.py        Konstanten, Regler-Grenzen, feste Seed-Mengen, Preset-Texte
tests/                  Formulierung, Schnitte, Auswertung, Presets, Behauptungen, App, Regler-Zustand
```

## Lokal starten

```bash
python -m venv venv
venv/Scripts/pip install -r requirements.txt
venv/Scripts/streamlit run app.py
```

## Tests ausführen

```bash
venv/Scripts/pip install -r requirements-dev.txt
venv/Scripts/python -m pytest tests/ -v
```

Die Tests laufen einige Minuten (App-Tests durchlaufen jedes Preset und jede Kombination von Kopplung und Schnittform; die Behauptungen rechnen die festen Netze).
