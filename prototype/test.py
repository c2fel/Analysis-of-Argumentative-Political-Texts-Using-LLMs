import os

import networkx as nx
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# Create a directed graph
G = nx.DiGraph()

# Nodes
G.add_node("Umweltverantwortungsinitiative", pos=(0, 4))
G.add_node("Fakten", pos=(-2, 3))
G.add_node("Pro-Argumente", pos=(2, 3))
G.add_node("Contra-Argumente", pos=(-2, 1))

# Fact nodes
G.add_node("Fortschritte im Umweltschutz", pos=(-4, 2))
G.add_node("Überschreitung planetarer Grenzen", pos=(-2, 2))
G.add_node("10-Jahres-Frist", pos=(0, 2))

# Pro nodes
G.add_node("Schutz der Lebensgrundlagen", pos=(2, 2))
G.add_node("Dringlichkeit", pos=(4, 2))
G.add_node("Wirtschaftliche Chancen", pos=(2, 1))
G.add_node("Ganzheitlicher Ansatz", pos=(4, 1))
G.add_node("Umweltgerechtigkeit", pos=(3, 0))

# Contra nodes
G.add_node("Einschneidende Vorschriften", pos=(-4, 0))
G.add_node("Wirtschaftliche Belastung", pos=(-2, 0))
G.add_node("Soziale Folgen", pos=(-3, -1))
G.add_node("Kurze Frist", pos=(-1, -1))
G.add_node("Internationaler Kontext", pos=(-2, -2))

# Edges
G.add_edge("Umweltverantwortungsinitiative", "Fakten")
G.add_edge("Umweltverantwortungsinitiative", "Pro-Argumente")
G.add_edge("Umweltverantwortungsinitiative", "Contra-Argumente")
G.add_edge("Fakten", "Fortschritte im Umweltschutz")
G.add_edge("Fakten", "Überschreitung planetarer Grenzen")
G.add_edge("Fakten", "10-Jahres-Frist")
G.add_edge("Pro-Argumente", "Schutz der Lebensgrundlagen")
G.add_edge("Pro-Argumente", "Dringlichkeit")
G.add_edge("Pro-Argumente", "Wirtschaftliche Chancen")
G.add_edge("Pro-Argumente", "Ganzheitlicher Ansatz")
G.add_edge("Pro-Argumente", "Umweltgerechtigkeit")
G.add_edge("Contra-Argumente", "Einschneidende Vorschriften")
G.add_edge("Contra-Argumente", "Wirtschaftliche Belastung")
G.add_edge("Contra-Argumente", "Soziale Folgen")
G.add_edge("Contra-Argumente", "Kurze Frist")
G.add_edge("Contra-Argumente", "Internationaler Kontext")

# Draw the graph
pos = nx.get_node_attributes(G, 'pos')
plt.figure(figsize=(12, 8))
nx.draw(G, pos, with_labels=True, node_size=3000, node_color='lightblue', font_size=10, font_weight='bold', arrowsize=20)
plt.title("Argumente zur Umweltverantwortungsinitiative")
plt.savefig("graph_6770.png")
plt.close()