#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import math
import os
import random
import struct
from typing import Iterable, Iterator, Optional, Tuple, Union


def _to_bytes(data: Union[str, bytes]) -> bytes:
	"""Helper to normalize inputs to bytes."""
	if isinstance(data, bytes):
		return data
	return data.encode("utf-8")


class BloomFilter:
	"""A simple Bloom filter backed by a bytearray and double hashing.
	
	- num_bits (m): number of bits in the filter
	- num_hashes (k): number of hash functions (via double hashing)
	"""

	MAGIC = b"BLMF"  # for basic serialization
	VERSION = 1

	def __init__(self, num_bits: int, num_hashes: int) -> None:
		if num_bits <= 0:
			raise ValueError("num_bits must be positive")
		if num_hashes <= 0:
			raise ValueError("num_hashes must be positive")
		self.num_bits = int(num_bits)
		self.num_hashes = int(num_hashes)
		num_bytes = (self.num_bits + 7) // 8
		self._bits = bytearray(num_bytes)
		self._count = 0  # number of insertions (approximate unique count is not tracked)

	# --------- Bit operations ----------
	def _set_bit(self, bit_index: int) -> None:
		byte_index = bit_index >> 3
		offset = bit_index & 7
		self._bits[byte_index] |= (1 << offset)

	def _get_bit(self, bit_index: int) -> bool:
		byte_index = bit_index >> 3
		offset = bit_index & 7
		return (self._bits[byte_index] >> offset) & 1 == 1

	# --------- Hashing ----------
	def _hashes(self, data: Union[str, bytes]) -> Iterator[int]:
		"""Generate k indices in [0, m) using Kirsch-Mitzenmacher double hashing."""
		payload = _to_bytes(data)
		# Use SHA-256 to derive two 64-bit hashes deterministically.
		digest = hashlib.sha256(payload).digest()
		# 32 bytes -> two 8-byte chunks for h1, h2, remaining not needed
		h1 = struct.unpack_from("<Q", digest, 0)[0]
		h2 = struct.unpack_from("<Q", digest, 8)[0]
		# Ensure h2 is odd to improve distribution when stepping
		if h2 % 2 == 0:
			h2 += 1
		m = self.num_bits
		for i in range(self.num_hashes):
			yield (h1 + i * h2) % m

	# --------- Public API ----------
	def add(self, data: Union[str, bytes]) -> None:
		for idx in self._hashes(data):
			self._set_bit(idx)
		self._count += 1

	def __contains__(self, data: Union[str, bytes]) -> bool:  # `x in bloom`
		for idx in self._hashes(data):
			if not self._get_bit(idx):
				return False
		return True

	def insert_many(self, items: Iterable[Union[str, bytes]]) -> None:
		for it in items:
			self.add(it)

	def estimated_false_positive_rate(self, n_inserted: Optional[int] = None) -> float:
		"""Return the theoretical false positive probability p ≈ (1 - e^{-k n / m})^k.
		
		If n_inserted is None, uses the number of insertions tracked so far.
		"""
		n = self._count if n_inserted is None else int(n_inserted)
		m = float(self.num_bits)
		k = float(self.num_hashes)
		if n <= 0:
			return 0.0
		return (1.0 - math.exp(-k * n / m)) ** k

	def bit_density(self) -> float:
		"""Return fraction of bits set to 1."""
		ones = 0
		for b in self._bits:
			ones += bin(b).count("1")
		return ones / float(self.num_bits)

	@property
	def count_inserted(self) -> int:
		return self._count

	def to_bytes(self) -> bytes:
		"""Serialize the Bloom filter to bytes (portable)."""
		header = self.MAGIC + struct.pack("<BQQ", self.VERSION, self.num_bits, self.num_hashes)
		body = bytes(self._bits)
		return header + body

	@classmethod
	def from_bytes(cls, payload: bytes) -> "BloomFilter":
		if not payload.startswith(cls.MAGIC):
			raise ValueError("Invalid BloomFilter bytes: bad magic")
		_, version, m, k = struct.unpack_from("<4sBQQ", payload, 0)
		if version != cls.VERSION:
			raise ValueError(f"Unsupported BloomFilter version: {version}")
		instance = cls(num_bits=m, num_hashes=k)
		header_len = 4 + 1 + 8 + 8
		expected_len = header_len + len(instance._bits)
		if len(payload) != expected_len:
			raise ValueError("Invalid BloomFilter bytes: length mismatch")
		instance._bits[:] = payload[header_len:]
		return instance

	# --------- Sizing helpers ----------
	@staticmethod
	def optimal_num_hashes(num_bits: int, expected_items: int) -> int:
		"""k* = round((m/n) ln 2)."""
		if expected_items <= 0:
			return 1
		k = (num_bits / float(expected_items)) * math.log(2.0)
		return max(1, int(round(k)))

	@staticmethod
	def size_for(expected_items: int, target_false_positive: float) -> int:
		"""m = ceil(-(n ln p) / (ln 2)^2)."""
		if expected_items <= 0:
			raise ValueError("expected_items must be positive")
		if not (0.0 < target_false_positive < 1.0):
			raise ValueError("target_false_positive must be in (0,1)")
		m = -expected_items * math.log(target_false_positive) / (math.log(2.0) ** 2)
		return int(math.ceil(m))


# ---------------- CLI / Demo ----------------
def _demo() -> None:
	print("Bloom Filter demo")
	n = 1000
	target_p = 0.01
	m = BloomFilter.size_for(n, target_p)
	k = BloomFilter.optimal_num_hashes(m, n)
	print(f"Configured for n={n}, target_p={target_p} -> m={m}, k={k}")
	bf = BloomFilter(m, k)

	random.seed(42)
	values = [f"item-{i}-{random.randrange(1_000_000)}" for i in range(n)]
	bf.insert_many(values)
	print(f"Inserted {n} items.")
	print(f"Estimated p={bf.estimated_false_positive_rate():.4f}, bit density={bf.bit_density():.3f}")

	negatives = 5000
	false_pos = 0
	for i in range(negatives):
		probe = f"probe-{i}-{random.randrange(1_000_000)}"
		if probe in bf and probe not in values:
			false_pos += 1
	empirical_p = false_pos / float(negatives)
	print(f"Empirical false positive rate over {negatives} probes: {empirical_p:.4f}")


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Bloom Filter utility")
	parser.add_argument("--demo", action="store_true", help="Run a quick demo")
	parser.add_argument("--serialize", metavar="PATH", help="Write a serialized filter to PATH")
	parser.add_argument("--deserialize", metavar="PATH", help="Read a serialized filter from PATH and print summary")
	return parser.parse_args()


def main() -> None:
	args = _parse_args()
	if args.demo:
		_demo()
		return
	if args.serialize:
		# Write a small prebuilt filter
		n = 200
		target_p = 0.02
		m = BloomFilter.size_for(n, target_p)
		k = BloomFilter.optimal_num_hashes(m, n)
		bf = BloomFilter(m, k)
		for i in range(n):
			bf.add(f"value-{i}")
		with open(args.serialize, "wb") as f:
			f.write(bf.to_bytes())
		print(f"Wrote Bloom filter to {args.serialize} (m={m}, k={k})")
		return
	if args.deserialize:
		with open(args.deserialize, "rb") as f:
			data = f.read()
		bf = BloomFilter.from_bytes(data)
		print(f"Loaded Bloom filter (m={bf.num_bits}, k={bf.num_hashes})")
		print(f"Bit density: {bf.bit_density():.3f}")
		return
	# Default: help
	print("No action specified. Use --demo, --serialize PATH, or --deserialize PATH.")


if __name__ == "__main__":
	main()


