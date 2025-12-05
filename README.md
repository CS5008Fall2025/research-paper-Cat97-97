[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/zBqi0PeJ)
# Research Paper
* Name: <!-- Sitong Zhang -->
* Semester: <!-- Fall 2025 -->
* Topic: Bloom Filter


## Introduction
Bloom filters are probabilistic set data structures that support insert and membership query with no false negatives and tunable false positive probability \(p\) [1, 2]. They enable memory-efficient representation of large sets where storing exact elements is impractical. Typical applications include databases and storage systems (e.g., query filtering before disk fetch), distributed systems (cache pre-checks), and networking (packet filtering, URL blacklists) [2].

Burton H. Bloom introduced the structure in 1970 as a space–time trade-off using bit arrays and multiple hash functions [1]. Modern systems often implement hash function families using double hashing as analyzed by Kirsch and Mitzenmacher [3], which reduces hash cost while preserving performance. This report provides background and history, a high-level operational overview with pseudo-code, a theoretical analysis including runtime, memory, and false positive probability derivations, empirical results that validate theory, implementation details, and use cases.

## Algorithm Background and Overview
- Concept: Maintain a bit array of length \(m\). Use \(k\) hash functions mapping an element \(x\) to \(k\) positions in \([0, m-1]\). To insert, set those bits to 1. To query, check if all \(k\) bits are 1; if any bit is 0, the element is definitely not present; if all 1, it is “probably present” (may be a false positive).
- History: Introduced in 1970 [1]; widely adapted for network applications, web caching, deduplication, and storage engines [2]. Many variants exist (counting Bloom filters, compressed Bloom filters, scalable Bloom filters) [2, 4].
- Data structure type: Probabilistic set representation (approximate membership query).

### Pseudo-code
Let \(h_1, h_2\) be two base hash functions. Use double hashing to derive \(k\) indices: \(g_i(x) = (h_1(x) + i \cdot h_2(x)) \bmod m\) for \(i \in [0, k-1]\) [3].

Insert(x):
```
for i = 0 .. k-1:
    pos = (h1(x) + i * h2(x)) mod m
    bitset[pos] = 1
```

Query(x):
```
for i = 0 .. k-1:
    pos = (h1(x) + i * h2(x)) mod m
    if bitset[pos] == 0:
        return NOT_PRESENT
return PROBABLY_PRESENT
```

## Theoretical Analysis
- Time complexity: Each operation touches \(k\) bits. Insert and query are \(O(k)\). With optimal \(k\) (below), \(k\) is a constant for fixed target \(p\), so operations are constant time.
- Space complexity: \(m\) bits.
- False positive probability: After inserting \(n\) items, each bit remains 0 with probability \((1 - \tfrac{1}{m})^{kn} \approx e^{-kn/m}\). Hence a given bit is 1 with probability \(1 - e^{-kn/m}\). A query is a false positive if all \(k\) bits are 1, so
\[
p \approx \bigl(1 - e^{-k n / m}\bigr)^{k}.
\]
- Optimal number of hashes: Minimizing \(p\) w.r.t. \(k\) yields \(k^* = \frac{m}{n}\ln 2\) (rounded to an integer).
- Sizing for a target \(p\): Solving for \(m\) gives
\[
m = -\frac{n \ln p}{(\ln 2)^2}.
\]
- Correctness: No false negatives. If an element was inserted, all of its \(k\) positions were set to 1 during insertion; queries only return NOT_PRESENT if they find any 0, which cannot happen for inserted elements. False positives occur only when unrelated insertions incidentally set all \(k\) positions used by the queried element.

## Empirical Analysis
We empirically validate the false positive probability against the theoretical estimate. For \(n\) from 1,000 to 20,000, we sized \(m\) for a target \(p = 0.01\) and used \(k = \text{round}(\tfrac{m}{n}\ln 2)\). For each \(n\), we inserted \(n\) random strings and tested 5,000 negative queries. The script writes `data/results.csv`, and we render a dependency-free SVG plot at `plots/false_positive.svg`.

- Data: see `data/results.csv`
- Figure: see `plots/false_positive.svg`
- Method: `scripts/benchmark_bloom_filter.py`, `scripts/plot_svg.py`

As expected, empirical rates closely follow theory \(p \approx \bigl(1 - e^{-k n / m}\bigr)^k\) (minor deviations are due to randomness and finite sample size). We also record elapsed time across insertion and queries to show operations remain near-constant per element for fixed \(k\).

## Application
Common use cases include:
- Databases and storage engines: Pre-filters for SSTables or on-disk indices to avoid unnecessary IO (e.g., LSM-tree systems).
- Web caches and CDNs: Avoid duplicate fetches; identify likely cache misses.
- Networking: Packet filtering, blacklists, and distributed set membership [2].

Key advantages are significant memory savings and fast queries; the trade-off is the possibility of false positives (mitigated by proper sizing).

## Implementation
Language: Python 3 (standard library only).

Files:
- `src/bloom_filter.py`: Bloom filter implementation using a `bytearray` bitset and SHA-256–based double hashing [3]. Includes serialization helpers and a small CLI demo.
- `tests/test_bloom_filter.py`: Unit tests for basic membership, no false negatives, empirical vs. theoretical rate, and serialization round-trip.
- `scripts/benchmark_bloom_filter.py`: Generates empirical results into CSV.
- `scripts/plot_svg.py`: Produces a simple SVG line chart from the CSV, no external dependencies.

Challenges and decisions:
- Hashing: To avoid multiple heavy hash computations, we use double hashing (Kirsch–Mitzenmacher) with two 64-bit values derived from SHA-256 [3].
- Bitset: We use `bytearray` for a compact in-memory bit array and implement get/set bit operations manually for portability.
- Sizing: Helpers expose \(m\) and \(k\) formulas to meet a target \(p\).

Key snippet (double hashing index generation):
```
for i in range(k):
    pos = (h1(x) + i * h2(x)) mod m
```

## Summary
Bloom filters provide fast, memory-efficient approximate set membership with no false negatives and controllable false positives. Theoretical analysis yields closed-form sizing rules for \(m\) and \(k\), and empirical results closely match those predictions under random inputs. The provided implementation and scripts can be used as a lightweight baseline or teaching aid; production systems should consider variants (e.g., counting or scalable Bloom filters) when deletions or growth beyond planned \(n\) are required [2, 4].

## How to Reproduce
1. Run unit tests:
   - `python -m unittest -v tests/test_bloom_filter.py`
2. Generate empirical data:
   - `python scripts/benchmark_bloom_filter.py --out data/results.csv --seed 42`
3. Plot SVG:
   - `python scripts/plot_svg.py --csv data/results.csv --out plots/false_positive.svg`
4. Demo run (optional):
   - `python -m src.bloom_filter --demo`

All outputs (CSV/plots) are included or can be regenerated with the above commands. Sample run outputs are captured under `data/`.

## References
[1] B. H. Bloom. “Space/Time Trade-offs in Hash Coding with Allowable Errors.” Communications of the ACM, 13(7):422–426, 1970.  
[2] A. Broder and M. Mitzenmacher. “Network Applications of Bloom Filters: A Survey.” Internet Mathematics, 1(4):485–509, 2004.  
[3] A. Kirsch and M. Mitzenmacher. “Less Hashing, Same Performance: Building a Better Bloom Filter.” ESA 2006.  
[4] M. Mitzenmacher. “Compressed Bloom Filters.” IEEE/ACM Transactions on Networking, 10(5):604–612, 2002.  
[5] “Bloom filter.” Wikipedia. (Background overview, parameter formulas, and variants.)