"""Tamper-Evident Merkle-Sealed Flight Log (B9.1, INN-07, D17).

Provides:
1. Hash-chained continuous record: H_i = SHA256(H_{i-1} || Record_i).
2. Merkle tree batch sealing for forensic non-repudiation.
3. Cryptographic tamper detection: detects any altered, omitted, or reordered flight record.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FlightLogEntry:
    index: int
    t_sec: float
    payload: Dict[str, Any]
    prev_hash: str
    entry_hash: str


class MerkleFlightLog:
    """Tamper-evident flight recorder with hash chaining and Merkle root sealing."""

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self) -> None:
        self.entries: List[FlightLogEntry] = []
        self.current_prev_hash = self.GENESIS_HASH

    def append(self, t_sec: float, payload: Dict[str, Any]) -> FlightLogEntry:
        """Append record to hash chain."""
        idx = len(self.entries)
        payload_str = json.dumps(payload, sort_keys=True)
        content = f"{idx}:{t_sec}:{self.current_prev_hash}:{payload_str}"
        entry_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        entry = FlightLogEntry(
            index=idx,
            t_sec=t_sec,
            payload=payload,
            prev_hash=self.current_prev_hash,
            entry_hash=entry_hash,
        )
        self.entries.append(entry)
        self.current_prev_hash = entry_hash
        return entry

    def compute_merkle_root(self, start_idx: int = 0, end_idx: Optional[int] = None) -> str:
        """Compute Merkle root hash over a range of log entries."""
        subset = self.entries[start_idx : (end_idx or len(self.entries))]
        if not subset:
            return self.GENESIS_HASH

        hashes = [e.entry_hash for e in subset]
        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])
            new_level = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                h = hashlib.sha256(combined.encode("utf-8")).hexdigest()
                new_level.append(h)
            hashes = new_level
        return hashes[0]

    def verify_integrity(self) -> Tuple[bool, Optional[int]]:
        """Verify the continuous hash chain. Returns (is_valid, first_corrupted_index)."""
        prev = self.GENESIS_HASH
        for i, e in enumerate(self.entries):
            if e.prev_hash != prev:
                return False, i

            payload_str = json.dumps(e.payload, sort_keys=True)
            content = f"{e.index}:{e.t_sec}:{e.prev_hash}:{payload_str}"
            expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if e.entry_hash != expected_hash:
                return False, i

            prev = e.entry_hash
        return True, None
