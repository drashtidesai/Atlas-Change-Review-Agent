# Atlas Change Review Agent

A supervised network configuration review application built with Streamlit,
LangGraph and Nebius. Upload proposed router configurations, compare them against
documented baselines, investigate potential impact, and review a proposed change
plan with supporting evidence.

## How it works

Three specialist agents work through a shared review:

1. **Configuration Reviewer** identifies changes and runs supported checks.
2. **Impact Investigator** examines configuration references, topology and design.
3. **Change Planner** drafts prechecks, verification, rollback objectives and stop
   conditions for engineering review.

The operator can answer questions, request revisions, reject a report, or approve
saving it. Approval applies to the report; deployment remains a separate process.
Single-device reviews and bundles of two to four routers are supported.

The included fictional Atlas dataset covers Dubai and London. Proposal targets
are `DXB-R01`, `DXB-R02`, `LON-R01` and `LON-R02`. The 27-file evidence corpus
contains device configurations, design notes, topology, services and synthetic
test logs. Each review preserves its own source snapshots and evidence hashes.

## Install and verify

Requirements: Python 3.12 or later and [uv](https://docs.astral.sh/uv/).
Run from the cloned repository:

```powershell
cd Atlas-Change-Review-Agent
uv sync
uv run python -m unittest discover -s tests -v
uv run python run_review.py new --demo bgp
```

The CLI preview validates the input without making model calls or creating
checkpoints. The test suite covers workflow control, permissions, evidence,
bundles and approval boundaries using scripted models and temporary databases.
If OneDrive reports incompatible hardlinks, use `uv sync --link-mode=copy`.

## Command-line usage

```powershell
uv run python run_review.py new --demo bgp --execute
```

The `--execute` flag starts a paid review using your Nebius account. Enter your
API key privately when prompted. The configured model is
`Qwen/Qwen3-235B-A22B-Instruct-2507` through a ChatOpenAI-compatible endpoint.

Copy the review ID printed before execution. Inspect or resume it:

```powershell
uv run python run_review.py show RUN_ID
uv run python run_review.py resume RUN_ID --action reply --note "Review the changed WAN neighbor AS"
uv run python run_review.py resume RUN_ID --action approve --hash CURRENT_REPORT_HASH
```

Use the action requested by the pending handoff. Rejection, cancellation and final
approval do not require a model call. Clarification, revision and retry may require
one, so the CLI requests the key again. `agent.py` also forwards to this CLI.

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

```text
START -> model decision -> validated tools -> model decision
                         -> human interrupt -> resume / reject / unresolved
                         -> report approval -> transactional artifact save -> END
```

Role-specific tools provide configuration inspection, comparison, checks, design
lookup, corpus list/search/read, literal references, topology lookup, evidence
retrieval, human questions and specialist submission. Final saving is outside
model tool access. Backend checks require baseline/diff inspection, relevant deterministic checks and design
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

## Tests and examples

- `tests/`: 46 offline tests covering configuration checks, role handoffs,
  interruptions, recovery, evidence access, bundle handling and exact approval.
- `inputs/`: fictional single-device proposals and coordinated bundle examples.
- `resources/`: configuration baselines and the read-only evidence corpus.
- `samples/`: a completed prefix-list review and its execution metrics.
- `evaluation/`: scenario definitions and detailed live-run observations.

Offline tests verify application behavior. Model-generated impact assessments
and plans require engineering review; detailed evaluation findings are kept
separately in [evaluation/](evaluation/).
