# Written by Claude, guided by Chris.
"""The ILAHP register map, decoded over the mock backend."""

from __future__ import annotations

import pytest
from modbus_connection import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusUnit

from spacepak_modbus import (
    READINGS,
    SETTINGS,
    IlahpHeatPump,
    OperatingMode,
    Outputs,
    UnitMode,
)


def test_nothing_before_the_first_read(heat_pump: IlahpHeatPump) -> None:
    assert heat_pump.measurements.outlet_temperature is None
    assert heat_pump.status.compressor_on is None
    assert heat_pump.faults.any_fault is None
    assert heat_pump.faults.active_faults == ()


async def test_update_decodes_every_component(heat_pump: IlahpHeatPump) -> None:
    report = await heat_pump.async_update()

    assert report.updated == {*READINGS, *SETTINGS}
    assert report.complete

    controls = heat_pump.controls
    assert controls.power_on is True
    assert controls.operating_mode is OperatingMode.HEATING
    assert controls.heating_target_temperature == 45.0
    assert controls.cooling_target_temperature == 7.0
    assert (controls.min_heating_setpoint, controls.max_heating_setpoint) == (
        15.0,
        50.0,
    )
    assert (controls.min_cooling_setpoint, controls.max_cooling_setpoint) == (
        8.0,
        28.0,
    )

    status = heat_pump.status
    assert status.running is True
    assert status.unit_mode is UnitMode.HEATING
    assert status.outputs == Outputs.COMPRESSOR | Outputs.WATER_PUMP
    assert status.compressor_on is True
    assert status.alarm_on is False
    assert status.compressor_hours == 40000

    m = heat_pump.measurements
    assert m.compressor_current == 10.5
    assert m.dc_bus_voltage == 380
    assert m.inlet_temperature == 38.0
    assert m.outlet_temperature == 43.2
    assert m.discharge_temperature == 71.5
    assert m.ac_input_current == 14.2
    assert m.room_temperature == 21.0
    assert m.ac_input_voltage == 238
    assert m.compressor_frequency_target == 62
    assert m.compressor_frequency == 60
    assert m.water_flow == 3.25


async def test_temperatures_below_zero_are_signed(heat_pump: IlahpHeatPump) -> None:
    await heat_pump.async_update_readings()
    assert heat_pump.measurements.ambient_temperature == -10.0
    assert heat_pump.measurements.coil_temperature == -8.0
    assert heat_pump.measurements.suction_temperature == -3.0


async def test_currents_and_counters_are_unsigned(
    unit: MockModbusUnit, heat_pump: IlahpHeatPump
) -> None:
    unit.holding[2042] = 40000
    await heat_pump.async_update_readings()
    assert heat_pump.measurements.compressor_current == 4000.0
    assert heat_pump.status.compressor_hours == 40000


async def test_defrost_and_alarm(
    unit: MockModbusUnit, heat_pump: IlahpHeatPump
) -> None:
    unit.holding[2012] = 2
    unit.holding[2019] = 0x0402 | 0x0001  # compressor, reserved bit 1, alarm
    await heat_pump.async_update_readings()
    assert heat_pump.status.unit_mode is UnitMode.DEFROST
    outputs = heat_pump.status.outputs
    assert outputs is not None
    assert Outputs.ALARM in outputs
    assert outputs & 0x0002  # a reserved bit is kept, not dropped
    assert heat_pump.status.alarm_on is True


async def test_readings_and_settings_poll_apart(heat_pump: IlahpHeatPump) -> None:
    report = await heat_pump.async_update_readings()
    assert report.updated == set(READINGS)
    assert heat_pump.controls.power_on is None

    report = await heat_pump.async_update_settings()
    assert report.updated == set(SETTINGS)
    assert heat_pump.controls.power_on is True


async def test_a_full_poll_costs_five_reads(
    unit: MockModbusUnit, heat_pump: IlahpHeatPump
) -> None:
    await heat_pump.async_update()
    blocks = [(event.address, event.count) for event in unit.read_events]
    assert sorted(blocks) == [
        (1011, 2),
        (1158, 8),
        (2011, 22),
        (2042, 36),
        (2081, 10),
    ]
    assert all(event.register_type == "holding" for event in unit.read_events)


async def test_a_refused_block_keeps_the_rest(
    unit: MockModbusUnit, heat_pump: IlahpHeatPump
) -> None:
    unit.fail_read(2081, IllegalDataAddressError())
    report = await heat_pump.async_update_readings()
    assert report.updated == {"status", "measurements"}
    assert isinstance(report.failed["faults"], IllegalDataAddressError)
    assert heat_pump.measurements.outlet_temperature == 43.2


async def test_a_silent_unit_raises(
    unit: MockModbusUnit, heat_pump: IlahpHeatPump
) -> None:
    unit.fail_requests(ModbusTimeoutError())
    with pytest.raises(ModbusTimeoutError):
        await heat_pump.async_update()


async def test_a_dead_link_raises(
    unit: MockModbusUnit, heat_pump: IlahpHeatPump
) -> None:
    unit.fail_requests(ModbusConnectionError())
    with pytest.raises(ModbusConnectionError):
        await heat_pump.async_update_readings()


async def test_power_write(unit: MockModbusUnit, heat_pump: IlahpHeatPump) -> None:
    await heat_pump.controls.write("power_on", False)
    assert unit.holding[1011] == 0


async def test_setpoint_write_scales(
    unit: MockModbusUnit, heat_pump: IlahpHeatPump
) -> None:
    await heat_pump.controls.write("heating_target_temperature", 47.5)
    assert unit.holding[1158] == 475
    await heat_pump.controls.write("cooling_target_temperature", 12.0)
    assert unit.holding[1159] == 120


async def test_setpoint_out_of_range_writes_nothing(
    unit: MockModbusUnit, heat_pump: IlahpHeatPump
) -> None:
    with pytest.raises(ValueError):
        await heat_pump.controls.write("heating_target_temperature", 120.0)
    assert unit.holding[1158] == 450


async def test_operating_mode_is_read_only(heat_pump: IlahpHeatPump) -> None:
    with pytest.raises(AttributeError):
        await heat_pump.controls.write("operating_mode", OperatingMode.COOLING)


async def test_raw_dump_covers_every_component(heat_pump: IlahpHeatPump) -> None:
    raw = await heat_pump.async_read_raw()
    holding = raw["holding"]
    assert holding[1011] == 1
    assert holding[2048] == 0xFF9C
    assert holding[2090] == 0
    assert list(holding) == sorted(holding)


async def test_raw_snapshot_replays(mock_modbus_unit: MockModbusUnit) -> None:
    mock_modbus_unit.load_raw({"holding": dict.fromkeys(range(2042, 2078), 0)})
    mock_modbus_unit.load_raw({"holding": {2046: 500, 2048: 0xFFEC}})
    heat_pump = IlahpHeatPump(mock_modbus_unit)
    await heat_pump.measurements.async_update()
    assert heat_pump.measurements.outlet_temperature == 50.0
    assert heat_pump.measurements.ambient_temperature == -2.0
