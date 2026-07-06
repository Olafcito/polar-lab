"""Hermetic: BLE Heart Rate Measurement packet parsing (the only pure logic)."""

from polar_lab.h10_recorder import parse_hr


def test_uint8_hr_no_rr():
    bpm, rrs = parse_hr(bytearray([0x00, 72]))
    assert bpm == 72 and rrs == []


def test_uint8_hr_with_rr():
    # flags 0x10 = RR present; RR raw 1024 -> exactly 1000 ms
    bpm, rrs = parse_hr(bytearray([0x10, 65, 0x00, 0x04, 0x00, 0x02]))
    assert bpm == 65
    assert rrs[0] == 1000.0
    assert abs(rrs[1] - 500.0) < 0.01


def test_uint16_hr_energy_and_rr():
    # flags: bit0 (16-bit HR) + bit3 (energy) + bit4 (RR)
    data = bytearray([0x19, 180, 0x00, 0x34, 0x12, 0x00, 0x04])
    bpm, rrs = parse_hr(data)
    assert bpm == 180
    assert rrs == [1000.0]
