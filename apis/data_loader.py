from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / "data"


@lru_cache
def load_lines(name: str) -> tuple[str, ...]:
    path = DATA_DIR / name
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return tuple(row for row in rows if row)


@lru_cache
def load_json(name: str) -> Any:
    path = DATA_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))
