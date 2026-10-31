"""
Scenario 11 - Contact Window Scheduling with Integer Linear Programming (ILP)
==============================================================================
Optimally schedules ground contacts for the Walker 24/3/1 constellation
from Scenario 06, using ILP to simultaneously:
  1. Maximise total scheduled contact time across all satellites
  2. Minimise worst-case revisit gap (max gap between successive contacts
     for any satellite)

Constraints:
  - One antenna per ground station (only one satellite served at a time)
  - No overlapping assignments at the same station
  - Each contact window assigned at most once
  - Binary decision variables: x[i] = 1 if window i is scheduled

Multi-objective (weighted sum, maximised):
  alpha * total_contact_time/100  -  beta * G_max/100

Input:  output_sc06/Contact_[A-C][1-8].txt  (from Scenario 06)
Output: schedule_output.txt, 11_schedule_gantt.png, 11_ilp_summary.txt

Solver: HiGHS via PuLP 4.x

Author: Stephen O. Ogodo
Date:   2026-10-30
"""

import os
import re
import sys
from datetime import datetime, timedelta
from collections import defaultdict

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── PuLP ILP solver (PuLP 4.x API) ──────────────────────────────────────────
try:
    import pulp
except ImportError:
    sys.exit("PuLP not found. Run: pip install pulp --break-system-packages")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
INPUT_DIR   = os.path.join(os.path.dirname(__file__), "output_sc11")
OUTPUT_DIR  = os.path.dirname(__file__)

STATIONS    = ["London", "Nairobi", "Lagos"]   # Tromso excluded (0 passes)
PLANES      = ["A", "B", "C"]
SATS_PER_PLANE = 8

# Multi-objective weights
ALPHA = 1.0    # weight on total contact time (per 100 s)
BETA  = 2.0    # weight on worst-case gap penalty (per 100 s)
                # beta > alpha => gap minimisation prioritised

EPOCH = datetime(2024, 1, 1, 0, 0, 0)   # simulation start

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — PARSE CONTACT FILES
# ─────────────────────────────────────────────────────────────────────────────

def parse_datetime(s):
    return datetime.strptime(s.strip(), "%d %b %Y %H:%M:%S.%f")

def parse_contact_file(filepath):
    """
    Returns list of dicts:
      { satellite, station, start, stop, duration_s }
    """
    satellite = None
    current_station = None
    windows = []

    with open(filepath, "r") as f:
        lines = f.readlines()

    for line in lines:
        line = line.rstrip()
        m = re.match(r"Target:\s+(\S+)", line)
        if m:
            satellite = m.group(1)
            continue

        m = re.match(r"Observer:\s+(.+)", line)
        if m:
            current_station = m.group(1).strip()
            continue

        # Data row: two datetime strings then a float
        m = re.match(
            r"(\d{2} \w{3} \d{4} \d{2}:\d{2}:\d{2}\.\d+)"
            r"\s+"
            r"(\d{2} \w{3} \d{4} \d{2}:\d{2}:\d{2}\.\d+)"
            r"\s+"
            r"([\d.]+)",
            line
        )
        if m and satellite and current_station in STATIONS:
            start    = parse_datetime(m.group(1))
            stop     = parse_datetime(m.group(2))
            duration = float(m.group(3))
            windows.append({
                "satellite": satellite,
                "station":   current_station,
                "start":     start,
                "stop":      stop,
                "duration":  duration,
            })

    return windows


def load_all_windows():
    all_windows = []
    for plane in PLANES:
        for sat_num in range(1, SATS_PER_PLANE + 1):
            fname = f"Contact_{plane}{sat_num}.txt"
            fpath = os.path.join(INPUT_DIR, fname)
            if not os.path.exists(fpath):
                print(f"  WARNING: {fname} not found -- skipping")
                continue
            wins = parse_contact_file(fpath)
            all_windows.extend(wins)

    all_windows.sort(key=lambda w: w["start"])
    print(f"  Loaded {len(all_windows)} candidate contact windows")
    return all_windows


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — BUILD CONFLICT GRAPH
# ─────────────────────────────────────────────────────────────────────────────

def find_conflicts(windows):
    """
    Returns list of (i, j) index pairs that conflict
    (same station, overlapping time intervals).
    """
    conflicts = []
    by_station = defaultdict(list)
    for idx, w in enumerate(windows):
        by_station[w["station"]].append(idx)

    for station, indices in by_station.items():
        n = len(indices)
        for a in range(n):
            for b in range(a + 1, n):
                i, j = indices[a], indices[b]
                wi, wj = windows[i], windows[j]
                if wi["start"] < wj["stop"] and wj["start"] < wi["stop"]:
                    conflicts.append((i, j))

    print(f"  Found {len(conflicts)} conflict pairs")
    return conflicts


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — BUILD GAP STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────

def build_gap_structure(windows):
    """
    For each satellite, identify consecutive pairs of windows (by start time).
    Returns:
      sat_windows: dict satellite -> sorted list of window indices
      consecutive_pairs: list of (i, j, gap_seconds) for adjacent windows per sat
    """
    sat_windows = defaultdict(list)
    for idx, w in enumerate(windows):
        sat_windows[w["satellite"]].append(idx)

    for sat in sat_windows:
        sat_windows[sat].sort(key=lambda idx: windows[idx]["start"])

    consecutive_pairs = []
    for sat, indices in sat_windows.items():
        for k in range(len(indices) - 1):
            i = indices[k]
            j = indices[k + 1]
            gap_s = (windows[j]["start"] - windows[i]["stop"]).total_seconds()
            if gap_s < 0:
                gap_s = 0
            consecutive_pairs.append((i, j, gap_s))

    return sat_windows, consecutive_pairs


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — BUILD AND SOLVE ILP  (PuLP 4.x API)
# ─────────────────────────────────────────────────────────────────────────────

def solve_ilp(windows, conflicts, sat_windows, consecutive_pairs):
    """
    PuLP 4.x uses prob.add_variable() instead of LpVariable().
    solve() returns an LpSolveStats object; use pulp.value() for variable values.

    Decision variables:
      x[i]   = 1 if window i is scheduled  (Binary)
      g[k]   = active gap for pair k, linearised via big-M
      G_max  = max gap across all pairs  (Continuous, to minimise)

    Objective (maximise):
      alpha * sum(duration[i] * x[i]) / 100
    - beta  * G_max / 100

    Constraints:
      - Station exclusivity:  x[i] + x[j] <= 1  for each conflict pair
      - Gap linearisation (big-M):
            g[k] >= gap[k] * (x[i] + x[j] - 1)
            g[k] <= gap[k] * x[i]
            g[k] <= gap[k] * x[j]
      - G_max >= g[k]  for all k
    """
    N = len(windows)
    MAX_GAP_S = 86400.0   # 24 h upper bound

    prob = pulp.LpProblem("ContactScheduling", pulp.LpMaximize)

    # Binary scheduling variables
    x = [prob.add_variable(f"x_{i}", cat="Binary") for i in range(N)]

    # Max-gap variable (continuous)
    G_max = prob.add_variable("G_max", lowBound=0)

    # Gap auxiliary variables
    g = [prob.add_variable(f"g_{k}", lowBound=0, upBound=MAX_GAP_S)
         for k in range(len(consecutive_pairs))]

    # ── Objective ────────────────────────────────────────────────────────────
    total_contact = pulp.lpSum(windows[i]["duration"] * x[i] for i in range(N))
    prob += ALPHA * total_contact / 100.0 - BETA * G_max / 100.0

    # ── Constraints ──────────────────────────────────────────────────────────

    # 1. Station exclusivity — one antenna per station at a time
    for (i, j) in conflicts:
        prob += x[i] + x[j] <= 1

    # 2. Gap linearisation and G_max tracking
    for k, (i, j, gap_s) in enumerate(consecutive_pairs):
        gvar = g[k]
        prob += gvar >= gap_s * (x[i] + x[j] - 1)
        prob += gvar <= gap_s * x[i]
        prob += gvar <= gap_s * x[j]
        prob += G_max >= gvar

    # ── Solve ────────────────────────────────────────────────────────────────
    print("  Solving ILP with HiGHS ...")
    solver = pulp.HiGHS(msg=False, timeLimit=120)
    result = prob.solve(solver)

    status_str = result.status_str
    print(f"  Solver status: {status_str}")

    # Extract solution
    scheduled = [i for i in range(N) if pulp.value(x[i]) and pulp.value(x[i]) > 0.5]
    total_s   = sum(windows[i]["duration"] for i in scheduled)
    max_gap_s = pulp.value(G_max) if pulp.value(G_max) else 0.0

    print(f"  Objective value: {pulp.value(prob.objective):.4f}")

    return scheduled, status_str, total_s, max_gap_s


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — COMPUTE STATISTICS
# ─────────────────────────────────────────────────────────────────────────────

def compute_statistics(windows, scheduled, sat_windows):
    scheduled_set = set(scheduled)
    stats = {}

    for sat, indices in sat_windows.items():
        sel = sorted([i for i in indices if i in scheduled_set],
                     key=lambda i: windows[i]["start"])
        total_contact = sum(windows[i]["duration"] for i in sel)

        gaps = []
        for k in range(len(sel) - 1):
            gap = (windows[sel[k+1]]["start"] - windows[sel[k]]["stop"]).total_seconds()
            gaps.append(gap)

        if sel:
            gap_start = (windows[sel[0]]["start"] - EPOCH).total_seconds()
            gap_end   = (EPOCH + timedelta(hours=24) - windows[sel[-1]]["stop"]).total_seconds()
            gaps_all  = [gap_start] + gaps + [gap_end]
        else:
            gaps_all  = [86400.0]

        stats[sat] = {
            "n_scheduled":    len(sel),
            "n_available":    len(indices),
            "total_contact_s": total_contact,
            "max_gap_s":      max(gaps_all),
            "mean_gap_s":     np.mean(gaps_all),
            "gaps":           gaps_all,
            "scheduled_indices": sel,
        }

    station_load = defaultdict(float)
    for i in scheduled:
        station_load[windows[i]["station"]] += windows[i]["duration"]

    return stats, station_load


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — WRITE SCHEDULE OUTPUT
# ─────────────────────────────────────────────────────────────────────────────

def write_schedule(windows, scheduled, stats, station_load,
                   total_contact_s, max_gap_s, ilp_status):
    outpath = os.path.join(OUTPUT_DIR, "schedule_output.txt")

    with open(outpath, "w") as f:
        f.write("=" * 72 + "\n")
        f.write("SCENARIO 11 -- ILP CONTACT SCHEDULE\n")
        f.write("Walker 24/3/1 Constellation | 3 Ground Stations | 24-hour Window\n")
        f.write("=" * 72 + "\n\n")
        f.write(f"Solver status    : {ilp_status}\n")
        f.write(f"Objective weights: alpha={ALPHA} (contact), beta={BETA} (gap)\n")
        f.write(f"Total scheduled contact : {total_contact_s:.1f} s  "
                f"({total_contact_s/3600:.2f} h)\n")
        f.write(f"Worst-case revisit gap  : {max_gap_s:.1f} s  "
                f"({max_gap_s/3600:.2f} h)\n\n")

        f.write("-" * 72 + "\n")
        f.write("GROUND STATION UTILISATION\n")
        f.write("-" * 72 + "\n")
        for st in STATIONS:
            load_s = station_load.get(st, 0)
            f.write(f"  {st:<10}  {load_s:>8.1f} s  ({load_s/3600:.2f} h)\n")
        f.write("\n")

        f.write("-" * 72 + "\n")
        f.write("SCHEDULED CONTACT WINDOWS (chronological)\n")
        f.write("-" * 72 + "\n")
        f.write(f"  {'Satellite':<6}  {'Station':<10}  "
                f"{'Start (UTC)':<25}  {'Stop (UTC)':<25}  {'Dur(s)':>8}\n")
        f.write("  " + "-" * 68 + "\n")

        for i in sorted(scheduled, key=lambda i: windows[i]["start"]):
            w = windows[i]
            f.write(f"  {w['satellite']:<6}  {w['station']:<10}  "
                    f"{w['start'].strftime('%d %b %Y %H:%M:%S'):<25}  "
                    f"{w['stop'].strftime('%d %b %Y %H:%M:%S'):<25}  "
                    f"{w['duration']:>8.1f}\n")

        f.write("\n")
        f.write("-" * 72 + "\n")
        f.write("PER-SATELLITE SUMMARY\n")
        f.write("-" * 72 + "\n")
        f.write(f"  {'Sat':<5}  {'Schd':>5}  {'Avail':>5}  "
                f"{'Contact(s)':>10}  {'MaxGap(s)':>10}  {'MaxGap(h)':>10}\n")
        f.write("  " + "-" * 55 + "\n")

        for sat in sorted(stats.keys()):
            s = stats[sat]
            f.write(f"  {sat:<5}  {s['n_scheduled']:>5}  {s['n_available']:>5}  "
                    f"{s['total_contact_s']:>10.1f}  {s['max_gap_s']:>10.1f}  "
                    f"{s['max_gap_s']/3600:>10.2f}\n")

    print(f"  Schedule written to: schedule_output.txt")
    return outpath


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — GANTT CHART
# ─────────────────────────────────────────────────────────────────────────────

def plot_gantt(windows, scheduled, stats):
    scheduled_set = set(scheduled)

    all_sats = [f"{p}{n}" for p in PLANES for n in range(1, SATS_PER_PLANE + 1)]
    active_sats = [s for s in all_sats if s in stats and stats[s]["n_scheduled"] > 0]

    n_sats = len(active_sats)
    sat_idx = {s: i for i, s in enumerate(active_sats)}

    STATION_COLORS = {
        "London":  "#2196F3",
        "Nairobi": "#4CAF50",
        "Lagos":   "#FF9800",
    }

    fig, ax = plt.subplots(figsize=(18, max(8, n_sats * 0.45)))

    for i in scheduled:
        w = windows[i]
        if w["satellite"] not in sat_idx:
            continue
        y     = sat_idx[w["satellite"]]
        start = (w["start"] - EPOCH).total_seconds() / 3600.0
        dur   = w["duration"] / 3600.0
        color = STATION_COLORS.get(w["station"], "#999")
        ax.barh(y, dur, left=start, height=0.6,
                color=color, alpha=0.85, edgecolor="white", linewidth=0.3)

    ax.set_yticks(range(n_sats))
    ax.set_yticklabels(active_sats, fontsize=7)
    ax.set_xlabel("Time from Epoch (hours UTC, 01 Jan 2024)", fontsize=10)
    ax.set_title("Scenario 11 -- ILP-Optimised Contact Schedule\n"
                 "Walker 24/3/1 Constellation | Objective: Max Contact + Min Worst-Case Gap",
                 fontsize=11, fontweight="bold")
    ax.set_xlim(0, 24)
    ax.set_ylim(-0.5, n_sats - 0.5)

    for plane_idx, plane in enumerate(PLANES):
        boundary = plane_idx * SATS_PER_PLANE - 0.5
        if boundary >= 0:
            ax.axhline(boundary, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
        mid = plane_idx * SATS_PER_PLANE + SATS_PER_PLANE / 2 - 0.5
        ax.text(24.2, mid, f"Plane {plane}", va="center", fontsize=8,
                color="gray", fontstyle="italic")

    ax.grid(axis="x", linestyle=":", alpha=0.4)

    patches = [mpatches.Patch(color=c, label=s)
               for s, c in STATION_COLORS.items()]
    ax.legend(handles=patches, loc="upper right", fontsize=9,
              title="Ground Station", title_fontsize=9)

    plt.tight_layout()
    outpath = os.path.join(OUTPUT_DIR, "11_schedule_gantt.png")
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Gantt chart saved to: 11_schedule_gantt.png")
    return outpath


# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — ILP SUMMARY REPORT
# ─────────────────────────────────────────────────────────────────────────────

def write_ilp_summary(windows, scheduled, stats, station_load,
                       total_contact_s, max_gap_s, ilp_status,
                       n_windows, n_conflicts, n_pairs):
    outpath = os.path.join(OUTPUT_DIR, "11_ilp_summary.txt")

    all_max_gaps = [s["max_gap_s"] for s in stats.values()]
    all_contacts = [s["total_contact_s"] for s in stats.values()]

    with open(outpath, "w") as f:
        f.write("=" * 72 + "\n")
        f.write("SCENARIO 11 -- ILP FORMULATION AND RESULT SUMMARY\n")
        f.write("=" * 72 + "\n\n")

        f.write("PROBLEM FORMULATION\n")
        f.write("-" * 40 + "\n")
        f.write(f"  Decision variables (binary x_i) : {n_windows}\n")
        f.write(f"  Conflict constraints             : {n_conflicts}\n")
        f.write(f"  Gap linearisation pairs          : {n_pairs}\n")
        f.write(f"  Auxiliary gap variables (g_k)    : {n_pairs}\n")
        f.write(f"  Max-gap variable (G_max)         : 1\n")
        f.write(f"  Total variables                  : {n_windows + n_pairs + 1}\n\n")

        f.write("OBJECTIVE (weighted sum, maximised)\n")
        f.write("-" * 40 + "\n")
        f.write("  alpha * (sum contact_i * x_i)/100  -  beta * G_max/100\n")
        f.write(f"  alpha = {ALPHA}  (contact weight)\n")
        f.write(f"  beta  = {BETA}  (gap penalty weight -- beta > alpha: "
                f"gap minimisation prioritised)\n\n")

        f.write("CONSTRAINTS\n")
        f.write("-" * 40 + "\n")
        f.write("  1. Station exclusivity:\n")
        f.write("       x_i + x_j <= 1  for each conflict pair (i,j)\n")
        f.write("       (one antenna per station -- no simultaneous contacts)\n")
        f.write("  2. Gap linearisation (big-M, M = 86400 s):\n")
        f.write("       g_k >= gap_k * (x_i + x_j - 1)   [active if both selected]\n")
        f.write("       g_k <= gap_k * x_i\n")
        f.write("       g_k <= gap_k * x_j\n")
        f.write("  3. G_max >= g_k  for all k\n\n")

        f.write("SOLVER RESULT\n")
        f.write("-" * 40 + "\n")
        f.write(f"  Solver              : HiGHS (via PuLP 4.x)\n")
        f.write(f"  Status              : {ilp_status}\n")
        f.write(f"  Windows scheduled   : {len(scheduled)} / {n_windows}\n")
        f.write(f"  Total contact time  : {total_contact_s:.1f} s ({total_contact_s/3600:.3f} h)\n")
        f.write(f"  Worst-case gap      : {max_gap_s:.1f} s ({max_gap_s/3600:.3f} h)\n\n")

        f.write("FLEET-LEVEL STATISTICS\n")
        f.write("-" * 40 + "\n")
        f.write(f"  Mean contact per satellite  : {np.mean(all_contacts):.1f} s\n")
        f.write(f"  Min contact per satellite   : {np.min(all_contacts):.1f} s\n")
        f.write(f"  Max contact per satellite   : {np.max(all_contacts):.1f} s\n")
        f.write(f"  Mean max-gap per satellite  : {np.mean(all_max_gaps)/3600:.3f} h\n")
        f.write(f"  Worst max-gap (fleet)       : {np.max(all_max_gaps)/3600:.3f} h\n\n")

        f.write("GROUND STATION UTILISATION\n")
        f.write("-" * 40 + "\n")
        for st in STATIONS:
            load = station_load.get(st, 0)
            f.write(f"  {st:<10}: {load:.1f} s ({load/3600:.3f} h)\n")

    print(f"  ILP summary written to: 11_ilp_summary.txt")
    return outpath


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n=== Scenario 11 -- ILP Contact Scheduler ===\n")

    print("Step 1: Loading contact windows from Scenario 06 ...")
    windows = load_all_windows()

    print("Step 2: Building conflict graph ...")
    conflicts = find_conflicts(windows)

    print("Step 3: Building gap structure ...")
    sat_windows, consecutive_pairs = build_gap_structure(windows)

    print("Step 4: Solving ILP ...")
    scheduled, ilp_status, total_contact_s, max_gap_s = solve_ilp(
        windows, conflicts, sat_windows, consecutive_pairs)

    print("Step 5: Computing statistics ...")
    stats, station_load = compute_statistics(windows, scheduled, sat_windows)

    print("Step 6: Writing schedule output ...")
    write_schedule(windows, scheduled, stats, station_load,
                   total_contact_s, max_gap_s, ilp_status)

    print("Step 7: Generating Gantt chart ...")
    plot_gantt(windows, scheduled, stats)

    print("Step 8: Writing ILP summary ...")
    write_ilp_summary(windows, scheduled, stats, station_load,
                      total_contact_s, max_gap_s, ilp_status,
                      len(windows), len(conflicts), len(consecutive_pairs))

    print(f"\n=== DONE ===")
    print(f"  Scheduled {len(scheduled)} / {len(windows)} windows")
    print(f"  Total contact : {total_contact_s:.1f} s ({total_contact_s/3600:.2f} h)")
    print(f"  Worst gap     : {max_gap_s:.1f} s ({max_gap_s/3600:.2f} h)")


if __name__ == "__main__":
    main()
