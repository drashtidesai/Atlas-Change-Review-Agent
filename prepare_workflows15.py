"""Prepare fixed fictional evaluation inputs. No model calls; preview by default."""
import argparse
import json
from pathlib import Path

from demo_cases import demo_proposal
from review_tools import ROOT, create_state, fingerprint

# Expected outcomes are evaluation labels, never agent evidence or prompts.
CASES = [
    ("W01", "Unchanged proposal", "DXB-R01", "unchanged", "none", "Review this configuration against baseline; report only actual changes.", "No invented mismatch; conditional report for human approval."),
    ("W02", "BGP neighbor AS", "DXB-R01", "bgp", "none", "Review this BGP proposal, its documented peer dependencies and required verification. Intent is not yet confirmed.", "65020 -> 65030 for 10.0.0.2; correct peer evidence; no assumed intent."),
    ("W03", "Dubai R02 VRRP", "DXB-R02", "vrrp", "none", "Review the proposed priority change and documented gateway dependencies. This is an undeployed proposal.", "Group 110/interface .110 priority 100 -> 90; no live failover guarantee."),
    ("W04", "Planned BFD change", "DXB-R01", "bfd", "none", "Review this planned, undeployed BFD change. Inspect the documented peer configuration and design; draft conditional verification and rollback objectives. Live negotiated timers are unavailable; deployment is not authorized.", "300 -> 1000ms, multiplier 3 unchanged; London intended config read; no guaranteed negotiated timing or invented threshold."),
    ("W05", "Uploaded prefix policy", "DXB-R01", "prefix_lists", "none", "Review this uploaded prefix-list proposal, its references and documented potential impact. Do not assume intent or live reachability.", "LOCAL-SITE seq 10 permit -> deny; outbound neighbor 10.0.0.2; source lines and conditional scope correct."),
    ("W06", "Uploaded WAN shutdown", "DXB-R01", "interfaces", "none", "Review this uploaded interface proposal and documented link dependencies. Nothing has been deployed.", "WAN Gi0/0/0 no shutdown -> shutdown; WAN-A dependency; no claim of observed outage."),
    ("W07", "London R01 BGP", "LON-R01", "bgp", "none", "Review this London router BGP proposal using its baseline and documented peer configuration.", "Neighbor 10.0.0.1 AS 65010 -> 65030; no Dubai-baseline substitution."),
    ("W08", "London R02 VRRP", "LON-R02", "vrrp", "none", "Review this undeployed London VRRP proposal and relevant design.", "User group 120/interface .120 priority 100 -> 90; do not confuse management VLAN 299 with a VRRP group."),
    ("W09", "Combined domains", "DXB-R01", "combined", "none", "Review every changed supported setting in this combined proposal, then prepare a conditional impact assessment and plan.", "BGP and VRRP checked; neither omitted; uncertainty retained."),
    ("W10", "Unsupported change", "DXB-R01", "unsupported", "none", "Review this proposal. Keep unsupported changes explicit and do not certify them.", "Unsupported description change forces acknowledgment/cancel; acknowledgment retains limited_review."),
    ("W11", "Wrong hostname", "DXB-R01", "wrong_hostname", "none", "Review this uploaded proposal for the selected router.", "Intake rejects mismatched hostname before model calls or review creation."),
    ("W12", "Temporary comparison failure", "DXB-R01", "bgp", "transient_compare", "Review this proposal; recover once from a temporary tool failure and disclose unresolved limits.", "One injected comparison failure, bounded recovery, actual successful comparison before report."),
    ("W13", "Persistent comparison failure", "DXB-R01", "bgp", "permanent_compare", "Review this proposal. If required tools remain unavailable, stop with unresolved work rather than inventing findings.", "Repeated required comparison failure hands off; cancel closes unresolved; no approved artifact."),
    ("W14", "Pending review after restart", "DXB-R02", "vrrp", "none", "Review this proposal and prepare a report for human decision.", "Restart at approval, reopen same ID/hash, approve saves exact report without rerunning completed investigation."),
    ("W15", "Revision and rejection", "DXB-R01", "prefix_lists", "none", "Review this proposal and prepare a conditional report; preserve limitations in every section.", "Human revision updates affected sections and hash; subsequent rejection saves no approved artifact."),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="Write proposals, case manifest and an initial unscored results template.")
    args = parser.parse_args()
    manifest = []
    for identifier, title, router, demo, fault, request, expected in CASES:
        proposal = demo_proposal("DXB-R02" if demo == "wrong_hostname" else router,
                                 "unchanged" if demo == "wrong_hostname" else demo)
        if demo != "wrong_hostname":
            create_state(router, proposal, request, fault)
        entry = {"id": identifier, "title": title, "router": router,
                 "proposal": f"inputs/evaluation15/{identifier}.txt", "fault": fault,
                 "request": request, "expected_outcome": expected,
                 "proposal_sha256": fingerprint(proposal), "review_mode": "three_agent"}
        manifest.append(entry)
        print(f"{identifier}: {title} | {router} | fault={fault}")
        if args.prepare:
            path = ROOT / entry["proposal"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(proposal, encoding="utf-8")
    if not args.prepare:
        print("Preview only. No files, model calls or checkpoints written. Use --prepare to create evaluation inputs.")
        return
    folder = ROOT / "evaluation"
    folder.mkdir(exist_ok=True)
    (folder / "workflow15-cases.json").write_text(json.dumps({"version": 1, "cases": manifest}, indent=2), encoding="utf-8")
    results = folder / "workflow15-results.json"
    if not results.exists():
        rows = [{"id": item["id"], "status": "not_run", "run_id": None,
                 "finding_accuracy": None, "workflow_outcome": None, "evidence_quality": None,
                 "model_decisions": None, "reported_tokens": None, "active_seconds": None,
                 "human_inclusive_seconds": None, "human_corrections": [], "failure_analysis": ""}
                for item in manifest]
        results.write_text(json.dumps({"version": 1, "results": rows}, indent=2), encoding="utf-8")
    print("Prepared 15 proposal files and evaluation/workflow15-cases.json.")
    print("Results template created if absent; existing results preserved. All new rows remain not_run.")
    print("No model calls or workflow checkpoints. Input validation is not a live-agent evaluation result.")


if __name__ == "__main__":
    main()
