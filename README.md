# Atlas Change Review Agent

A Week 3 agentic extension of the fictional Atlas network project. A model chooses
local tools to investigate a proposed router configuration change. LangGraph runs
the loop and persists checkpoints to SQLite. The operator can clarify, reject,
revise or approve an exact review report. No live lab is required.

## Three-agent extension

Three roles review configuration, investigate potential impact, and draft a
conditional change plan. Final saving requires human approval of the exact report;
it never grants deployment authorization. Single-device reviews and bundles of
two to four routers are supported. See BUNDLE-SCOPE.txt for supported settings.

Latest scope: all four routers can be proposal targets. All 27 fictional Week 2
source files are copied as read-only evidence, including eight device baselines,
services, topology, designs, dated snapshot and synthetic logs. See CORPUS-SCOPE.txt.
New reviews preserve corpus snapshots; older reviews keep their original evidence.
The user ran all **46 offline tests successfully on 8 November 2026 (4.225s)**.
These use scripted models or mocks; they do not measure live reasoning accuracy.
Live bundle review reached human approval within budget, while London BGP
reasoning and unsupported-review continuation failed. Read the observed results
under evaluation/. This is a supervised prototype, not a deployment validator.

## Install and verify

Run from this folder, which has its own pyproject.toml:

```powershell
cd week3-agent
uv sync
uv run python -m unittest discover -s tests -v
uv run python run_review.py new --demo bgp
```

The preview makes no model calls or state writes. The 46 offline tests use
scripted models/mocks and temporary SQLite databases. They verify control flow,
permissions, evidence handling, bundles and approval boundaries; they do not
establish that the real model reasons correctly. Recent live results are in
evaluation/BUNDLE-OBSERVED-RESULTS.txt, W07-OBSERVED-RESULTS.txt and
W10-OBSERVED-RESULTS.txt. A clean independent installation is not yet verified.
If OneDrive reports incompatible hardlinks, use `uv sync --link-mode=copy`.

## Verify real tool calling

```powershell
uv run python run_review.py new --demo bgp --execute
```

Enter your Nebius key privately when prompted. This authorizes up to ten paid
model decisions for that review, bounded additionally by tool calls, reported
usage and active processing time. The model is configured through a ChatOpenAI
compatible endpoint. Real tool calls succeeded in the recorded development runs;
another operator still needs their own working account and key.

Copy the review ID printed before execution. Inspect or resume it:

```powershell
uv run python run_review.py show RUN_ID
uv run python run_review.py resume RUN_ID --action reply --note "Review the changed WAN neighbor AS"
uv run python run_review.py resume RUN_ID --action approve --hash CURRENT_REPORT_HASH
```

Use the action requested by the pending handoff. Rejection, cancellation and final
approval do not require a model call. Clarification, revision and retry may require
one, so the CLI requests the key again. agent.py forwards to this CLI; the earlier
custom-loop prototype has been replaced.

## Launch the application

```powershell
uv run streamlit run app.py
```

1. Choose single-device or bundle scope. Upload full .txt configurations (100 KB
   per device); bundles require two to four distinct supported hostnames and can
   include an optional shared .txt change document (20 KB).
2. Select a Dubai or London router and enter the review request.
3. Create the review and inspect its paid-call-free diff preview. Enter a Nebius
   key privately and start the agent. Bundle mode always uses three agents.
4. Watch tool activity and inspect the diff, findings and design evidence.
5. Respond to any clarification or unsupported-change handoff.
6. Approve, reject or request a revision of the exact report shown.
7. Download the approved artifact or the execution trace.

The failure demonstration selector injects a comparison-tool error once or on every
attempt. It is explicitly test data, not a claim about a remote service. The UI
can open saved reviews after a restart without re-uploading proposals.

## Architecture and authority

START -> model decision -> validated tools -> model decision
                         -> human interrupt -> resume / reject / unresolved
                         -> report approval -> transactional artifact save -> END

Role-specific tools provide configuration inspection, comparison, checks, design
lookup, corpus list/search/read, literal references, topology lookup, evidence
retrieval, human questions and specialist submission. Final saving is outside
model tool access. Backend
checks require baseline/diff inspection, relevant deterministic checks and design
evidence before approval. Unsupported changes force a human handoff and remain
explicitly unsupported even after acknowledgment. A mismatch is a departure from
baseline, not proof that an intended change is wrong or that deployment is safe.

Supported deterministic checks: neighbor remote-as in a BGP block, explicit
VRRP priority within its interface block, interface IPv4 addresses/masks,
explicit shutdown/no shutdown and dot1Q encapsulation, BFD timers/echo and BGP
neighbor BFD registration, and sequenced IPv4 prefix-list permit/deny entries
with ge/le qualifiers plus BGP and route-map list references. Missing prefix-list
definitions are flagged. Interface ranges, secondary addresses, IPv6, trunk
switchport settings and effective policy evaluation are unsupported. Bundle
comparisons cover each device separately; cross-device impact and sequencing
are model interpretations, not a network simulation or formal verification.
Absent commands do not establish platform defaults. Full IOS syntax, hardware compatibility,
other settings, network impact and deployment safety are outside validation scope.
Generated summaries remain unverified; deterministic findings accompany them.

SQLite checkpointers preserve messages, snapshots, attempts, findings and pending
interrupts. A separate SQLite artifact table records final approved reports with
unique review IDs and exact hashes. Saving is idempotent on replay. Stale approvals
are rejected before consuming an interrupt. A per-review OS-backed lock prevents
concurrent executions of the same review. Changing the proposal requires a new run.

## Limits and data handling

State persists in runtime/v2/ until the local operator removes it. It includes
proposal text and evidence, so keep this directory private. It is ignored by Git.
Keys remain outside graph state and are not stored by the app. Provider calls send
selected configuration/design evidence to Nebius. Do not upload real credentials
in configurations. This is a single-operator local prototype without login, not
an application to expose publicly. Checkpoints are automatic internal state writes;
only final artifact saving is gated by explicit approval.

Single-agent reviews allow ten model decisions, 24 tools and 50,000 reported
tokens. Three-agent reviews (including bundles) allow 18 decisions, 36 tools and
80,000 reported tokens across resumes. Approximately 300 active seconds is budgeted;
human waiting is separate. Failed provider requests can have unknown usage, so
reported tokens are not a guaranteed monetary cap. Each model request is timed
out after at most 45 seconds. One explicit model-error retry is allowed. Repeated
identical tool failures trigger an unresolved handoff. No automatic device action,
configuration modification, arbitrary shell execution or remote vector write exists.

## Evaluation and submission

See evaluation/CASES.txt for ten end-to-end expectations and a demonstration outline.
See evaluation/OBSERVED-RESULTS.txt for actual user-run development observations,
including recovery, human decisions, reopening saved reviews and model errors.
Do not report the proposed 8/10 success target as measured. Offline scripted tests,
real model tool selection and human-inclusive task completion must be distinguished.

An independently selected DXB-R01 prefix-list seq 30 permit-to-deny review
completed with human approval: 10 decisions, 14.142 active seconds, 27,529
reported tokens. See evaluation/PREFIX-USER-TEST.txt and samples/ if supplied in
the submission package. This is a single-device example, not a bundle benchmark.
Other live scenarios failed as documented; no overall success rate is claimed.

Submission needs a Google Doc describing the architecture, data, actual coding
prompts, iterations and learnings; a live demo of five minutes or less; and source
assets with setup instructions. Resources are copied fictional Week 2 baselines
and design notes. Evaluate live behavior after offline checks, including recovery,
restart/resume, rejection and approval. Keep Week 3 in its own repository before
publishing rather than accidentally adding runtime data to the Week 2 submission.
