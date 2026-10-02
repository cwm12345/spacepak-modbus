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
    1018: 1,  # H01 auto restart
    1021: 1,  # H05 cooling enabled
    1023: 1,  # H07 field-wired control
    1024: 1,  # H10 unit address
    1028: 0,  # H28 hot water function off
    1029: 1,  # H21 display in F
    1030: 0,  # H22 silence mode off
    1158: 450,  # heating target 45.0 C
    1159: 70,  # cooling target 7.0 C
    1162: 80,  # min cooling setpoint 8.0 C
    1163: 280,  # max cooling setpoint 28.0 C
    1164: 150,  # min heating setpoint 15.0 C
    1165: 500,  # max heating setpoint 50.0 C
    # -- tuning --
    1037: 0xFED4,  # A03 shutdown ambient -30.0 C
    1038: 22,  # A04 antifreeze 2.2 C
    1039: 28,  # A05 antifreeze difference 2.8 K
    1053: 11,  # A22 antifreeze minimum 1.1 C
    1166: 20,  # R15 outlet overheat difference 2.0 K
    1193: 11,  # R40 pump freeze protection ambient 1.1 C
    1228: 545,  # R42 max water 54.5 C
    1229: 433,  # R43 max water at low ambient 43.3 C
    1230: 433,  # R44 max water at high ambient 43.3 C
    1160: 20,  # R04 heating restart difference 2.0 K
    1161: 20,  # R05 heating stop difference 2.0 K
    1167: 0xFF4E,  # R29 low-ambient compensation start -17.8 C
    1168: 0xFF17,  # R30 low-ambient compensation end -23.3 C
    1169: 406,  # R31 low-ambient heating target 40.6 C
    1174: 20,  # R06 cooling restart difference 2.0 K
    1175: 20,  # R07 cooling stop difference 2.0 K
    1192: 100,  # R39 heating restart ambient 10.0 C
    1197: 1,  # P01 pump mode economic
    1198: 30,  # P02 interval 30 min
    1199: 3,  # P03 run time 3 min
    1219: 30,  # C02 compressor min 30 Hz
    1220: 90,  # C03 compressor max 90 Hz
    1234: 10,  # weather compensation slope 1.0
    1235: 200,  # weather compensation offset 20.0 C
    1236: 0,  # weather compensation off
    # -- status --
    2011: 1,  # running
    2012: 1,  # heating
    2013: 450,  # target after limits 45.0 C
    2014: 450,  # target after weather compensation 45.0 C
    2019: 0x0011,  # compressor + water pump
    2032: 40000,  # compressor hours, above the int16 range
    2034: 0x0000,  # every field input closed: enabled, heating, flow made
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
