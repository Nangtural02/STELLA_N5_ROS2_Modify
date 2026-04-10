from stella_uwb_qm.nrf_parser import parse_ranging_block


BLOCK_SEQ18 = """# Ranging Data:
        session handle:         2147483649
        sequence n:         18
        ranging interval:   200 ms
        measurement type:   Twr
        Mac add size:       2
        primary session id: 0x0
        n of measurement:   1
        # Measurement 1:
            status:                 Ok (0x0)
            mac address:            00:00 hex
            hw fp detection error:  0
            timestamp conf level:   No FOM
            distance:               690.0 cm
            AoA azimuth:            1.546875 deg
            AoA az. FOM:            0.0 %
            AoA elevation:          18.828125 deg
            AoA elev. FOM:          0.0 %
            AoA dest azimuth:       0.0 deg
            AoA dest az. FOM:       0.0 %
            AoA dest elevation:     0.0 deg
            AoA dest elev. FOM:     0.0 %
            slot in error:          0
            rssi:                   -0.0 dBm
"""

BLOCK_SEQ19 = """# Ranging Data:
        session handle:         2147483649
        sequence n:         19
        ranging interval:   200 ms
        measurement type:   Twr
        Mac add size:       2
        primary session id: 0x0
        n of measurement:   1
        # Measurement 1:
            status:                 Ok (0x0)
            mac address:            00:01 hex
            hw fp detection error:  0
            timestamp conf level:   No FOM
            distance:               700.0 cm
            AoA azimuth:            -10.7578125 deg
            AoA az. FOM:            0.0 %
            AoA elevation:          16.390625 deg
            AoA elev. FOM:          0.0 %
            AoA dest azimuth:       0.0 deg
            AoA dest az. FOM:       0.0 %
            AoA dest elevation:     0.0 deg
            AoA dest elev. FOM:     0.0 %
            slot in error:          0
            rssi:                   -0.0 dBm
"""


def test_parse_block_seq18():
    results = parse_ranging_block(BLOCK_SEQ18)
    assert len(results) == 1
    r = results[0]
    assert r['anchor_id'] == '0x0000'
    assert r['status'] == 0
    assert abs(r['distance_m'] - 6.90) < 1e-9
    assert abs(r['aoa_azimuth'] - 1.546875) < 1e-9
    assert abs(r['aoa_elevation'] - 18.828125) < 1e-9
    assert r['aoa_azimuth_fom'] == 0.0
    assert r['aoa_elevation_fom'] == 0.0
    assert r['rssi'] == 0.0  # -0.0 parses to 0.0
    assert r['pdr'] == 0.0
    assert r['cir'] == []


def test_parse_block_seq19_negative_aoa():
    results = parse_ranging_block(BLOCK_SEQ19)
    assert len(results) == 1
    r = results[0]
    assert r['anchor_id'] == '0x0001'
    assert abs(r['distance_m'] - 7.00) < 1e-9
    assert abs(r['aoa_azimuth'] - (-10.7578125)) < 1e-9


def test_empty_block():
    assert parse_ranging_block('') == []


def test_non_ranging_block():
    assert parse_ranging_block('Initializing session 42...\n') == []


def test_failed_status_zeros_distance():
    block = BLOCK_SEQ18.replace('Ok (0x0)', 'Failed (0x2)')
    results = parse_ranging_block(block)
    assert len(results) == 1
    assert results[0]['status'] == 255
    assert results[0]['distance_m'] == 0.0


if __name__ == '__main__':
    test_parse_block_seq18()
    test_parse_block_seq19_negative_aoa()
    test_empty_block()
    test_non_ranging_block()
    test_failed_status_zeros_distance()
    print('all tests passed')
