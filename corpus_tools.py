"""Read-only, per-review snapshots of the fictional Atlas evidence corpus."""
import re
from pathlib import Path

from review_tools import ROOT, fingerprint, schema

CATEGORIES = {
    "design": "design_document",
    "topology": "topology_document",
    "intended-configs": "intended_configuration",
    "running-config-snapshots": "dated_fictional_snapshot",
    "synthetic-logs": "synthetic_log",
    "references": "reference_notes",
}
NAMES = {"list_sources", "search_sources", "read_source"}
NOTICE = ("Fictional offline documentation only. Intended configuration is not running state; "
          "dated snapshots are not current state; synthetic logs are assigned simulations, "
          "not device observations. Links in reference notes are not fetched.")


def snapshot_corpus(directory=None):
    root = Path(directory or ROOT / "resources" / "atlas-corpus").resolve()
    snapshots = {}
    for category, kind in CATEGORIES.items():
        for path in sorted((root / category).glob("*")):
            if path.suffix not in {".txt", ".csv"} or not path.is_file() or path.is_symlink():
                continue
            if not path.resolve().is_relative_to(root):
                raise ValueError("Corpus resource outside allowed directory.")
            text = path.read_text(encoding="utf-8-sig")
            snapshots[f"corpus/{category}/{path.name}"] = {
                "text": text, "document_type": kind, "sha256": fingerprint(text),
                "line_count": len(text.splitlines()), "evidence_is_simulated": kind == "synthetic_log"}
    return snapshots


def inventory(state):
    return [{"source": source, **{key: value for key, value in document.items() if key != "text"}}
            for source, document in state.get("corpus_snapshots", {}).items()]


def evidence_line(state, source, number, document):
    identifier = f"{source}:L{number}"
    record = {"source": source, "line": number,
              "text": document["text"].splitlines()[number - 1],
              "document_type": document["document_type"], "sha256": document["sha256"],
              "evidence_is_simulated": document["evidence_is_simulated"]}
    state.setdefault("specialist_evidence", {})[identifier] = record
    state.setdefault("corpus_accessed", {})[source] = document["sha256"]
    return {"id": identifier, **record}


def dispatch_corpus(state, name, args):
    shapes = {"list_sources": set(), "search_sources": {"query"},
              "read_source": {"source", "line_start", "line_end"}}
    if name not in shapes or not isinstance(args, dict) or set(args) != shapes[name]:
        return {"error": "invalid_corpus_arguments", "retryable": False}
    documents = state.get("corpus_snapshots")
    if documents is None:
        return {"error": "corpus_not_snapshotted_for_this_run", "retryable": False,
                "note": "Historical review evidence is not silently replaced; create a new review for expanded corpus access."}
    if name == "list_sources":
        return {"sources": inventory(state), "notice": NOTICE}
    if name == "read_source":
        source, start, end = args["source"], args["line_start"], args["line_end"]
        if not isinstance(source, str) or source not in documents:
            return {"error": "source_not_in_snapshot", "retryable": True}
        if any(not isinstance(value, int) or isinstance(value, bool) for value in (start, end)) or not (
                1 <= start <= end <= documents[source]["line_count"] and end - start < 40):
            return {"error": "invalid_line_range_maximum_40", "retryable": True}
        return {"matches": [evidence_line(state, source, number, documents[source])
                            for number in range(start, end + 1)], "notice": NOTICE}
    query = args["query"]
    if not isinstance(query, str) or not query.strip() or len(query) > 200:
        return {"error": "invalid_search_query", "retryable": False}
    terms = set(re.findall(r"[\w./:-]+", query.casefold()))
    if not terms:
        return {"error": "query_requires_search_terms", "retryable": True}
    matches = []
    for source, document in documents.items():
        for number, line in enumerate(document["text"].splitlines(), 1):
            lowered = line.casefold()
            hits = sum(term in lowered for term in terms)
            if hits:
                score = hits / len(terms) + (2 if query.casefold() in lowered else 0)
                # Source-name matches break ties, not replace content evidence.
                score += sum(term in source.casefold() for term in terms) / (10 * len(terms))
                matches.append((score, source, number, document))
    matches.sort(key=lambda item: (-item[0], item[1], item[2]))
    return {"matches": [evidence_line(state, source, number, document)
                        for _, source, number, document in matches[:8]],
            "truncated": len(matches) > 8, "search_method": "bounded lexical line search",
            "notice": NOTICE, "note": "Search rank is not authority. Read the relevant source block before interpreting dependencies."}


CORPUS_TOOLS = [
    schema("list_sources", "List available snapshotted Atlas files and evidence types; no arbitrary filesystem access."),
    schema("search_sources", "Search all eight device configs, design, topology, services, fictional snapshot and synthetic logs. Returns up to eight numbered lines; use device name plus setting.", {"query": {"type": "string"}}),
    schema("read_source", "Read up to 40 exact lines from one listed source. Inspect a peer/interface block, policy or design section. These are offline documents, never live state.", {
        "source": {"type": "string"}, "line_start": {"type": "integer"}, "line_end": {"type": "integer"}}),
]
