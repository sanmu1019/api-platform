"""带容量上限的简单 TTL + LRU 内存缓存（无外部依赖，线程安全）。"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any

_MISSING = object()


class TTLCache:
    def __init__(self, maxsize: int, ttl: float) -> None:
        self.maxsize = maxsize
        self.ttl = ttl
        self._data: OrderedDict[Any, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Any, default: Any = None, *, allow_stale: bool = False) -> Any:
        """取未过期的值；allow_stale=True 时过期但尚未被淘汰的旧值也返回（上游失败兜底用）。"""
        with self._lock:
            item = self._data.get(key, _MISSING)
            if item is _MISSING:
                return default
            expire, value = item
            if not allow_stale and time.time() >= expire:
                return default
            self._data.move_to_end(key)
            return value

    def set(self, key: Any, value: Any) -> None:
        now = time.time()
        with self._lock:
            self._data[key] = (now + self.ttl, value)
            self._data.move_to_end(key)
            if len(self._data) > self.maxsize:
                for k in [k for k, (exp, _) in self._data.items() if exp <= now]:
                    del self._data[k]
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __contains__(self, key: Any) -> bool:
        return key in self._data

    def __len__(self) -> int:
        return len(self._data)
