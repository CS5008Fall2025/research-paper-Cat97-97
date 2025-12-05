#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import random
import time
from typing import List, Tuple

from src.bloom_filter import BloomFilter


def run_trial(n: int, target_p: float, probes: int, rng: random.Random) -> Tuple[int, int, int, float, float, float]:
	m = BloomFilter.size_for(n, target_p)
	k = BloomFilter.optimal_num_hashes(m, n)
	bf = BloomFilter(m, k)

	# Insert n random strings
	values = [f"val-{i}-{rng.randrange(1_000_000_000)}" for i in range(n)]
	t0 = time.perf_counter()
	bf.insert_many(values)
	t_insert = time.perf_counter() - t0

	# Probe negatives
	false_pos = 0
	t0 = time.perf_counter()
	for i in range(probes):
		q = f"probe-{i}-{rng.randrange(1_000_000_000)}"
		if q in bf and q not in values:
			false_pos += 1
	t_query = time.perf_counter() - t0
	emp = false_pos / float(probes)
	theory = bf.estimated_false_positive_rate(n_inserted=n)
	return m, k, false_pos, emp, theory, t_insert + t_query


def main() -> None:
	parser = argparse.ArgumentParser(description="Benchmark Bloom filter false positive rates")
	parser.add_argument("--out", default="data/results.csv", help="CSV output path")
	parser.add_argument("--seed", type=int, default=42, help="RNG seed")
	parser.add_argument("--min-n", type=int, default=1000, help="Minimum n")
	parser.add_argument("--max-n", type=int, default=20000, help="Maximum n (inclusive)")
	parser.add_argument("--step", type=int, default=1000, help="Step for n")
	parser.add_argument("--probes", type=int, default=5000, help="Negative probes per n")
	parser.add_argument("--p", type=float, default=0.01, help="Target false positive probability")
	args = parser.parse_args()

	os.makedirs(os.path.dirname(args.out), exist_ok=True)

	rng = random.Random(args.seed)
	print(f"# Benchmark Bloom Filter (seed={args.seed})")
	print(f"# Writing CSV to {args.out}")
	rows: List[List] = [["n", "m", "k", "false_pos", "probes", "empirical_p", "theory_p", "elapsed_s"]]
	for n in range(args.min_n, args.max_n + 1, args.step):
		m, k, false_pos, emp, theory, elapsed = run_trial(n, args.p, args.probes, rng)
		rows.append([n, m, k, false_pos, args.probes, f"{emp:.6f}", f"{theory:.6f}", f"{elapsed:.6f}"])
		print(f"n={n:5d} m={m:7d} k={k:2d} emp={emp:.5f} theory={theory:.5f} elapsed={elapsed:.3f}s")

	with open(args.out, "w", newline="") as f:
		writer = csv.writer(f)
		writer.writerows(rows)
	print("Done.")


if __name__ == "__main__":
	main()


