"""Add DNS/UDP denial to the unchanged prepared synthetic unit gate.

Use as the actual launcher so DNS lookups stop before a TCP connect is attempted.
The imported prepared runner already guards Engine, raw connection, Pool,
SQLite paths, dotenv reads, environment settings and Main bytecode/cache writes.
"""

from pathlib import Path
import runpy
import socket
import sys


sys.dont_write_bytecode = True


def no_network(*_, **__):
    raise AssertionError("DNS and UDP are prohibited in this synthetic unit gate")


socket.getaddrinfo = no_network
socket.socket.sendto = no_network

if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().with_name("run_worker_prewarm_unit_gate_PREPARED01.py")),
        run_name="__main__",
    )
