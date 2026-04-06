"""Parse UWB serial output into structured data.

Supports SESSION_INFO_NTF CLI format. Designed to be extended
when firmware adds new fields (RSSI, CIR, etc.).
"""
import re

# SESSION_INFO_NTF: {session_handle=1, sequence_number=126651, block_index=126651, n_measurements=1
#  [mac_address=0x0001, status="SUCCESS", distance[cm]=9]}
_NTF_PATTERN = re.compile(
    r'mac_address=(0x[0-9a-fA-F]+),\s*'
    r'status="(\w+)",\s*'
    r'distance\[cm\]=(\d+)'
)


def parse_ntf_line(line: str) -> dict | None:
    """Parse a SESSION_INFO_NTF message.

    Returns dict with keys: anchor_id, distance_m, status, rssi, pdr
    or None if the line doesn't match.
    """
    m = _NTF_PATTERN.search(line)
    if not m:
        return None

    anchor_id = m.group(1)
    status_str = m.group(2)
    distance_cm = int(m.group(3))

    success = status_str == "SUCCESS"
    return {
        'anchor_id': anchor_id,
        'distance_m': distance_cm / 100.0 if success else 0.0,
        'status': 0 if success else 255,  # 0=LOS, 255=UNKNOWN
        'rssi': 0.0,
        'pdr': 0.0,
        'cir': [],
    }
