# QualifyPath-KG

A knowledge-grounded qualification and standings reasoner for cricket tournaments, built on the
**IPL 2026** league stage (snapshot after match 39, 27 April 2026). AI-3001 Knowledge Representation &
Reasoning, Fall 2026 — Iterations 1 and 2.

**Team:** Muhammad Kaif (24I-0071), Talha Habib (24I-0029), Haseebullah Gondal (24I-0086) · section AI-B
**Instructor:** Ms. Mehreen Javaid

```
User question → KG retrieval + multi-hop reasoning → retrieved facts → LLM (Groq) → grounded answer + evidence
```

## What is in the repository

| Folder | Contents |
| --- | --- |
| `Dataset/` | Original Kaggle archive and extracted CSVs (`raw/`), cleaned match table (`processed/`), cleaning notes |
| `Ontology/` | `qualifypath.ttl` — OWL/RDFS schema (T-Box): 19 classes, 46 properties, 5 reasoning constructs |
| `RDF_Knowledge_Graph/` | `ipl2026_abox.ttl` (1,378 triples), `build_kg.py` (CSV → RDF), URI design, `graphdb/` loader |
| `SPARQL_Queries/` | Queries Q01–Q11, SPARQL Update rules R1–R7 (`rules/`), inference demos I1–I3, `run_queries.py` |
| `qualifypath/` | Python package: graph loading with provenance (`kg.py`), multi-hop reasoner (`multihop.py`), retriever (`retriever.py`), LLM client (`llm.py`), QA pipeline (`qa.py`) |
| `prompts/` | System prompts for the KG-grounded and LLM-only conditions |
| `app/` | Streamlit application: Overview, Points Table, Match Center, Qualification Predictor, Scenario Explorer, Ask AI (grounded Q&A), Multi-hop Reasoner, Graph Explorer, Evidence & Sources, Evaluation, About |
| `scripts/` | Evaluation: multi-hop vs ground truth, LLM-only vs KG-grounded (10 CQs), explainability examples |
| `Results/` | Iteration 1 query outputs and inference examples; `iteration2/` evaluation results |
| `Visualization/` | Ontology, season and team diagrams; GraphDB screenshots |
| `Report/` | Iteration reports and the final PDF report |

## Prerequisites

- Python 3.10 or newer (developed on 3.14)
- A free Groq API key from https://console.groq.com (for the LLM application and evaluation only)
- Optional: GraphDB 10/11 Free and Protégé 5.6 for the graph demos

## Setup

```bash
pip install -r requirements.txt
```

Copy the sample configuration and add your own key (the real `.env` is git-ignored and must never be committed):

```bash
cp .env.example .env
```

`.env` holds `GROQ_API_KEY`, `GROQ_MODEL` (default `llama-3.3-70b-versatile`), `LLM_TEMPERATURE` (0) and `LLM_MAX_TOKENS`.

## Data preparation

The original data is included (`Dataset/ipl-2026-complete-dataset.zip`, Kaggle
[krishd123/ipl-2026-complete-dataset](https://www.kaggle.com/datasets/krishd123/ipl-2026-complete-dataset), CC0).
To rebuild the RDF instance data from the CSVs and re-check it against the official points table:

```bash
python RDF_Knowledge_Graph/build_kg.py
```

## Running

| Step | Command | Output |
| --- | --- | --- |
| SPARQL queries, rules and inference demos (Iteration 1) | `python SPARQL_Queries/run_queries.py` | `Results/Q*.csv`, `Results/inference_examples.csv` |
| Multi-hop reasoning evaluation (Option C) | `python scripts/evaluate_multihop.py` | `Results/iteration2/multihop_*` |
| Application | `streamlit run app/streamlit_app.py` | web app at http://localhost:8501 |
| LLM-only vs KG-grounded evaluation | `python scripts/run_cq_evaluation.py` | `Results/iteration2/cq_evaluation_raw.*` |
| Explainability examples | `python scripts/explainability_examples.py` | `Results/iteration2/explainability_examples.md` |
| Diagrams | `python Visualization/make_visualizations.py` | `Visualization/*.png` |
| GraphDB repository (GraphDB running) | `python RDF_Knowledge_Graph/graphdb/load_graphdb.py --reset` | repository `qualifypath-ipl2026` |

All commands run from the repository root. The graph (1,712 explicit triples) is loaded, expanded with
OWL 2 RL reasoning (owlrl) and the SPARQL rules at start-up, which takes about 3 seconds.

## How the application answers

1. **Entity linking**: team names and aliases, venues and match numbers are matched against graph labels.
2. **Intent detection**: keyword patterns map the question to competency-question types (standings,
   fixtures, qualification, rivals, what-if, results, venues, …).
3. **Retrieval**: the Iteration 1 SPARQL queries and the multi-hop reasoner return numbered facts, each
   tagged *explicit*, *inferred (OWL 2 RL)*, *rule-derived*, *reasoning path* or *scenario*.
4. **Generation**: the facts and the question go to the LLM with `prompts/grounded_system.txt`, which
   requires citations ([F#]) and an `INSUFFICIENT EVIDENCE` reply when the facts do not cover the question.
5. **Insufficient evidence**: if nothing in the graph matches the question, the LLM is not called at all.

The LLM-only baseline uses the same model, temperature and token limit with `prompts/llm_only_system.txt`.

## Results at a glance

- Iteration 1 standings computed by the SPARQL rules match the official IPL table after match 39 for all 10 teams.
- Multi-hop reasoner: 150/150 questions correct against independently computed ground truth; 3,356 path hops verified.
- LLM-only vs KG-grounded comparison and explainability examples: see `Results/iteration2/`.
