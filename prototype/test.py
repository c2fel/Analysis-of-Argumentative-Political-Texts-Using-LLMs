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

import tiktoken

retry = ""
markdown_content = 'markdown_output/erlaeuterungen_6600_fr.md'
# Deinen Prompt hier einfügen (als String)
prompt = f"""{retry} The attached markdown file contains all the information that was given to Swiss citizens to vote on this topic. Score the complexity by easy, normal, or difficult. Consider that this score needs to apply for an average citizen. Only output the label of the score, no reasoning at all.

```markdown
{markdown_content}
```"""
# Encoder für Grok-Modelle (cl100k_base)
encoding = tiktoken.get_encoding("cl100k_base")

# Tokens zählen
tokens = len(encoding.encode(prompt))
print(f"Anzahl Tokens im Prompt: {tokens}")

# Check gegen Limit
limit = 131072
if tokens > limit:
    print("⚠️ Überschreitet das Limit! Kürze den Prompt.")
elif tokens > limit * 0.8:  # 80% Puffer für Response
    print("🔶 Nah am Limit – prüfe mit Response-Schätzung.")
else:
    print("✅ Sicher unter dem Limit.")

# TODO this code needs to be implemented in functions.py
load_dotenv(dotenv_path='agents/.env')
erlaeuterung_template = os.getenv("BK_API_ERLAEUTERUNGEN")
erlaeuterung_url = erlaeuterung_template.format(vote_id="6770")
print(erlaeuterung_url)