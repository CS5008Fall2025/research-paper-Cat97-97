#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
from typing import List, Tuple


def read_csv(path: str) -> Tuple[List[int], List[float], List[float]]:
	ns: List[int] = []
	emp: List[float] = []
	theory: List[float] = []
	with open(path, "r") as f:
		reader = csv.DictReader(f)
		for row in reader:
			ns.append(int(row["n"]))
			emp.append(float(row["empirical_p"]))
			theory.append(float(row["theory_p"]))
	return ns, emp, theory


def normalize(xs: List[float], xmin: float, xmax: float) -> List[float]:
	den = (xmax - xmin) or 1.0
	return [(x - xmin) / den for x in xs]


def polyline(points: List[Tuple[float, float]], color: str, width: int = 2) -> str:
	pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
	return f'<polyline fill="none" stroke="{color}" stroke-width="{width}" points="{pts}" />'


def main() -> None:
	parser = argparse.ArgumentParser(description="Plot CSV results to a simple SVG line chart")
	parser.add_argument("--csv", default="data/results.csv", help="Input CSV path")
	parser.add_argument("--out", default="plots/false_positive.svg", help="Output SVG path")
	args = parser.parse_args()

	os.makedirs(os.path.dirname(args.out), exist_ok=True)
	ns, emp, theory = read_csv(args.csv)
	if not ns:
		raise SystemExit("No data to plot")

	# SVG canvas
	W, H = 800, 480
	PAD_L, PAD_R, PAD_T, PAD_B = 70, 20, 20, 60
	plot_w = W - PAD_L - PAD_R
	plot_h = H - PAD_T - PAD_B

	# Normalize
	xmin, xmax = min(ns), max(ns)
	ymin, ymax = 0.0, max(max(emp), max(theory)) * 1.1
	xs = normalize([float(n) for n in ns], xmin, xmax)
	ys_emp = normalize(emp, ymin, ymax)
	ys_the = normalize(theory, ymin, ymax)

	def to_px(xn: float, yn: float) -> Tuple[float, float]:
		x = PAD_L + xn * plot_w
		y = PAD_T + (1.0 - yn) * plot_h
		return x, y

	points_emp = [to_px(xn, yn) for xn, yn in zip(xs, ys_emp)]
	points_the = [to_px(xn, yn) for xn, yn in zip(xs, ys_the)]

	# Axes and ticks
	ticks_x = 5
	ticks_y = 5
	grid = []
	labels = []
	# X axis
	for i in range(ticks_x + 1):
		xn = i / float(ticks_x)
		x, y0 = to_px(xn, 0.0)
		_, y1 = to_px(xn, 1.0)
		grid.append(f'<line x1="{x:.1f}" y1="{y0:.1f}" x2="{x:.1f}" y2="{y1:.1f}" stroke="#eee" />')
		val = int(round(xmin + xn * (xmax - xmin)))
		labels.append(f'<text x="{x:.1f}" y="{H - 20}" font-size="12" text-anchor="middle" fill="#444">{val}</text>')
	# Y axis
	for i in range(ticks_y + 1):
		yn = i / float(ticks_y)
		x0, y = to_px(0.0, yn)
		x1, _ = to_px(1.0, yn)
		grid.append(f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" stroke="#eee" />')
		val = ymin + yn * (ymax - ymin)
		labels.append(f'<text x="{PAD_L - 8}" y="{y + 4:.1f}" font-size="12" text-anchor="end" fill="#444">{val:.3f}</text>')

	title = '<text x="400" y="18" font-size="16" text-anchor="middle" fill="#222">Bloom Filter False Positive Rate</text>'
	xlab = f'<text x="{(PAD_L + plot_w/2):.1f}" y="{H - 5}" font-size="13" text-anchor="middle" fill="#222">n (inserted items)</text>'
	ylab = f'<text x="18" y="{(PAD_T + plot_h/2):.1f}" font-size="13" text-anchor="middle" fill="#222" transform="rotate(-90, 18, {(PAD_T + plot_h/2):.1f})">false positive probability</text>'
	legend = (
		'<rect x="560" y="26" width="220" height="44" fill="#fff" stroke="#ddd" />'
		'<line x1="580" y1="42" x2="610" y2="42" stroke="#1f77b4" stroke-width="3" />'
		'<text x="620" y="46" font-size="12" fill="#333">Empirical</text>'
		'<line x1="580" y1="62" x2="610" y2="62" stroke="#ff7f0e" stroke-width="3" />'
		'<text x="620" y="66" font-size="12" fill="#333">Theoretical</text>'
	)

	content = "\n".join([
		f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
		'<rect width="100%" height="100%" fill="#ffffff"/>',
		title,
		*grid,
		polyline(points_emp, "#1f77b4", 3),
		polyline(points_the, "#ff7f0e", 3),
		*labels,
		xlab,
		ylab,
		legend,
		"</svg>",
	])
	with open(args.out, "w") as f:
		f.write(content)
	print(f"Wrote {args.out}")


if __name__ == "__main__":
	main()


