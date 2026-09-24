<!-- Written by Claude, guided by Chris. -->

# spacepak-modbus

Read and control SpacePak Solstice Inverter Extreme (ILAHP) air-to-water heat
pumps over Modbus, as typed Python objects rather than register numbers.

The library maps the ILAHP register set onto
[modbus-connection](https://github.com/home-assistant-libs/modbus-connection)'s
device model: you hand it a `ModbusUnit`, call `async_update()`, and read
sub-systems as attributes. It owns no connection and no I/O policy. The caller
does.

## Status

This is a working reference pulled from one real installation, shared in case
it is useful. It is **not an actively maintained package**: there is no
commitment to triage issues or pull requests, or to track future
modbus-connection changes. Forks are welcome, and so is anyone who wants to take
it over.

## Supported devices

The SpacePak Solstice Inverter Extreme (ILAHP) range, per the register map in
its installation manual (ILHP2-0423). It has been exercised against two units
behind a Modbus TCP gateway. Other SpacePak models are untested.

The unit speaks Modbus RTU at 9600 baud, 8N1, on its RS-485 port. Every
register this library reads is a holding register.

## What it covers

| Component | Registers | What |
| :--- | :--- | :--- |
| `controls` | 1011-1012, 1158-1165 | Power, operating mode, heating and cooling targets, the unit's own setpoint limits |
| `status` | 2011-2032 | Running, current mode (defrost included), load outputs, compressor hours |
| `measurements` | 2042-2077 | Water, air, coil and refrigerant temperatures, currents, voltages, compressor frequency, water flow |
| `faults` | 2081-2090 | The nine failure registers, decoded into named faults |

The installer parameters (registers 1013-1270: compressor frequency curves, EEV
steps, defrost timing, weather compensation, timers) are deliberately left out.
Writing those by mistake would misconfigure the heat pump, not just misreport
it.

Every temperature is stored in tenths of a degree Celsius, whatever the unit's
display is set to show, so every temperature here is in °C.

## Usage

```python
import asyncio

from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection
from spacepak_modbus import IlahpHeatPump


async def main() -> None:
    connection = ModbusConnection(ModbusTcpParams(host="192.168.1.50", port=502))
    try:
        heat_pump = IlahpHeatPump(connection.for_unit(1))
        await heat_pump.async_update()

        print("Running:", heat_pump.status.running, heat_pump.status.unit_mode)
        print("Outlet:", heat_pump.measurements.outlet_temperature, "°C")
        print("Outdoor:", heat_pump.measurements.ambient_temperature, "°C")
        print("Target:", heat_pump.controls.heating_target_temperature, "°C")
        print("Faults:", [fault.key for fault in heat_pump.faults.active_faults])
    finally:
        await connection.close()


asyncio.run(main())
```

### Readings and settings refresh separately

- `async_update_readings()` reads `status`, `measurements` and `faults`: what the
  unit measures and reports.
- `async_update_settings()` reads `controls`: registers that change when
  something writes them. Run one after a write to read back what took effect.
- `async_update()` does both, in one report.

Each returns an `UpdateReport`. A component whose block the unit refuses keeps
its previous values and is listed in `report.failed`; the rest still refresh. A
dead link (`ModbusConnectionError`) raises, and so does a timeout before
anything has answered.

### Writing

```python
await heat_pump.controls.write("power_on", True)
await heat_pump.controls.write("heating_target_temperature", 45.0)
await heat_pump.async_update_settings()
```

Setpoint writes are checked against the widest range each register accepts.
The unit applies its own tighter limits too, which it reports as
`min_heating_setpoint`/`max_heating_setpoint` and
`min_cooling_setpoint`/`max_cooling_setpoint`. Clamp to those before writing.

The operating mode is read-only here. The mode register's values depend on
whether the installer enabled cooling (parameter H05), and a wrong mode can
leave a hydronic system without heat.

### Faults

The unit reports faults as nine bitmask registers. `faults.active_faults`
decodes them into `Fault` entries, each with its failure register, bit, a
stable snake_case `key`, and a description. `FAULTS` is the full table of the
bits the manual names. A set bit the manual does not name (failure register 3
has no published bit table) is still reported, as `failure_<n>_bit_<b>`, so
nothing is hidden. `faults.any_fault` is true when any register has a bit set.

## Checking a real heat pump

`script/query.py` reads one unit once and prints every value, which is the
quickest way to see whether a unit is reachable and addressed correctly:

```bash
uv run script/query.py 192.168.1.50 --port 502 --unit 1
uv run script/query.py socket://192.168.1.50:8899 --transport serial --unit 1
uv run script/query.py /dev/ttyUSB0 --transport serial --baudrate 9600 --unit 1 --raw
```

`--raw` adds every register it read, undecoded, which is what an issue about a
wrong value should quote. A raw dump loads straight into modbus-connection's
mock with `load_raw()`, so it can become a test.

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

The tests run against modbus-connection's in-memory mock backend. No hardware
is needed.

## Source

The register map comes from the SpacePak ILAHP Installation, Operation &
Maintenance manual (ILHP2-0423), Modbus section. Addresses, scales and the
enum and bit tables follow it. On live units:

- 1011, 1158 and 1159 have been read and written.
- Every register this library reads has been read from two units and checked
  against the values an existing integration reported for the same units.
- The operating mode (1012) and the setpoint limits (1162-1165) read as
  expected. The limits are whatever the installer configured, so they differ
  from the manual's defaults.

## License

[Unlicense](LICENSE): public domain.
