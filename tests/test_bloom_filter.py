import os
import random
import tempfile
import unittest

from src.bloom_filter import BloomFilter


class TestBloomFilter(unittest.TestCase):
	def test_basic_membership(self):
		n = 1000
		m = BloomFilter.size_for(n, 0.01)
		k = BloomFilter.optimal_num_hashes(m, n)
		bf = BloomFilter(m, k)
		items = [f"v{i}" for i in range(100)]
		for it in items:
			bf.add(it)
		for it in items:
			self.assertIn(it, bf)
		self.assertNotIn("not-present", bf)

	def test_no_false_negatives(self):
		n = 2000
		m = BloomFilter.size_for(n, 0.02)
		k = BloomFilter.optimal_num_hashes(m, n)
		bf = BloomFilter(m, k)
		vals = [f"key-{i}" for i in range(n)]
		bf.insert_many(vals)
		for v in vals:
			self.assertIn(v, bf)

	def test_empirical_rate_close_to_theory(self):
		random.seed(123)
		n = 4000
		target_p = 0.01
		m = BloomFilter.size_for(n, target_p)
		k = BloomFilter.optimal_num_hashes(m, n)
		bf = BloomFilter(m, k)
		inserted = [f"item-{i}-{random.randrange(1_000_000)}" for i in range(n)]
		bf.insert_many(inserted)

		# Probe negatives
		probes = 5000
		false_pos = 0
		for i in range(probes):
			q = f"probe-{i}-{random.randrange(1_000_000)}"
			if q in bf and q not in inserted:
				false_pos += 1
		empirical = false_pos / float(probes)
		theory = bf.estimated_false_positive_rate(n_inserted=n)
		# Allow some tolerance (stochastic)
		self.assertLess(abs(empirical - theory), max(0.01, theory * 0.5))

	def test_serde_roundtrip(self):
		n = 500
		m = BloomFilter.size_for(n, 0.05)
		k = BloomFilter.optimal_num_hashes(m, n)
		bf = BloomFilter(m, k)
		for i in range(n):
			bf.add(f"val-{i}")
		with tempfile.TemporaryDirectory() as d:
			path = os.path.join(d, "bloom.bin")
			with open(path, "wb") as f:
				f.write(bf.to_bytes())
			with open(path, "rb") as f:
				data = f.read()
		bf2 = BloomFilter.from_bytes(data)
		self.assertEqual(bf2.num_bits, bf.num_bits)
		self.assertEqual(bf2.num_hashes, bf.num_hashes)
		self.assertGreater(bf2.bit_density(), 0.0)


if __name__ == "__main__":
	unittest.main()


