"""
Build the Iteration 1 submission ZIP: AI3001_Iteration1_<TeamName>.zip

Usage (from this folder):  python make_submission.py
Rebuild it after any change (e.g. after filling in member contributions in the report).
"""
import zipfile
from pathlib import Path

TEAM_NAME = "QualifyPath-KG"
ROOT = Path(__file__).resolve().parent
NAME = f"AI3001_Iteration1_{TEAM_NAME}"
FOLDERS = ["Report", "Dataset", "Ontology", "RDF_Knowledge_Graph", "SPARQL_Queries", "Results", "Visualization"]
TOP_FILES = ["README.md", "make_submission.py"]
SKIP = {"__pycache__", ".ipynb_checkpoints"}

out = ROOT / f"{NAME}.zip"
count = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in TOP_FILES:
        z.write(ROOT / f, f"{NAME}/{f}")
        count += 1
    for folder in FOLDERS:
        for p in sorted((ROOT / folder).rglob("*")):
            if p.is_file() and not SKIP.intersection(p.parts) and not p.name.startswith("~$"):
                z.write(p, f"{NAME}/{p.relative_to(ROOT).as_posix()}")
                count += 1
print(f"Wrote {out.name}: {count} files, {out.stat().st_size / 1024:.0f} KB")
