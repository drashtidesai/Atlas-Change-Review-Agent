"""CLI for the LangGraph agent. Preview by default; --execute authorizes paid calls."""

import argparse
import getpass
import json
from pathlib import Path

from demo_cases import demo_proposal
from review_tools import ROOT, ROUTERS, create_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("new")
    new.add_argument("--router", choices=ROUTERS, default="DXB-R01")
    source = new.add_mutually_exclusive_group(required=True)
    source.add_argument("--proposal", type=Path)
    source.add_argument("--demo", choices=["bgp", "vrrp", "combined", "unchanged", "unsupported", "interfaces", "bfd", "prefix_lists"])
    source.add_argument("--bundle", type=Path, nargs="+", help="Two to four full configuration files under inputs/.")
    new.add_argument("--change-document", type=Path, help="Optional shared UTF-8 .txt under inputs/, max 20 KB; bundle only.")
    new.add_argument("--request", default="Review the proposal against approved design and configuration.")
    new.add_argument("--fault", choices=["none", "transient_compare", "permanent_compare"], default="none")
    new.add_argument("--execute", action="store_true")
    new.add_argument("--multi-agent", action="store_true", help="Three specialists; up to 18 model decisions, 36 tools and 80000 reported tokens.")
    show = commands.add_parser("show")
    show.add_argument("run_id")
    resume = commands.add_parser("resume")
    resume.add_argument("run_id")
    resume.add_argument("--action", choices=["reply", "retry", "acknowledge", "cancel", "approve", "reject", "revise"])
    resume.add_argument("--note", default="")
    resume.add_argument("--hash")
    args = parser.parse_args()
    if args.command == "new":
        proposals, change_document = None, ""
        if args.bundle:
            from change_bundle import uploaded_proposals, bundle_state
            if not args.multi_agent:
                parser.error("--bundle requires --multi-agent.")
            texts = []
            for path in args.bundle:
                path = path.resolve()
                if not path.is_relative_to((ROOT / "inputs").resolve()) or path.suffix != ".txt" or path.stat().st_size > 100_000:
                    parser.error("Bundle configurations must be .txt files under inputs/, at most 100 KB each.")
                texts.append(path.read_text(encoding="utf-8-sig"))
            proposals = uploaded_proposals(texts)
            if args.change_document:
                path = args.change_document.resolve()
                if not path.is_relative_to((ROOT / "inputs").resolve()) or path.suffix != ".txt" or path.stat().st_size > 20000:
                    parser.error("Change document must be .txt under inputs/, at most 20 KB.")
                change_document = path.read_text(encoding="utf-8-sig")
            bundle_state(proposals, args.request, args.fault, change_document)
            proposal = ""
        elif args.change_document:
            parser.error("--change-document requires --bundle.")
        elif args.proposal:
            path = args.proposal.resolve()
            if not path.is_relative_to((ROOT / "inputs").resolve()) or path.suffix != ".txt":
                parser.error("Proposal must be a text file inside inputs/.")
            if path.stat().st_size > 100_000:
                parser.error("Maximum proposal size is 100 KB.")
            proposal = path.read_text(encoding="utf-8-sig")
        else:
            proposal = demo_proposal(args.router, args.demo)
        if proposals is None:
            create_state(args.router, proposal, args.request, args.fault)
        if not args.execute:
            print("Preview valid: proposal and snapshots ready. No model calls or checkpoints written.")
            print(f"Add --execute to start a bounded paid review (up to {18 if args.multi_agent else 10} model decisions).")
            return
    from review_graph import ReviewService
    service = ReviewService()

    def progress(update):
        for node, payload in update.items():
            if node == "__interrupt__":
                continue
            data = payload.get("data", {}) if isinstance(payload, dict) else {}
            print(f"Node {node}: status={data.get('status')} model decisions={data.get('steps')} tool calls={data.get('calls')}")

    if args.command == "new":
        key = getpass.getpass("Nebius key (hidden): ").strip()
        if not key:
            parser.error("Key required before execution.")
        run_id = service.create(args.router, proposal, args.request, args.fault, multi_agent=args.multi_agent,
                                proposals=proposals, change_document=change_document)
        print("Review ID:", run_id)
        service.advance(run_id, key, on_update=progress)
    elif args.command == "resume":
        run_id = args.run_id
        decision = {"action": args.action, "note": args.note, "report_hash": args.hash} if args.action else None
        needs_model = not decision or args.action in {"reply", "retry", "acknowledge", "revise"}
        key = getpass.getpass("Nebius key (hidden): ").strip() if needs_model else ""
        service.advance(run_id, key, decision, on_update=progress)
    else:
        run_id = args.run_id
    snapshot = service.snapshot(run_id)
    data = snapshot["data"]
    print(json.dumps({key: value for key, value in data.items()
                      if key not in {"messages", "baseline", "proposal", "design", "events", "corpus_snapshots", "agent_transcripts", "topology_snapshots", "bundle_devices"}}, indent=2))
    if snapshot["pending"]:
        print("Pending human decision:", json.dumps(snapshot["pending"], indent=2))


if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        print(f"Stopped ({type(error).__name__}). Review checkpoints may be available; earlier calls may incur usage.")
        raise SystemExit(1)
