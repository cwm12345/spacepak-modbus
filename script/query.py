#!/usr/bin/env python3
# Written by Claude, guided by Chris.

"""Query a SpacePak ILAHP heat pump and print every value."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from modbus_connection import ModbusError
from modbus_connection.cli_helper import (
    CountingUnit,
    add_connection_args,
    connect_from_args,
    print_component,
)

from spacepak_modbus import READINGS, SETTINGS, IlahpHeatPump

# A gateway answering Modbus TCP, or the unit's RS-485 line directly or
# through a serial server (socket://host:port).
CONNECTIONS = (("tcp", None), ("serial", "rtu"))

EXAMPLES = """examples:
  uv run script/query.py 192.168.1.50 --port 502 --unit 1
  uv run script/query.py socket://192.168.1.50:8899 --transport serial --unit 1
  uv run script/query.py /dev/ttyUSB0 --transport serial --baudrate 9600 --unit 1 --raw
"""


async def main() -> int:
    """Read one heat pump and print it."""
    # The backend logs a failed connect at ERROR with its traceback; the
    # messages below say it in one line.
    logging.getLogger().addHandler(logging.NullHandler())

    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_connection_args(parser, connections=CONNECTIONS)
    parser.add_argument("--unit", type=int, default=1, help="Modbus unit id")
    parser.add_argument(
        "--raw", action="store_true", help="also dump every register read, as JSON"
    )
    args = parser.parse_args()

    try:
        connection = await connect_from_args(args)
    except ModbusError as err:
        print(f"Could not connect to {args.target}: {str(err) or type(err).__name__}")
        return 1

    counting = CountingUnit(connection.for_unit(args.unit))
    heat_pump = IlahpHeatPump(counting)
    try:
        report = await heat_pump.async_update()
        reads = counting.reads
        raw = await heat_pump.async_read_raw() if args.raw else None
    except ModbusError as err:
        print(f"Could not read the heat pump: {str(err) or type(err).__name__}")
        return 1
    finally:
        await connection.close()

    for name in (*SETTINGS, *READINGS):
        print()
        print_component(getattr(heat_pump, name), title=name)
    faults = heat_pump.faults.active_faults
    print("\nActive faults")
    for fault in faults:
        print(f"  {fault.key}  (failure {fault.register} bit {fault.bit})")
    if not faults:
        print("  none")
    if report.failed:
        print("\nFailed to read:")
        for name, error in report.failed.items():
            print(f"  {name}: {str(error) or type(error).__name__}")
    if raw is not None:
        print("\nRaw registers")
        print(json.dumps(raw, indent=2))
    print(f"\n{reads} Modbus reads")
    return 0


raise SystemExit(asyncio.run(main()))
