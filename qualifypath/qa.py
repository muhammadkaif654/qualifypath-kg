"""
Question answering in two conditions with the same LLM and settings:

  grounded : question -> KG retrieval / multi-hop reasoning -> numbered facts -> LLM -> answer + evidence
  llm_only : question -> LLM (no graph)

If retrieval finds nothing in the graph for the question, the grounded pipeline does not call the LLM
and returns an insufficient-evidence answer, so nothing can be invented.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import llm
from .retriever import Fact, Retrieval, Retriever

INSUFFICIENT = "INSUFFICIENT EVIDENCE"


@dataclass
class Answer:
    question: str
    mode: str
    answer: str
    seconds: float = 0.0
    retrieval: Retrieval | None = None
    cited: list[Fact] = field(default_factory=list)
    insufficient: bool = False
    warning: str = ""


_retriever: Retriever | None = None


def retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def ask_grounded(question: str) -> Answer:
    r = retriever().retrieve(question)
    if not r.facts:
        return Answer(question, "grounded", f"{INSUFFICIENT}: the knowledge graph has no teams, venues, matches "
                      "or rules matching this question, so it cannot be answered from the graph.",
                      retrieval=r, insufficient=True)
    user = f"Facts retrieved from the knowledge graph:\n{r.context()}\n\nQuestion: {question}"
    text, secs = llm.chat(llm.prompt("grounded_system"), user)
    ids = list(dict.fromkeys(re.findall(r"\[?(F\d+)\]?", text)))
    by_id = {f.id: f for f in r.facts}
    cited = [by_id[i] for i in ids if i in by_id]
    insufficient = text.upper().startswith(INSUFFICIENT)
    warning = "" if cited or insufficient else "The answer cites no retrieved fact; treat it as unsupported."
    return Answer(question, "grounded", text, secs, r, cited, insufficient, warning)


def ask_llm_only(question: str) -> Answer:
    text, secs = llm.chat(llm.prompt("llm_only_system"), question)
    return Answer(question, "llm_only", text, secs)


if __name__ == "__main__":
    import sys
    for q in sys.argv[1:]:
        a = ask_grounded(q)
        print(f"Q: {q}\nA: {a.answer}\nCited: {[f.id for f in a.cited]}  {a.warning}\n")
