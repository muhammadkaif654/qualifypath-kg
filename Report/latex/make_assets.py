"""
Prepare the LaTeX report assets from the real project outputs (run from anywhere):

    python Report/latex/make_assets.py

* copies figures from Visualization/ into figures/
* writes generated/*.tex: SPARQL queries and their outputs, multi-hop evaluation, the 10-CQ comparison,
  full LLM answers, explainability examples, graph statistics, git information and commit lists

Re-run it whenever results change (and after the final push, so the commit hash and commit links are
current), then re-upload figures/ and generated/ to Overleaf.
"""
import csv
import json
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FIG, GEN = HERE / "figures", HERE / "generated"
FIG.mkdir(exist_ok=True)
(GEN / "queries").mkdir(parents=True, exist_ok=True)
REPO_URL = "https://github.com/muhammadkaif654/qualifypath-kg"

UNI = {"→": r"$\rightarrow$", "⟶": r"$\rightarrow$", "➜": r"$\rightarrow$", "←": r"$\leftarrow$",
       "–": "--", "—": "---", "‑": "-", "−": "-", "’": "'", "‘": "`", "“": "``", "”": "''", "≥": r"$\geq$",
       "≤": r"$\leq$", "×": r"$\times$", "∘": r"$\circ$", "⊑": r"$\sqsubseteq$", "…": r"\ldots{}", "·": r"$\cdot$",
       "✔": "yes", "✅": "", "❌": "", "\u00a0": " ", "\u202f": " ", "\u200b": "", "é": r"\'e"}


def tex(s) -> str:
    s = str(s)
    s = s.replace("\\", r"\textbackslash{}")
    for a, b in [("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
                 ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"), ("<", r"\textless{}"), (">", r"\textgreater{}")]:
        s = s.replace(a, b)
    s = s.replace(r"\textbackslash\{\}", r"\textbackslash{}")
    for a, b in UNI.items():
        s = s.replace(a, b)
    return s.encode("ascii", "ignore").decode()


def md_to_tex(s: str) -> str:
    """Light markdown (bold, bullets, line breaks) from LLM answers -> LaTeX text."""
    out = []
    for line in str(s).splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        bullet = re.match(r"^\s*([-*\u2022]|\d+\.)\s+", line)
        body = line[bullet.end():] if bullet else line
        body = tex(body)
        body = re.sub(r"\\\*\\\*|\*\*", "", body)
        body = re.sub(r"\[(F\d+)\]", r"\\textsf{[\1]}", body)
        out.append((r"\quad$\bullet$ " if bullet else "") + body)
    return r" \newline ".join(out)


def write(name, text):
    (GEN / name).write_text(text, encoding="utf-8")


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def table(rows, cols, spec=None, max_rows=12, size=r"\footnotesize"):
    spec = spec or "l" * len(cols)
    lines = [r"{" + size, r"\begin{tabular}{" + spec + "}", r"\toprule",
             " & ".join(rf"\textbf{{{tex(c)}}}" for c in cols) + r" \\", r"\midrule"]
    for r in rows[:max_rows]:
        lines.append(" & ".join(tex(r.get(c, "")) for c in cols) + r" \\")
    if len(rows) > max_rows:
        lines.append(rf"\multicolumn{{{len(cols)}}}{{l}}{{\textit{{\ldots{{}} {len(rows) - max_rows} more rows}}}} \\")
    lines += [r"\bottomrule", r"\end{tabular}}"]
    return "\n".join(lines)


# ------------------------------------------------------------------ figures
from PIL import Image  # noqa: E402

for f in (ROOT / "Visualization").glob("*.png"):
    # downscale to 1600 px wide: sharp at A4 width, and keeps Overleaf's free compile time short
    im = Image.open(f)
    if im.width > 1600:
        im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
    im.convert("RGB").save(FIG / (f.stem + ".jpg"), quality=88, optimize=True)

# ------------------------------------------------------------------ graph statistics
import sys  # noqa: E402
sys.path.insert(0, str(ROOT))
from qualifypath.kg import load_kg  # noqa: E402
from rdflib import OWL, RDF  # noqa: E402

kg = load_kg()
abox = len([1 for _ in open(ROOT / "RDF_Knowledge_Graph" / "ipl2026_abox.ttl", encoding="utf-8")])  # unused, info
from rdflib import Graph  # noqa: E402
a = Graph().parse(ROOT / "RDF_Knowledge_Graph" / "ipl2026_abox.ttl")
t = Graph().parse(ROOT / "Ontology" / "qualifypath.ttl")
stats = {
    "statAbox": f"{len(a):,}", "statTbox": f"{len(t):,}", "statExplicit": f"{len(kg.explicit):,}",
    "statInferred": f"{len(kg.owl) - len(kg.explicit):,}", "statRule": f"{len(kg.full) - len(kg.owl):,}",
    "statFull": f"{len(kg.full):,}",
    "statClasses": str(len(set(t.subjects(RDF.type, OWL.Class)))),
    "statObjProps": str(len(set(t.subjects(RDF.type, OWL.ObjectProperty)))),
    "statDataProps": str(len(set(t.subjects(RDF.type, OWL.DatatypeProperty)))),
}
write("stats.tex", "\n".join(rf"\newcommand{{\{k}}}{{{v.replace(',', '{,}')}}}" for k, v in stats.items()) + "\n")

# ------------------------------------------------------------------ git info and commits
def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


head = git("rev-parse", "HEAD")
write("gitinfo.tex", "\n".join([
    rf"\newcommand{{\repoURL}}{{{REPO_URL}}}", rf"\newcommand{{\repoLink}}{{\url{{{REPO_URL}}}}}",
    rf"\newcommand{{\headCommit}}{{{head or 'not-committed'}}}",
    rf"\newcommand{{\headCommitShort}}{{{head[:7] if head else 'n/a'}}}",
    rf"\newcommand{{\headCommitDate}}{{{tex(git('log', '-1', '--format=%cd', '--date=format:%d %B %Y %H:%M'))}}}"]) + "\n")
log = git("log", "--reverse", "--format=%H\t%an\t%ad\t%s", "--date=format:%d %b %H:%M")
rows = []
for line in log.splitlines():
    h, an, ad, s = line.split("\t")
    rows.append(rf"\href{{{REPO_URL}/commit/{h}}}{{\texttt{{{h[:7]}}}}} & {tex(an)} & {tex(ad)} & {tex(s)} \\")
write("commits.tex", "\n".join(rows) + "\n")

# ------------------------------------------------------------------ SPARQL queries and outputs
FEATURES = {
    "Q01": ("CQ15", "basic graph pattern, property path"), "Q02": ("CQ1", "aggregation, inference-dependent"),
    "Q03": ("CQ3", "aggregation, OPTIONAL, VALUES"), "Q04": ("CQ2", "property path, rule results"),
    "Q05": ("CQ4", "multi-hop, FILTER, property path"), "Q06": ("CQ5--CQ7", "rule-inferred classes, FILTER"),
    "Q07": ("CQ11", "multi-hop, inverse property path"), "Q08": ("CQ13", "inference-dependent (property chain)"),
    "Q09": ("CQ12", "UNION, OPTIONAL, FILTER"), "Q10": ("CQ14", "aggregation with HAVING"),
    "Q11": ("CQ8--CQ9", "multi-hop, rule-inferred class"),
}
parts = []
for q in sorted((ROOT / "SPARQL_Queries").glob("Q*.rq")):
    code = q.read_text(encoding="utf-8")
    code = "".join(ch if ord(ch) < 128 else "-" for ch in code)
    (GEN / "queries" / q.name).write_text(code, encoding="utf-8")
    res = read_csv(ROOT / "Results" / f"{q.stem}.csv")
    qid = q.stem[:3]
    cq, feat = FEATURES[qid]
    cols = list(res[0].keys()) if res else []
    parts += [rf"\subsubsection*{{{qid} --- {tex(q.stem[4:].replace('_', ' '))} ({cq}; {feat})}}",
              rf"\lstinputlisting[language=SPARQL]{{generated/queries/{q.name}}}",
              r"\noindent\textit{Output (" + str(len(res)) + r" rows):}\par\smallskip",
              r"\resizebox{\ifdim\width>\linewidth\linewidth\else\width\fi}{!}{" + table(res, cols, max_rows=8) + "}",
              r"\medskip"]
write("sparql_queries.tex", "\n".join(parts) + "\n")
std = read_csv(ROOT / "Results" / "Q04_qualifying_places.csv")
write("standings_table.tex", table(std, ["position", "team", "points", "netRunRate", "inQualifyingPlace"],
                                   "rlrrl", max_rows=10, size=r"\small") + "\n")

# rules and inference queries as listings
for f in list((ROOT / "SPARQL_Queries" / "rules").glob("*.ru")) + list((ROOT / "SPARQL_Queries" / "inference").glob("*.rq")):
    code = "".join(ch if ord(ch) < 128 else "-" for ch in f.read_text(encoding="utf-8"))
    (GEN / "queries" / f.name).write_text(code, encoding="utf-8")
for f in (ROOT / "prompts").glob("*.txt"):
    code = "".join(ch if ord(ch) < 128 else "-" for ch in f.read_text(encoding="utf-8"))
    (GEN / "queries" / f.name).write_text(code, encoding="utf-8")
inf = read_csv(ROOT / "Results" / "inference_examples.csv")
write("inference_table.tex", table(
    [{"Query": r["query"], "Off": r["rows_inference_off"], "On": r["rows_inference_on"],
      "Values with inference": (r["values_inference_on"][:90] + ("..." if len(r["values_inference_on"]) > 90 else ""))}
     for r in inf], ["Query", "Off", "On", "Values with inference"], "lrrp{8.2cm}") + "\n")

# ------------------------------------------------------------------ multi-hop evaluation
summ = (ROOT / "Results" / "iteration2" / "multihop_summary.md").read_text(encoding="utf-8")
mrows = []
for line in summ.splitlines():
    m = re.match(r"\| (.+?) \| (\d+|\*\*\d+\*\*) \| (\S+) \| (\S+) \| (\S+) \|", line)
    if m and not line.startswith("| Reasoning"):
        mrows.append({k: v.replace("**", "") for k, v in zip(["Reasoning type", "Questions", "Correct", "Accuracy", "Paths"], m.groups())})
write("multihop_table.tex", table(mrows, ["Reasoning type", "Questions", "Correct", "Accuracy", "Paths"], "lrrrr",
                                  max_rows=20, size=r"\small") + "\n")
bullets = [l[2:] for l in summ.splitlines() if l.startswith("- ")]
write("multihop_bullets.tex", r"\begin{itemize}\setlength\itemsep{1pt}" + "\n" +
      "\n".join(r"\item " + tex(b).replace("`", "") for b in bullets) + "\n" + r"\end{itemize}" + "\n")
ex = (ROOT / "Results" / "iteration2" / "multihop_examples.txt").read_text(encoding="utf-8")
blocks = ex.split("\n\n")
chosen = [b for b in blocks if b.startswith(("Q: Can LSG", "Q: At which venues has RR", "Q: Is there a chain of wins"))]
ex_tex = []
for b in chosen:
    lines = b.splitlines()
    keep = [l for l in lines if not l.startswith("  ") or len([x for x in lines[:lines.index(l)] if x.startswith("  ")]) < 9]
    text = "\n".join(keep)
    text = "".join(ch if ord(ch) < 128 else "-" for ch in text)
    ex_tex.append(text)
(GEN / "multihop_examples.txt").write_text("\n\n".join(ex_tex) + "\n", encoding="utf-8")

# ------------------------------------------------------------------ 10-CQ evaluation
rev = read_csv(ROOT / "Results" / "iteration2" / "cq_evaluation_review.csv")
yes = lambda v: "Yes" if str(v) == "True" else "No"  # noqa: E731
lines = [r"{\footnotesize", r"\begin{longtable}{p{2.5cm}p{2.8cm}p{3.3cm}p{3.3cm}p{1.0cm}p{1.0cm}}",
         r"\caption{LLM-only (A) vs KG-grounded (B) answers on 10 competency questions (" + tex(rev[0]["model"]) +
         r", temperature 0, identical settings). Answers summarised; full text in Appendix~\ref{app:answers}.}\label{tab:cq-eval}\\",
         r"\toprule \textbf{CQ / question} & \textbf{Expected answer} & \textbf{LLM only (A)} & \textbf{KG-grounded (B)} & \textbf{Correct? A/B} & \textbf{Evidence? A/B} \\ \midrule \endfirsthead",
         r"\toprule \textbf{CQ / question} & \textbf{Expected answer} & \textbf{LLM only (A)} & \textbf{KG-grounded (B)} & \textbf{Correct? A/B} & \textbf{Evidence? A/B} \\ \midrule \endhead",
         r"\bottomrule \endfoot"]
for r in rev:
    lines.append(rf"\textbf{{{r['cq']}}}: {tex(r['question'])} & {tex(r['expected'])} & {tex(r['note_llm_only'])} & "
                 rf"{tex(r['note'])} & {yes(r['correct_llm_only'])} / {yes(r['correct_kg_grounded'])} & "
                 rf"{yes(r['evidence_llm_only'])} / {yes(r['evidence_kg_grounded'])} \\ \midrule")
lines.append(r"\end{longtable}}")
write("cq_eval_table.tex", "\n".join(lines) + "\n")
ca = sum(r["correct_llm_only"] == "True" for r in rev)
cb = sum(r["correct_kg_grounded"] == "True" for r in rev)
eb = sum(r["evidence_kg_grounded"] == "True" for r in rev)
write("cq_eval_stats.tex", rf"\newcommand{{\evalA}}{{{ca}}}\newcommand{{\evalB}}{{{cb}}}\newcommand{{\evidB}}{{{eb}}}"
      rf"\newcommand{{\evalModel}}{{{tex(rev[0]['model'])}}}" + "\n")
full = [r"\begin{longtable}{p{1.9cm}p{6.8cm}p{6.8cm}}",
        r"\caption{Actual answers recorded in both conditions (verbatim, markdown removed).}\label{tab:cq-full}\\",
        r"\toprule \textbf{CQ} & \textbf{LLM only (A)} & \textbf{KG-grounded (B)} \\ \midrule \endfirsthead",
        r"\toprule \textbf{CQ} & \textbf{LLM only (A)} & \textbf{KG-grounded (B)} \\ \midrule \endhead",
        r"\bottomrule \endfoot"]
for r in rev:
    full.append(rf"\textbf{{{r['cq']}}} \newline \scriptsize {tex(r['question'])} & \scriptsize {md_to_tex(r['llm_only'])} & "
                rf"\scriptsize {md_to_tex(r['kg_grounded'])} \\ \midrule")
full.append(r"\end{longtable}")
write("cq_full_answers.tex", "\n".join(full) + "\n")

# ------------------------------------------------------------------ explainability
md = (ROOT / "Results" / "iteration2" / "explainability_examples.md").read_text(encoding="utf-8")
sections = re.split(r"^## ", md, flags=re.M)[1:]
out = []
for sec in sections:
    title, body = sec.split("\n", 1)
    q = re.search(r"\*\*Question:\*\* (.+)", body).group(1)
    ans = re.search(r"\*\*Generated text \(LLM answer\):\*\*\n\n((?:>.*\n?)+)", body).group(1)
    ans = "\n".join(l[1:].strip() for l in ans.splitlines())
    cited = re.search(r"\*\*Supporting evidence cited:\*\* (.+)", body).group(1)
    out += [rf"\subsection{{{tex(title.split(': ', 1)[1] if ': ' in title else title)}}}",
            rf"\noindent\textbf{{Question.}} {tex(q)}\par\smallskip"]
    for grp in re.findall(r"\*\*(Explicit knowledge[^*]*|Inferred knowledge[^*]*|Multi-hop reasoning paths[^*]*|"
                          r"Hypothetical scenario[^*]*)\*\*\n\n((?:- .*\n)+)", body):
        name, items = grp
        colour = {"E": "kgexplicit", "I": "kginferred", "M": "kgpath", "H": "kgscenario"}[name[0]]
        items_t = [tex(i[2:]) for i in items.strip().splitlines()][:7]
        out += [rf"\noindent\textcolor{{{colour}}}{{\textbf{{{tex(name)}}}}}",
                r"\begin{itemize}\setlength\itemsep{0pt}\footnotesize"] + [r"\item{} " + i for i in items_t] + [r"\end{itemize}"]
    out += [r"\noindent\textcolor{kggenerated}{\textbf{Generated text (LLM answer)}}",
            r"\begin{quote}\small " + md_to_tex(ans) + r"\end{quote}",
            rf"\noindent\textbf{{Supporting evidence cited:}} {tex(cited)}\par\medskip"]
write("explainability.tex", "\n".join(out) + "\n")
print("assets written:", sorted(p.name for p in GEN.glob("*.tex")), f"| {len(list(FIG.glob("*.jpg")))} figures | HEAD {head[:7]}")
