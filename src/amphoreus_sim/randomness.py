"""Independent, reproducible random streams.

Changing flavour text must never change world outcomes, so each system receives
its own seed derived from the root seed and an explicit stream name.
"""

from __future__ import annotations

import hashlib
import random


class RandomStreams:
    def __init__(self, root_seed: int) -> None:
        self._root_seed = root_seed
        self._streams: dict[str, random.Random] = {}

    def get(self, name: str) -> random.Random:
        if name not in self._streams:
            source = f"{self._root_seed}:{name}".encode("utf-8")
            seed = int.from_bytes(hashlib.sha256(source).digest()[:8], "big")
            self._streams[name] = random.Random(seed)
        return self._streams[name]

