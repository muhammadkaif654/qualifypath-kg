"""Draw the end-to-end architecture of QualifyPath-KG (Visualization/architecture.png)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "architecture.png"
INK, MUTED = "#0f172a", "#64748b"

fig, ax = plt.subplots(figsize=(17, 9.2), dpi=170)
ax.set_xlim(0, 17)
ax.set_ylim(0, 9.2)
ax.axis("off")


def box(x, y, w, h, title, lines, fc, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.18", fc=fc, ec=ec, lw=1.8))
    ax.text(x + w / 2, y + h - 0.32, title, ha="center", va="top", fontsize=12.5, weight="bold", color=INK)
    ax.text(x + w / 2, y + h - 0.78, "\n".join(lines), ha="center", va="top", fontsize=9.6, color="#334155",
            linespacing=1.45)


def arrow(x1, y1, x2, y2, label="", color="#475569", rad=0.0, dy=0.18):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=17, lw=1.8, color=color,
                                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + dy, label, ha="center", fontsize=9, color=color, style="italic")


ax.text(0.2, 8.95, "QualifyPath-KG — system architecture", fontsize=18, weight="bold", color=INK, va="top")
ax.text(0.2, 8.45, "Iteration 1 builds and reasons over the graph; Iteration 2 adds multi-hop reasoning and the "
        "knowledge-grounded LLM application", fontsize=11, color=MUTED, va="top")

# Iteration 1 pipeline (top row)
box(0.2, 5.6, 2.6, 2.2, "Kaggle CSVs", ["matches, deliveries,", "venues, points table", "(IPL 2026, CC0)"],
    "#f8fafc", "#94a3b8")
box(3.3, 5.6, 2.8, 2.2, "Cleaning + RDF", ["build_kg.py", "9 documented fixes", "1,378 A-Box triples"],
    "#ecfdf5", "#059669")
box(6.6, 5.6, 3.2, 2.2, "Knowledge graph", ["Ontology (T-Box) + A-Box", "OWL 2 RL reasoning (owlrl)", "SPARQL rules R1–R7",
                                            "explicit · inferred · rule-derived"], "#eef2ff", "#4f46e5")
box(10.3, 5.6, 3.0, 2.2, "Symbolic layer", ["SPARQL Q01–Q11", "inference demos I1–I3", "GraphDB (OWL2-RL)"],
    "#f5f3ff", "#7c3aed")
box(13.8, 5.6, 3.0, 2.2, "Multi-hop reasoner", ["Option C (multihop.py)", "paths with intermediate", "entities + provenance",
                                                 "150/150 vs ground truth"], "#fffbeb", "#d97706")
arrow(2.8, 6.7, 3.3, 6.7)
arrow(6.1, 6.7, 6.6, 6.7)
arrow(9.8, 6.7, 10.3, 6.7)
arrow(13.3, 6.7, 13.8, 6.7)

# Iteration 2 QA pipeline (bottom row)
box(0.2, 1.2, 2.6, 2.5, "User question", ["Streamlit app", "e.g. Can LSG still", "qualify for the top 4?"],
    "#f8fafc", "#94a3b8")
box(3.3, 1.2, 2.8, 2.5, "Linking + intent", ["team / venue / match", "aliases from labels;", "keyword intents → CQ types"],
    "#ecfdf5", "#059669")
box(6.6, 1.2, 3.2, 2.5, "KG retrieval", ["SPARQL-generated context", "+ multi-hop paths →", "numbered facts [F1..Fn]",
                                         "tagged with provenance"], "#eef2ff", "#4f46e5")
box(10.3, 1.2, 3.0, 2.5, "LLM (Groq)", ["openai/gpt-oss-120b", "temperature 0", "answer only from facts,",
                                         "cite [F#] or refuse"], "#f5f3ff", "#7c3aed")
box(13.8, 1.2, 3.0, 2.5, "Grounded answer", ["answer + cited evidence", "reasoning-path graph", "explicit / inferred /",
                                              "generated separated"], "#fffbeb", "#d97706")
arrow(2.8, 2.45, 3.3, 2.45)
arrow(6.1, 2.45, 6.6, 2.45)
arrow(9.8, 2.45, 10.3, 2.45)
arrow(13.3, 2.45, 13.8, 2.45)
arrow(8.2, 5.6, 8.2, 3.7, "SPARQL", color="#4f46e5", dy=0)
arrow(15.3, 5.6, 9.3, 3.7, color="#d97706", rad=0.08)
ax.text(13.2, 4.95, "reasoning paths", fontsize=9, color="#d97706", style="italic")
ax.text(8.2, 0.75, "No facts retrieved → LLM not called → \"INSUFFICIENT EVIDENCE\"", ha="center", fontsize=10,
        color="#b45309", weight="bold")
ax.text(11.8, 0.75, "LLM-only baseline: same model and settings, no facts", ha="left", fontsize=9.5, color=MUTED)
fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print("Written", OUT.name)
