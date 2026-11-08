"""Prepare coordinated two-device BFD demo inputs; no models or checkpoints."""
import argparse
from change_bundle import bundle_state
from demo_cases import demo_proposal
from review_tools import ROOT, dispatch

REQUEST = (
    "Review this coordinated, planned and undeployed BFD change on DXB-R01 and LON-R01. "
    "Both WAN-A endpoints are proposed at 1000 ms instead of 300 ms, multiplier 3 unchanged. "
    "Assess both proposed states together, the temporary state during sequencing, dependencies, "
    "conditional verification and coordinated rollback objectives. The design exception remains "
    "unjustified by operational evidence. Live negotiated timers are unavailable. Deployment is not authorized.")
DOCUMENT = (
    "Scope: DXB-R01 and LON-R01 WAN-A interfaces only.\n"
    "Proposed change: BFD transmit and minimum receive intervals 300 to 1000 ms; multiplier remains 3.\n"
    "Status: planned, undeployed; review and planning only.\n"
    "No operational justification for the design exception is supplied.\n"
    "Do not infer deployment authorization, negotiated timers or measured failover.\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    proposals = {router: demo_proposal(router, "bfd") for router in ("DXB-R01", "LON-R01")}
    state = bundle_state(proposals, REQUEST, change_document=DOCUMENT)
    result = dispatch(state, "inspect_proposal", {})
    if "error" in result:
        raise ValueError("Demo inspection failed: " + result["error"])
    print(REQUEST)
    if args.prepare:
        directory = ROOT / "inputs" / "bundle-demo"
        directory.mkdir(parents=True, exist_ok=True)
        for router, text in proposals.items():
            (directory / f"{router}-proposed.txt").write_text(text, encoding="utf-8")
        (directory / "change-document.txt").write_text(DOCUMENT, encoding="utf-8")
        print("Prepared inputs/bundle-demo/: two configurations and one shared change document.")
    else:
        print("Preview valid. Add --prepare to write demo inputs.")
    print("No model calls, paid review or checkpoints. This is input preparation, not live evaluation.")


if __name__ == "__main__":
    main()
