"""Atomic JSON file writes: never leave a truncated file on disk.

A crash mid-write must not replace a valid dataset with a partial one —
write to a temp file in the same directory, then os.replace() (atomic on
POSIX and Windows for same-filesystem paths).
"""

import json
import os


def write_json(path: str, obj, **dump_kwargs) -> None:
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, **dump_kwargs)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
