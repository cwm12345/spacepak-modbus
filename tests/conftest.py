# Written by Claude, guided by Chris.
"""Fixtures: an ILAHP heat pump on modbus-connection's in-memory mock backend."""

from __future__ import annotations

import pytest
from modbus_connection.mock import MockModbusUnit

from spacepak_modbus import IlahpHeatPump

# A unit heating on a cold day, compressor and water pump running.
HOLDING: dict[int, int] = {
    # -- controls --
    1011: 1,  # on
    1012: 1,  # operating mode: heating
    1028: 0,  # H28 hot water function off
    1158: 450,  # heating target 45.0 C
    1159: 70,  # cooling target 7.0 C
    1162: 80,  # min cooling setpoint 8.0 C
    1163: 280,  # max cooling setpoint 28.0 C
    1164: 150,  # min heating setpoint 15.0 C
    1165: 500,  # max heating setpoint 50.0 C
    # -- status --
    2011: 1,  # running
    2012: 1,  # heating
    2019: 0x0011,  # compressor + water pump
    2032: 40000,  # compressor hours, above the int16 range
    # -- measurements --
    2042: 105,  # compressor current 10.5 A
    2043: 380,  # DC bus 380 V
    2045: 380,  # inlet 38.0 C
    2046: 432,  # outlet 43.2 C
    2047: 0,  # no tank sensor
    2048: 0xFF9C,  # ambient -10.0 C
    2049: 0xFFB0,  # coil -8.0 C
    2051: 0xFFE2,  # suction -3.0 C
    2053: 715,  # discharge 71.5 C
    2057: 142,  # AC input 14.2 A
    2062: 238,  # AC input 238 V
    2071: 62,  # compressor target 62 Hz
    2072: 60,  # compressor running 60 Hz
    # -- faults: none --
    **dict.fromkeys(range(2081, 2091), 0),
}


@pytest.fixture
def unit(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    """The mock unit seeded with a heating heat pump."""
    for address, value in HOLDING.items():
        mock_modbus_unit.holding[address] = value
    return mock_modbus_unit


@pytest.fixture
def heat_pump(unit: MockModbusUnit) -> IlahpHeatPump:
    """A heat pump reading the seeded unit."""
    return IlahpHeatPump(unit)
