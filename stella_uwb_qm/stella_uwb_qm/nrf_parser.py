"""Parser for `run_fira_twr` stdout `# Ranging Data:` text blocks.

Output dict schema matches `parser.parse_json_line` so that
`uwb_publisher._publish_record` can handle either transport uniformly.
"""

_KEY_MAP = {
    'status': 'status',
    'macaddress': 'mac',
    'distance': 'distance',
    'aoaazimuth': 'aoa_azimuth',
    'aoaazfom': 'aoa_azimuth_fom',
    'aoaelevation': 'aoa_elevation',
    'aoaelevfom': 'aoa_elevation_fom',
    'rssi': 'rssi',
}

_UNIT_SUFFIXES = ('cm', 'deg', 'dBm', 'hex', '%')


def _normalize_key(raw: str) -> str:
    return raw.lower().replace(' ', '').replace('.', '')


def _strip_units(value: str) -> str:
    v = value.strip()
    for unit in _UNIT_SUFFIXES:
        if v.endswith(unit):
            v = v[: -len(unit)].strip()
            break
    return v


def _parse_float(value: str) -> float | None:
    try:
        return float(_strip_units(value))
    except ValueError:
        return None


def _parse_measurement(lines: list[str]) -> dict | None:
    fields: dict[str, str] = {}
    for line in lines:
        if ':' not in line:
            continue
        key_raw, _, value = line.partition(':')
        key = _normalize_key(key_raw)
        mapped = _KEY_MAP.get(key)
        if mapped is not None:
            fields[mapped] = value.strip()

    mac_raw = fields.get('mac')
    if mac_raw is None:
        return None
    mac = _strip_units(mac_raw)  # "00:00 hex" -> "00:00"
    anchor_id = '0x' + mac.replace(':', '')

    status_raw = fields.get('status', '')
    # e.g. "Ok (0x0)" -> first token "Ok"
    status_name = status_raw.split('(', 1)[0].strip().lower()
    if status_name in ('ok', 'success'):
        status = 0
        distance_cm = _parse_float(fields.get('distance', '0'))
        distance_m = (distance_cm or 0.0) / 100.0
    else:
        status = 255
        distance_m = 0.0

    def _f(key: str) -> float:
        v = fields.get(key)
        if v is None:
            return 0.0
        parsed = _parse_float(v)
        return parsed if parsed is not None else 0.0

    return {
        'anchor_id': anchor_id,
        'distance_m': distance_m,
        'status': status,
        'rssi': _f('rssi'),
        'pdr': 0.0,
        'cir': [],
        'aoa_azimuth': _f('aoa_azimuth'),
        'aoa_elevation': _f('aoa_elevation'),
        'aoa_azimuth_fom': _f('aoa_azimuth_fom'),
        'aoa_elevation_fom': _f('aoa_elevation_fom'),
    }


def parse_ranging_block(block: str) -> list[dict]:
    """Parse one `# Ranging Data:` block into a list of measurement dicts.

    Returns an empty list if the block header is missing or no measurements
    could be parsed.
    """
    if not block:
        return []
    lines = block.splitlines()
    if not lines or not lines[0].lstrip().startswith('# Ranging Data'):
        return []

    # Split into measurement sub-blocks delimited by "# Measurement" lines.
    groups: list[list[str]] = []
    current: list[str] | None = None
    for line in lines[1:]:
        if line.lstrip().startswith('# Measurement'):
            if current is not None:
                groups.append(current)
            current = []
            continue
        if current is not None:
            current.append(line)
    if current is not None:
        groups.append(current)

    results: list[dict] = []
    for g in groups:
        parsed = _parse_measurement(g)
        if parsed is not None:
            results.append(parsed)
    return results
