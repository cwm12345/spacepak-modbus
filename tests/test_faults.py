# Written by Claude, guided by Chris.
"""Decoding the failure registers."""

from __future__ import annotations

from modbus_connection.mock import MockModbusUnit

from spacepak_modbus import FAILURE_ADDRESSES, FAULTS, Faults, IlahpHeatPump


def test_fault_keys_are_unique() -> None:
    keys = [fault.key for fault in FAULTS]
    assert len(keys) == len(set(keys))


def test_every_fault_names_a_real_bit() -> None:
    for fault in FAULTS:
        assert fault.register in FAILURE_ADDRESSES
        assert 0 <= fault.bit < 16


def test_failure_fields_sit_at_their_addresses() -> None:
    for register, address in FAILURE_ADDRESSES.items():
        assert Faults.declared_fields[f"failure_{register}"].address == address


async def test_no_faults(heat_pump: IlahpHeatPump) -> None:
    await heat_pump.async_update_readings()
    assert heat_pump.faults.any_fault is False
    assert heat_pump.faults.active_faults == ()


async def test_named_and_unnamed_bits(
    unit: MockModbusUnit, heat_pump: IlahpHeatPump
) -> None:
    unit.holding[2085] = 1 << 4  # failure 1: high pressure
    unit.holding[2087] = 1 << 0  # failure 3: no published bit table
    unit.holding[2081] = 1 << 2  # failure 7: compressor overcurrent
    await heat_pump.async_update_readings()

    assert heat_pump.faults.any_fault is True
    assert [fault.key for fault in heat_pump.faults.active_faults] == [
        "high_pressure",
        "failure_3_bit_0",
        "compressor_overcurrent",
    ]


async def test_a_reserved_bit_is_still_reported(
    unit: MockModbusUnit, heat_pump: IlahpHeatPump
) -> None:
    unit.holding[2085] = 1 << 0  # failure 1 bit 0 is reserved
    await heat_pump.async_update_readings()
    (fault,) = heat_pump.faults.active_faults
    assert fault.key == "failure_1_bit_0"
    assert fault.description == "Undocumented fault bit"
