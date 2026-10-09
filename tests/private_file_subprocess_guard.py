"""No-effects audit boundary for the authored CLI subprocess test."""

import os
import sys


def _guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo"}:
        raise PermissionError("Offline configuration validation cannot use network")
    if event == "open":
        path, mode, flags = args
        if isinstance(path, (str, bytes, os.PathLike)):
            spelling = os.fsdecode(path).replace("/", "\\").lower()
            if spelling.endswith("\\.env") or "\\.secrets\\" in spelling:
                raise PermissionError("Offline configuration validation cannot read private stores")
            writing = (isinstance(mode, str) and any(letter in mode for letter in "wax+")) or bool(
                flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            )
            if writing:
                raise PermissionError("Offline configuration validation cannot write files")


sys.addaudithook(_guard)
