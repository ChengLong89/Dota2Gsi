"""Summarize a logged match: python analyze_match.py [match_logs/<matchid>.jsonl]

With no argument it uses the most recent log. Prints last-hit checkpoints,
item timings, death times and moments you were sitting on lots of gold.
Add --plot to save a PNG of gold / net worth / last hits over time (needs matplotlib).
"""

import glob
import json
import os
import sys


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def fmt(t):
    return f"{t // 60:02d}:{t % 60:02d}"


def summarize(rows):
    if not rows:
        print("Empty log.")
        return
    print(f"Hero: {rows[-1]['hero']}   duration: {fmt(rows[-1]['t'])}")
    last = rows[-1]
    print(f"Final K/D/A {last['k']}/{last['d']}/{last['a']}   LH/DN {last['lh']}/{last['dn']}"
          f"   GPM {last['gpm']}  XPM {last['xpm']}")

    print("\nLast hits:")
    for m in (5, 10, 15, 20, 25, 30):
        row = next((r for r in rows if r["t"] >= m * 60), None)
        if row:
            print(f"  {m:>2} min: {row['lh']}")

    print("\nItem timings:")
    seen = set(rows[0]["items"])
    for r in rows[1:]:
        for item in r["items"]:
            if item not in seen and not item.startswith("item_tpscroll"):
                print(f"  {fmt(r['t'])}  {item.replace('item_', '')}")
        seen |= set(r["items"])

    print("\nDeaths:")
    prev_d = rows[0]["d"] or 0
    for r in rows:
        if (r["d"] or 0) > prev_d:
            print(f"  {fmt(r['t'])}")
        prev_d = r["d"] or 0

    rich = [r for r in rows if r["alive"] and (r["gold"] or 0) >= 2500]
    if rich:
        print(f"\nAlive with 2500+ unspent gold for ~{len(rich) * (rows[1]['t'] - rows[0]['t'] if len(rows) > 1 else 0)}s"
              f" (first at {fmt(rich[0]['t'])})")


def plot(rows, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = [r["t"] / 60 for r in rows]
    fig, ax = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    ax[0].plot(t, [r["nw"] or 0 for r in rows], label="net worth")
    ax[0].plot(t, [r["gold"] or 0 for r in rows], label="unspent gold")
    ax[0].legend()
    ax[1].plot(t, [r["lh"] or 0 for r in rows], label="last hits")
    ax[1].set_xlabel("minute")
    ax[1].legend()
    fig.tight_layout()
    fig.savefig(out)
    print(f"\nSaved {out}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0] if args else max(glob.glob("match_logs/*.jsonl"), key=os.path.getmtime, default=None)
    if not path:
        sys.exit("No logs found in match_logs/")
    rows = load(path)
    summarize(rows)
    if "--plot" in sys.argv:
        plot(rows, os.path.splitext(path)[0] + ".png")
