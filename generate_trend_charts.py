"""
Generate 10-day RAG trend chart mockups for the blog post.
Style matches the existing rag_latency_p50/p95 screenshots:
  - White background, light grey grid
  - Colored line + filled area (green=good, yellow=warning, red=bad)
  - Dots at each data point
  - "Last 10 days" subtitle
  - X axis: Apr 26 – May 05 (10 consecutive days representing the last 10 days)
  - Top-right X close button (painted as text)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from pathlib import Path
from datetime import date, timedelta

OUT_DIR = Path(r"C:\Users\rajes\OneDrive\blog\my-blog\static\images")

# 10 days: Apr 26 – May 05
START = date(2026, 4, 26)
DATES = [START + timedelta(days=i) for i in range(10)]
DATE_LABELS = [d.strftime("Apr %d").replace("Apr 0", "Apr ") if d.month == 4
               else d.strftime("May %d").replace("May 0", "May ")
               for d in DATES]


def make_chart(
    filename: str,
    title: str,
    values: list,
    y_fmt: str = "{:.0f}",
    color: str = "#22c55e",   # green
    fill_alpha: float = 0.15,
    y_label_suffix: str = "",
    y_min_pad_frac: float = 0.15,
    y_max_pad_frac: float = 0.15,
):
    fig, ax = plt.subplots(figsize=(5.2, 3.0), dpi=130)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    xs = np.arange(len(DATES))
    ys = np.array(values, dtype=float)

    # filled area
    ax.fill_between(xs, ys, alpha=fill_alpha, color=color, linewidth=0)
    # line
    ax.plot(xs, ys, color=color, linewidth=2.0, zorder=3)
    # dots
    ax.scatter(xs, ys, color=color, s=28, zorder=4)

    # grid
    ax.grid(True, which="both", color="#e5e7eb", linewidth=0.7, linestyle="-")
    ax.set_axisbelow(True)

    # spines
    for spine in ax.spines.values():
        spine.set_visible(False)

    # x axis
    ax.set_xticks(xs)
    ax.set_xticklabels(DATE_LABELS, fontsize=7.5, color="#6b7280")
    ax.tick_params(axis="x", length=0)

    # y axis — compute nice range
    lo = min(ys)
    hi = max(ys)
    span = hi - lo if hi != lo else hi * 0.2 or 1
    y_lo = lo - span * y_min_pad_frac
    y_hi = hi + span * y_max_pad_frac
    ax.set_ylim(y_lo, y_hi)

    # y tick labels
    ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=6, integer=False))
    def fmt_y(val, pos):
        return y_fmt.format(val) + y_label_suffix
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(fmt_y))
    ax.tick_params(axis="y", length=0, labelsize=7.5, colors="#6b7280")

    # title block (top-left, like the screenshots)
    fig.text(0.04, 0.93, title, fontsize=10, fontweight="bold", color="#111827",
             va="top", ha="left")
    fig.text(0.04, 0.82, "Last 10 days", fontsize=7.5, color="#9ca3af",
             va="top", ha="left")
    # close X (top-right)
    fig.text(0.97, 0.93, "×", fontsize=12, color="#9ca3af", va="top", ha="right")

    ax.set_position([0.10, 0.17, 0.87, 0.60])

    out_path = OUT_DIR / filename
    fig.savefig(out_path, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  wrote {out_path.name}")


# ---------------------------------------------------------------------------
# DATA  (10 values, one per day Apr 26 – May 05)
#
# Causal chain:
#   query_volume drives tokens_in, tokens_out, daily_usd (all co-move)
#   tokens_per_successful rises independently mid-week (chunk filter letting
#     more through) — this is the degradation signal, NOT volume
#   rising tokens_per_successful → worse answers → lower satisfaction,
#     higher follow_up_rate, and rising cost_per_successful (more refusals)
#   P95 latency tracks tokens_per_successful (bigger context = tail latency)
#   P50 latency tracks volume more loosely (queuing effect)
#   rated_count tracks volume (more users = more feedback clicks)
#   cost_per_query tracks tokens_per_successful (longer prompts cost more)
#   By May 3–5 the chunk filter threshold is tightened → recovery
# ---------------------------------------------------------------------------

# ── QUERY VOLUME (latent driver, not charted directly) ────────────────────
# Low start, mid-week surge Apr 29–30, then weekend dip, then steady
volume = [38, 45, 52, 61, 68, 58, 42, 48, 55, 52]

# ── TOKENS PER SUCCESSFUL (the degradation signal) ────────────────────────
# Drifts UP mid-week (filter letting bigger chunks through), then corrected
# This is the root cause that cascades into satisfaction/follow-up/P95
tokens_per_succ = [1880, 1920, 1990, 2080, 2190, 2240, 2180, 2050, 1940, 1870]

# ── LATENCY ──────────────────────────────────────────────────────────────────
# P50: loosely tracks volume (queuing), not as sensitive to chunk size
p50 = [2580, 2620, 2700, 2780, 2840, 2810, 2740, 2690, 2650, 2610]

# P95: tracks tokens_per_successful (tail latency = longest context path)
# peaks a day after tokens_per_succ peaks (inference queue lag)
p95 = [3750, 3820, 4050, 4480, 4920, 5100, 4780, 4350, 4050, 3820]

# ── COST ─────────────────────────────────────────────────────────────────────
# daily_usd: volume-driven — tracks query count
daily_usd = [0.19, 0.22, 0.26, 0.31, 0.34, 0.29, 0.21, 0.24, 0.27, 0.26]

# per_query_usd: tracks tokens_per_successful (longer prompts = more spend/query)
per_query = [0.0050, 0.0049, 0.0050, 0.0051, 0.0050, 0.0050, 0.0050, 0.0050, 0.0049, 0.0050]

# per_successful_usd: rises when refusal rate rises (more spend per useful answer)
# correlated with tokens_per_successful degradation — peaks May 1
per_successful = [0.0082, 0.0086, 0.0094, 0.0108, 0.0124, 0.0138, 0.0131, 0.0112, 0.0094, 0.0085]

# per_grounded_usd: tightest bar, moves similarly but wider spread
per_grounded = [0.0121, 0.0128, 0.0142, 0.0163, 0.0188, 0.0207, 0.0196, 0.0168, 0.0141, 0.0128]

# ── TOKEN VOLUME ─────────────────────────────────────────────────────────────
# tokens_in: volume × tokens_per_successful — both factors compound
tokens_in = [v * tps // 100 * 100
             for v, tps in zip(volume, tokens_per_succ)]
# hand-smooth to round numbers
tokens_in = [17200, 20800, 24900, 30400, 35900, 31200, 22000, 23600, 25400, 23400]

# tokens_out: tracks volume (answer length is fairly stable)
tokens_out = [2200, 2580, 2990, 3520, 3940, 3380, 2450, 2780, 3180, 3020]

# ── USER FEEDBACK ─────────────────────────────────────────────────────────────
# satisfaction: INVERSE of tokens_per_successful degradation
# drops as chunk quality degrades, recovers after filter fix May 3
satisfaction = [0.84, 0.83, 0.81, 0.78, 0.73, 0.69, 0.72, 0.77, 0.82, 0.85]

# rated_count: tracks volume (more queries = more feedback opportunities)
rated_count = [11, 14, 17, 20, 23, 19, 13, 16, 19, 18]

# follow_up_rate: INVERSE of satisfaction (users retry bad answers)
# peaks when satisfaction troughs, recovers with it
follow_up = [0.16, 0.18, 0.21, 0.25, 0.30, 0.34, 0.29, 0.23, 0.17, 0.14]


# ---------------------------------------------------------------------------
# GENERATE
# ---------------------------------------------------------------------------

print("Generating trend charts...")

# Latency (replace existing sparse charts with full 10-day)
make_chart("rag_latency_p50.png", "P50 LATENCY", p50,
           y_fmt="{:.0f}", y_label_suffix=" ms", color="#22c55e")

make_chart("rag_latency_p95.png", "P95 LATENCY", p95,
           y_fmt="{:.0f}", y_label_suffix=" ms", color="#eab308")  # yellow

# Cost
make_chart("rag_trend_daily_usd.png", "DAILY COST", daily_usd,
           y_fmt="${:.2f}", color="#22c55e")

make_chart("rag_trend_per_query_usd.png", "COST / QUERY", per_query,
           y_fmt="${:.4f}", color="#22c55e")

make_chart("rag_trend_per_successful_usd.png", "COST / SUCCESSFUL", per_successful,
           y_fmt="${:.4f}", color="#eab308")

make_chart("rag_trend_per_grounded_usd.png", "COST / GROUNDED", per_grounded,
           y_fmt="${:.4f}", color="#eab308")

# Token volume
make_chart("rag_trend_tokens_in.png", "TOKENS IN / DAY", tokens_in,
           y_fmt="{:.0f}", color="#22c55e")

make_chart("rag_trend_tokens_out.png", "TOKENS OUT / DAY", tokens_out,
           y_fmt="{:.0f}", color="#22c55e")

make_chart("rag_trend_tokens_per_successful.png", "TOKENS / SUCCESSFUL", tokens_per_succ,
           y_fmt="{:.0f}", color="#22c55e")

# User feedback
make_chart("rag_trend_satisfaction.png", "SATISFACTION SCORE", satisfaction,
           y_fmt="{:.0%}", color="#22c55e", y_min_pad_frac=0.08, y_max_pad_frac=0.08)

make_chart("rag_trend_rated_count.png", "RATED COUNT", rated_count,
           y_fmt="{:.0f}", color="#6366f1")  # indigo/neutral

make_chart("rag_trend_follow_up_rate.png", "FOLLOW-UP RATE", follow_up,
           y_fmt="{:.0%}", color="#eab308", y_min_pad_frac=0.08, y_max_pad_frac=0.08)

print("Done.")
