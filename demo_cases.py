"""Deliberately edited fictional proposals; these are not device configurations to deploy."""

import re
from review_tools import read_resource

CASES = {"BGP neighbor change": "bgp", "VRRP priority change": "vrrp",
         "Interface WAN shutdown": "interfaces", "BFD timer change": "bfd",
         "Prefix-list permit to deny": "prefix_lists",
         "Combined BGP and VRRP": "combined", "No changes": "unchanged",
         "Unsupported description change": "unsupported"}


def demo_proposal(router, case):
    text = read_resource(f"{router}.txt")
    if text is None:
        raise ValueError("Baseline unavailable.")
    if case not in {"bgp", "vrrp", "combined", "unchanged", "unsupported", "interfaces", "bfd", "prefix_lists"}:
        raise ValueError("Unknown demo case.")
    if case in {"bgp", "combined"}:
        local_as = re.search(r"^router bgp (\d+)$", text, re.M)
        peers = re.findall(r"^ neighbor (\S+) remote-as (\d+)$", text, re.M)
        external = next(((peer, asn) for peer, asn in peers if local_as and asn != local_as[1]), None)
        if external is None:
            raise ValueError("Demo baseline does not contain expected peer.")
        peer, asn = external
        old = f"neighbor {peer} remote-as {asn}"
        text = text.replace(old, f"neighbor {peer} remote-as 65030", 1)
    if case in {"vrrp", "combined"}:
        setting = re.search(r"^ vrrp (\d+) priority (\d+)$", text, re.M)
        if not setting:
            raise ValueError("Expected VRRP baseline absent.")
        old = f"vrrp {setting[1]} priority {setting[2]}"
        text = text.replace(old, f"vrrp {setting[1]} priority 90", 1)
    if case == "unsupported":
        text = text.replace("description UNUSED", "description RESERVED-FUTURE", 1)
    if case == "interfaces":
        text = text.replace(" no shutdown", " shutdown", 1)
    if case == "bfd":
        text = text.replace("bfd interval 300 min_rx 300 multiplier 3",
                            "bfd interval 1000 min_rx 1000 multiplier 3", 1)
    if case == "prefix_lists":
        text = text.replace("LOCAL-SITE seq 10 permit", "LOCAL-SITE seq 10 deny", 1)
    return text
