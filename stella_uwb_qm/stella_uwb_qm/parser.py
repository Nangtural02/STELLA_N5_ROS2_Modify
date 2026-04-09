import json


def parse_json_line(line: str) -> dict | None:
    try:
        data = json.loads(line)
    except (json.JSONDecodeError, TypeError):
        return None

    mac = data.get('mac', '')
    anchor_id = '0x' + mac.replace(':', '')

    status_str = data.get('status', '')
    if 'success' in status_str.lower() or 'ok' in status_str.lower():
        status = 0
        distance_m = data.get('distance_cm', 0.0) / 100.0
    else:
        status = 255
        distance_m = 0.0

    return {
        'anchor_id': anchor_id,
        'distance_m': distance_m,
        'status': status,
        'rssi': 0.0,
        'pdr': 0.0,
        'cir': [],
        'aoa_azimuth': data.get('aoa_azimuth', 0.0),
        'aoa_elevation': data.get('aoa_elevation', 0.0),
        'aoa_azimuth_fom': data.get('aoa_azimuth_fom', 0.0),
        'aoa_elevation_fom': data.get('aoa_elevation_fom', 0.0),
    }
