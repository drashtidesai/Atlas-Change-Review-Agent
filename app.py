"""Run: uv run streamlit run app.py (from week3-agent)."""

import json
import difflib

import streamlit as st

from demo_cases import CASES, demo_proposal
from review_graph import MAX_STEPS, MAX_TOOL_CALLS, ReviewService
from review_tools import ROUTERS

st.set_page_config(page_title="Atlas Change Review Agent", page_icon=":material/rule:", layout="wide")
st.title("Atlas Change Review Agent")
st.write("Review a proposed router configuration against documented intent, with tool evidence and human decisions.")
st.caption("Fictional offline lab · BGP, VRRP, interfaces, BFD and prefix lists · No device access")

service = ReviewService()
with st.sidebar:
    st.header("Review connection")
    key = st.text_input("Nebius API key", type="password", key="nebius_key")
    st.caption("Key stays in app session memory, outside checkpoints. Use trusted local hosting.")
    st.caption("Single-agent reviews allow 10 model decisions / 24 tools; three-agent reviews allow 18 / 36 across resumes. Provider charges apply.")
    if st.button("Clear key"):
        st.session_state.pop("nebius_key", None)
        st.rerun()

with st.expander("Create a review", expanded="run_id" not in st.session_state):
    bundle_mode = st.radio("Change scope", ["Single device", "Device bundle"], key="change_scope") == "Device bundle"
    with st.form("new_review"):
        router = st.selectbox("Target router (single-device reviews)", ROUTERS, disabled=bundle_mode)
        st.caption("Proposal targets: four Dubai/London routers. Evidence: the full fictional Atlas corpus, including switch baselines and services. No live validation.")
        multi_agent = st.checkbox("Three-agent review: configuration, impact and change plan", value=bundle_mode, disabled=bundle_mode)
        st.caption("Three-agent mode: up to 18 paid model decisions, 36 tools and 80,000 reported tokens. Single-agent mode: 10 decisions and 24 tools. Both allow 300 active seconds; reported usage is not a monetary cap.")
        st.caption("New three-agent reviews are conditional offline assessments: live-data gaps are recorded as unknowns, ordinary clarification is limited to one answered question, and final human approval is always required. Unknown intent or authorization does not permit implementation.")
        if bundle_mode:
            st.caption("Upload two to four full proposed configurations, one per unique supported hostname. All devices share one review and approval to save its report.")
            uploads = st.file_uploader("Proposed device configurations (.txt)", type=["txt"], accept_multiple_files=True, key="bundle_uploads")
            document = st.file_uploader("Optional shared change document (.txt, up to 20 KB)", type=["txt"], key="bundle_document")
        else:
            source = st.selectbox("Proposal source", list(CASES) + ["Upload a proposal"])
            upload = st.file_uploader("Proposed full configuration (.txt)", type=["txt"])
        request = st.text_area("Change request and review goal", "Review the proposed change against the approved baseline. Identify deviations, evidence and limitations.")
        with st.expander("Failure demonstration"):
            fault = st.selectbox("Inject a comparison-tool failure", ["none", "transient_compare", "permanent_compare"])
            st.caption("Explicit test injection; these do not represent real service outages.")
        create = st.form_submit_button("Create review", type="primary")
    if create:
        try:
            if bundle_mode:
                from change_bundle import uploaded_proposals
                if not 2 <= len(uploads) <= 4 or any(item.size > 100_000 for item in uploads):
                    raise ValueError("Upload two to four configurations, each at most 100 KB.")
                if document is not None and document.size > 20000:
                    raise ValueError("Change document must be at most 20 KB.")
                proposals = uploaded_proposals([item.getvalue().decode("utf-8-sig") for item in uploads])
                change_document = document.getvalue().decode("utf-8-sig") if document is not None else ""
                st.session_state["run_id"] = service.create(router, "", request, fault, multi_agent=True,
                                                             proposals=proposals, change_document=change_document)
                st.rerun()
            elif source == "Upload a proposal":
                if upload is None or upload.size > 100_000:
                    raise ValueError("Upload a proposal of at most 100 KB.")
                proposal = upload.getvalue().decode("utf-8-sig")
            else:
                if upload is not None:
                    raise ValueError("An uploaded file is present. Select 'Upload a proposal' to use it, or remove it to use the demo.")
                proposal = demo_proposal(router, CASES[source])
            st.session_state["run_id"] = service.create(router, proposal, request, fault, multi_agent=multi_agent)
            st.rerun()
        except (ValueError, OSError, UnicodeError) as error:
            st.error(str(error))

reviews = service.store.list_runs()
if reviews:
    with st.expander("Resume a saved review"):
        picked = st.selectbox("Saved reviews", [row["id"] for row in reviews],
                              format_func=lambda value: next(f"{r['router']} · {r['created']} · {value[:10]}" for r in reviews if r['id'] == value))
        if st.button("Open saved review"):
            st.session_state["run_id"] = picked
            st.rerun()
if not st.session_state.get("run_id"):
    st.info("Create a review, then start the agent. The proposal and checkpoint are saved locally; no paid calls occur until you start.")
    st.stop()

run_id = st.session_state["run_id"]
snapshot = service.snapshot(run_id)
data = snapshot["data"]
if not data:
    st.error("Review checkpoint is missing. Create a new review; no artifact was approved.")
    st.stop()
st.caption("Review ID: " + run_id)
if data.get("steps", 0) == 0:
    st.info("Check the proposed differences below before starting paid processing.")
    with st.expander("Input preview — no model calls", expanded=True):
        for device, item in data.get("bundle_devices", {data["router"]: data}).items():
            st.write(device)
            preview = list(difflib.unified_diff((item["baseline"] or "").splitlines(), item["proposal"].splitlines(),
                                                fromfile=device + "/baseline", tofile=device + "/proposal", lineterm=""))
            st.code("\n".join(preview) or "No differences.", language="diff")
if data.get("target_routers"):
    st.caption("Bundle devices: " + ", ".join(data["target_routers"]))
c1, c2, c3 = st.columns(3)
c1.metric("Status", data["status"])
c2.metric("Model decisions", f"{data['steps']} / {data.get('max_steps', MAX_STEPS)}")
c3.metric("Active processing", f"{data['active_seconds']:.1f} s")
st.caption("Active time excludes human waiting. It does not promise a fixed completion time.")
st.caption("Review mode: " + ("Three agents · current role: " + data.get("agent_role", "configuration") if data.get("multi_agent") else "Single agent (original workflow)"))


def advance(decision=None):
    with st.status("Agent is working…", expanded=True) as status:
        def progress(update):
            for node, payload in update.items():
                if node == "__interrupt__":
                    continue
                current = payload.get("data", {}) if isinstance(payload, dict) else {}
                if current.get("events"):
                    last = current["events"][-1]
                    if last["kind"] == "tool":
                        result = last["result"]
                        st.write(f"Tool: {last['tool']} — {result.get('error') or result.get('status') or 'completed'}")
                    else:
                        st.write(f"{node}: {current.get('status')}")
        try:
            final = service.advance(run_id, key, decision, progress)
            status.update(label="Review paused or finished: " + final["status"], state="complete")
        except Exception as error:
            status.update(label="Execution stopped; inspect saved review before retrying", state="error")
            st.error(f"{type(error).__name__}: {str(error) if isinstance(error, ValueError) else 'A checkpoint may be available. Already-submitted calls can incur usage.'}")
            return
    st.rerun()


if snapshot["pending"]:
    pending = snapshot["pending"][0]
    kind = pending["kind"]
    st.subheader("Human decision required")
    st.info(pending["question"])
    if kind == "approval":
        st.caption("This approves saving the displayed review, never deployment. The model summary is unverified; inspect deterministic findings.")
        st.markdown(pending["report"]["summary"])
        if pending["report"].get("architecture") == "three_agent":
            st.subheader("Documented potential impact")
            st.write(pending["report"]["impact_assessment"]["assessment"])
            st.write("Unknowns: " + pending["report"]["impact_assessment"]["unknowns"])
            st.subheader("Proposed plan — not executed")
            st.json(pending["report"]["change_plan"])
        if pending["report"].get("unresolved_questions"):
            st.warning("Unresolved questions remain. Saving this conditional report does not authorize implementation.")
            st.json(pending["report"]["unresolved_questions"])
        st.json(pending["report"])
        options = ["approve", "reject", "revise"]
    else:
        if pending.get("unsupported_changes"):
            st.code("\n".join(pending["unsupported_changes"]))
        options = {"intake": ["reply", "cancel"], "clarification": ["reply", "cancel"],
                   "retry": ["retry", "cancel"], "unsupported": ["acknowledge", "cancel"],
                   "blocked": ["cancel"]}[kind]
    with st.form(f"human_{run_id}_{len(data['human_history'])}"):
        action = st.selectbox("Decision", options)
        note = st.text_area("Clarification or decision note")
        confirm = st.form_submit_button("Submit human decision")
    if confirm:
        if action in {"reply", "revise", "retry", "acknowledge"} and not key.strip():
            st.error("Enter your Nebius key to continue model execution.")
        else:
            advance({"action": action, "note": note, "report_hash": pending.get("report_hash")})
elif snapshot["next"]:
    st.caption("Starting or continuing authorizes model calls within the review's existing limits.")
    if st.button("Start or continue agent", type="primary", disabled=not key.strip()):
        advance()
else:
    st.write(data.get("outcome", "Review finished."))

artifact = service.store.artifact(run_id)
if artifact:
    st.success("The exact human-approved report is saved in local SQLite.")
    st.download_button("Download approved report", json.dumps(artifact, indent=2),
                       f"atlas-review-{run_id[:10]}.json", "application/json")
with st.expander("Request and configuration comparison"):
    st.write(data["request"])
    if data.get("bundle_devices"):
        st.write("Shared change document (source data):")
        st.text(data.get("change_document") or "No additional document supplied.")
        for device, item in data["bundle_devices"].items():
            st.write(device)
            st.caption("Baseline SHA-256: " + item["baseline_hash"] + " · Proposal SHA-256: " + item["proposal_hash"])
            st.code("\n".join(item.get("diff", [])) or "Comparison has not run yet.", language="diff")
    st.code("\n".join(data.get("diff", [])) or "Comparison has not run yet.", language="diff")
    st.json(data.get("checks", {}))
with st.expander("Tool activity and evidence"):
    for item in data["events"]:
        st.caption(item["at"] + " · " + item["kind"])
        st.json(item)
with st.expander("Usage and reproducible trace"):
    st.json(data["usage"])
    trace = {k: v for k, v in data.items() if k not in {"messages", "baseline", "proposal", "design", "corpus_snapshots", "agent_transcripts", "topology_snapshots", "bundle_devices"}}
    if data.get("bundle_devices"):
        from change_bundle import report_devices
        trace["devices"] = report_devices(data)
    st.download_button("Download review trace", json.dumps(trace, indent=2),
                       f"atlas-trace-{run_id[:10]}.json", "application/json")
