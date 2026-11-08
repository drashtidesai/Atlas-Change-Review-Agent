"""Conditional offline-review policy; unknowns never become approvals."""
TOPICS = ("intent", "authorization", "documentary_evidence", "operational_validation", "other")


def human_question(state, question, topic="other"):
    answered = sum(item.get("action") == "reply" and item.get("kind") == "clarification"
                   for item in state.get("human_history", []))
    if state.get("efficient_review") and (topic in {"operational_validation", "documentary_evidence"} or answered >= 1):
        record = {"question": question, "topic": topic,
                  "resolution": "unverified; engineer confirmation required before implementation"}
        records = state.setdefault("review_unknowns", [])
        if record not in records:
            records.append(record)
        return {"status": "recorded_unknown", "unknown": record,
                "instruction": "Continue conditional offline review. Search available documents if relevant. Do not infer answers, intent, authorization, live support or deployment permission. Human approval remains required."}
    state.update(status="needs_human", human_kind="clarification", pending_question=question)
    return {"status": "needs_human", "question": question}


def finishing_tool(state):
    if not state.get("efficient_review"):
        return None
    role = state.get("agent_role", "configuration")
    turns = state.get("role_turns", {}).get(role, 0)
    if role == "configuration":
        ready = state.get("baseline_read") and "diff" in state and (
            set(state.get("required_domains", [])) <= set(state["checks"]) and
            set(state.get("required_domains", [])) <= set(state["design_read"]))
        return "submit_review" if ready and (state.get("compact_workflow") or turns >= 4) else None
    if role == "impact":
        ready = {"find_references", "lookup_topology"} <= set(state.get("specialist_queries", []))
        allowance = 3 if state.get("compact_workflow") else 4
        return "submit_impact" if ready and state.get("specialist_evidence") and turns >= allowance else None
    return "submit_plan" if state.get("impact_assessment") and (state.get("compact_workflow") or turns >= 2) else None
