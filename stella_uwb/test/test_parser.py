"""Tests for UWB serial parser."""
import pytest
from stella_uwb.parser import parse_ntf_line


class TestParseNtfLine:
    def test_success_message(self):
        line = '[mac_address=0x0001, status="SUCCESS", distance[cm]=9]}'
        result = parse_ntf_line(line)
        assert result is not None
        assert result['anchor_id'] == '0x0001'
        assert result['distance_m'] == pytest.approx(0.09)
        assert result['status'] == 0  # LOS

    def test_full_ntf_message(self):
        line = (
            'SESSION_INFO_NTF: {session_handle=1, sequence_number=126651, '
            'block_index=126651, n_measurements=1\n'
            ' [mac_address=0x0001, status="SUCCESS", distance[cm]=150]}'
        )
        result = parse_ntf_line(line)
        assert result is not None
        assert result['anchor_id'] == '0x0001'
        assert result['distance_m'] == pytest.approx(1.5)
        assert result['status'] == 0

    def test_different_anchor_id(self):
        line = '[mac_address=0x00AB, status="SUCCESS", distance[cm]=300]}'
        result = parse_ntf_line(line)
        assert result is not None
        assert result['anchor_id'] == '0x00AB'
        assert result['distance_m'] == pytest.approx(3.0)

    def test_failure_status(self):
        line = '[mac_address=0x0001, status="FAIL", distance[cm]=0]}'
        result = parse_ntf_line(line)
        assert result is not None
        assert result['distance_m'] == 0.0
        assert result['status'] == 255  # UNKNOWN

    def test_no_match_returns_none(self):
        assert parse_ntf_line('') is None
        assert parse_ntf_line('random garbage') is None
        assert parse_ntf_line('STOP') is None

    def test_default_fields(self):
        line = '[mac_address=0x0001, status="SUCCESS", distance[cm]=100]}'
        result = parse_ntf_line(line)
        assert result['rssi'] == 0.0
        assert result['pdr'] == 0.0
        assert result['cir'] == []

    def test_zero_distance_success(self):
        line = '[mac_address=0x0001, status="SUCCESS", distance[cm]=0]}'
        result = parse_ntf_line(line)
        assert result['distance_m'] == 0.0
        assert result['status'] == 0

    def test_large_distance(self):
        line = '[mac_address=0x0001, status="SUCCESS", distance[cm]=5000]}'
        result = parse_ntf_line(line)
        assert result['distance_m'] == pytest.approx(50.0)
