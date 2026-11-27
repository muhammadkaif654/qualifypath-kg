"""
Create the QualifyPath-KG repository in a running GraphDB, load the graph, apply the SPARQL rules,
and check every query against the results produced offline.

Usage (GraphDB Desktop running on http://localhost:7200):
    python RDF_Knowledge_Graph/graphdb/load_graphdb.py            # create if missing, load, check
    python RDF_Knowledge_Graph/graphdb/load_graphdb.py --reset    # delete and recreate the repository first

Uses only the Python standard library.
"""
import csv
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

GRAPHDB = "http://localhost:7200"
REPO = "qualifypath-ipl2026"
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def request(method, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def repositories():
    status, body = request("GET", f"{GRAPHDB}/rest/repositories", headers={"Accept": "application/json"})
    if status != 200:
        sys.exit(f"GraphDB not reachable at {GRAPHDB} (HTTP {status}). Start GraphDB Desktop first.")
    return [r["id"] for r in json.loads(body)]


def create_repository():
    boundary = uuid.uuid4().hex
    config = (HERE / "repo-config.ttl").read_bytes()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"config\"; filename=\"repo-config.ttl\"\r\n"
            f"Content-Type: text/turtle\r\n\r\n").encode() + config + f"\r\n--{boundary}--\r\n".encode()
    status, text = request("POST", f"{GRAPHDB}/rest/repositories", body,
                           {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    if status not in (200, 201, 204):
        sys.exit(f"Could not create repository (HTTP {status}): {text[:500]}")


def upload_turtle(path):
    status, text = request("POST", f"{GRAPHDB}/repositories/{REPO}/statements", path.read_bytes(),
                           {"Content-Type": "text/turtle"})
    if status not in (200, 204):
        sys.exit(f"Upload of {path.name} failed (HTTP {status}): {text[:500]}")


def update(sparql):
    status, text = request("POST", f"{GRAPHDB}/repositories/{REPO}/statements", sparql.encode("utf-8"),
                           {"Content-Type": "application/sparql-update"})
    if status not in (200, 204):
        sys.exit(f"Update failed (HTTP {status}): {text[:500]}")


def select(sparql, infer=True):
    data = urllib.parse.urlencode({"query": sparql, "infer": str(infer).lower()}).encode()
    status, text = request("POST", f"{GRAPHDB}/repositories/{REPO}", data,
                           {"Content-Type": "application/x-www-form-urlencoded", "Accept": "text/csv"})
    if status != 200:
        sys.exit(f"Query failed (HTTP {status}): {text[:500]}")
    return list(csv.reader(io.StringIO(text)))[1:]


def count(infer):
    rows = select("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }", infer)
    return int(rows[0][0])


if __name__ == "__main__":
    repos = repositories()
    if REPO in repos and "--reset" in sys.argv:
        request("DELETE", f"{GRAPHDB}/rest/repositories/{REPO}")
        repos.remove(REPO)
        print(f"Deleted repository {REPO}")
    if REPO not in repos:
        create_repository()
        print(f"Created repository {REPO} (ruleset OWL2-RL optimized)")
        upload_turtle(ROOT / "Ontology" / "qualifypath.ttl")
        upload_turtle(ROOT / "RDF_Knowledge_Graph" / "ipl2026_abox.ttl")
        print(f"Loaded ontology + A-Box: {count(False)} explicit triples, {count(True)} with inference")
        for rule in sorted((ROOT / "SPARQL_Queries" / "rules").glob("*.ru")):
            update(rule.read_text(encoding="utf-8"))
            print(f"Applied {rule.stem}")
        print(f"After rules: {count(False)} explicit, {count(True)} with inference")
    else:
        print(f"Repository {REPO} already exists - checking it (use --reset to rebuild)")

    print("\nQuery check (GraphDB rows vs offline Results/*.csv):")
    ok = True
    for q in sorted((ROOT / "SPARQL_Queries").glob("Q*.rq")):
        rows = select(q.read_text(encoding="utf-8"))
        with open(ROOT / "Results" / f"{q.stem}.csv", encoding="utf-8") as f:
            expected = len(list(csv.reader(f))) - 1
        same = len(rows) == expected
        ok &= same
        print(f"  {q.stem:28s} {len(rows):3d} rows  {'OK' if same else f'expected {expected}'}")

    print("\nInference check (Include inferred data off -> on):")
    for q in sorted((ROOT / "SPARQL_Queries" / "inference").glob("I*.rq")):
        text = q.read_text(encoding="utf-8")
        off, on = select(text, infer=False), select(text, infer=True)
        print(f"  {q.stem:32s} off {len(off)} rows -> on {len(on)} rows: {', '.join(r[0].rsplit('#', 1)[-1] for r in on)}")
    print("\nAll query row counts match." if ok else "\nSome row counts differ - see above.")
