"""
plot_ewsk_09b.py  -- XY station-keeping plot for NigComSat-1R EWSK Scenario 09b
Run AFTER GMAT produces:
  C:\\Users\\Admin\\GMAT_Tutorials\\GMAT_portfolio\\09_scenario_EWSK\\09b_geo_ewsk_report.txt

Usage:
  python plot_ewsk_09b.py

Output:
  09b_ewsk_XYplot.png  (same folder as the report)

Scenario 09b: Two-burn full operational EWSK cycle
  Burn 1: day 1.5  (11s prograde, east trigger 42.53 degE)
  Phase 1: 15-day westward coast arc
  Burn 2: day ~16.5  (7s prograde, east trigger 42.53 degE, SMA-matched)
  Phase 2: 17-day eastward arc back to 42.53 degE
  Total scenario: ~33.5 days
  Compliance: full scenario day 0 to end -- both burns inside deadband
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ---- Path to GMAT report -----------------------------------------------
REPORT = (
    r'C:\Users\Admin\Documents\Projects\GMAT_portfolio'
    r'\09_scenario_EWSK\scenario_08b_geo_ewsk\09b_geo_ewsk_report.txt'
)
OUT_PNG = os.path.join(os.path.dirname(REPORT), '09b_ewsk_XYplot.png')

# ---- Deadband / trigger constants --------------------------------------
SLOT         = 42.50
EAST_LIMIT   = 42.55
WEST_LIMIT   = 42.45
EAST_TRIGGER = 42.53
WEST_TRIGGER = 42.47

# ---- Compliance: full scenario from day 0 ------------------------------
COMPLIANCE_START = 0.0

# ---- Parse report -------------------------------------------------------
def parse_report(path):
    days, lons, smas, fuels = [], [], [], []
    epoch_dt = None
    from datetime import datetime
    with open(path, 'r') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith('SC.'):
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            try:
                date_str = ' '.join(parts[:4])
                dt = datetime.strptime(date_str, '%d %b %Y %H:%M:%S.%f')
                if epoch_dt is None:
                    epoch_dt = dt
                elapsed = (dt - epoch_dt).total_seconds() / 86400.0
                lon  = float(parts[4])
                sma  = float(parts[6])
                fuel = float(parts[8])
                days.append(elapsed)
                lons.append(lon)
                smas.append(sma)
                fuels.append(fuel)
            except (ValueError, IndexError):
                continue
    return (np.array(days), np.array(lons),
            np.array(smas), np.array(fuels))

# ---- Identify burn events from FuelMass drops ---------------------------
def find_burns(days, fuels):
    burns = []
    for i in range(1, len(fuels)):
        if fuels[i-1] - fuels[i] > 0.03:
            burns.append(days[i])
    return burns

# ---- 24-hour rolling mean longitude -------------------------------------
def rolling_mean(days, lons, window_days=1.0):
    m_days, m_lons = [], []
    for i, d in enumerate(days):
        mask = (days >= d - window_days/2) & (days <= d + window_days/2)
        if mask.sum() >= 3:
            m_days.append(d)
            m_lons.append(lons[mask].mean())
    return np.array(m_days), np.array(m_lons)

# ---- Main ---------------------------------------------------------------
if not os.path.exists(REPORT):
    sys.exit(f"ERROR: report not found:\n  {REPORT}\nRun GMAT Scenario 09b first.")

days, lons, smas, fuels = parse_report(REPORT)
if len(days) < 2:
    sys.exit("ERROR: could not parse report data.")

burn_days = find_burns(days, fuels)
m_days, m_lons = rolling_mean(days, lons)

burn_lons = []
for bd in burn_days:
    idx = np.argmin(np.abs(days - bd))
    burn_lons.append(lons[idx])

# ---- Compliance check (mean longitude, full scenario) ------------------
mask_m = m_days >= COMPLIANCE_START
if mask_m.sum() > 0:
    sk_compliant = (m_lons[mask_m].min() >= WEST_LIMIT) and \
                   (m_lons[mask_m].max() <= EAST_LIMIT)
else:
    sk_compliant = False

# ---- Figure ------------------------------------------------------------
fig, ax = plt.subplots(figsize=(16, 7))
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#161b22')

# Deadband green band
ax.axhspan(WEST_LIMIT, EAST_LIMIT, color='#1a3a1a', alpha=0.5, zorder=1)

# Compliance window green tint (full scenario)
total_days = days[-1] if len(days) > 0 else 35.0
xmax = max(35, total_days + 1)
ax.axvspan(0, xmax, color='#238636', alpha=0.07, zorder=0,
           label='Compliance window (day 0 to end)')

# Deadband limits
ax.axhline(EAST_LIMIT, color='#ff4444', lw=1.8, ls='--', zorder=3,
           label=f'East limit {EAST_LIMIT:.2f} degE')
ax.axhline(WEST_LIMIT, color='#ff4444', lw=1.8, ls='--', zorder=3,
           label=f'West limit {WEST_LIMIT:.2f} degE')

# Operational triggers
ax.axhline(EAST_TRIGGER, color='#ffaa00', lw=1.2, ls=':', zorder=3,
           label=f'East trigger {EAST_TRIGGER:.2f} degE')
ax.axhline(WEST_TRIGGER, color='#aaddff', lw=1.2, ls=':', zorder=3,
           label=f'West trigger {WEST_TRIGGER:.2f} degE')

# Slot centre
ax.axhline(SLOT, color='#44aaff', lw=0.8, ls='-', alpha=0.5, zorder=2,
           label=f'Assigned slot {SLOT:.2f} degE')

# Instantaneous longitude
ax.plot(days, lons, color='#4fc3f7', lw=0.8, alpha=0.65, zorder=4,
        label='Instantaneous longitude')

# 24-hr mean longitude
if len(m_days) > 0:
    ax.plot(m_days, m_lons, color='#ffffff', lw=2.0, zorder=5,
            label='24-hr mean longitude')

# Burn markers
burn_labels = [
    f'Burn 1 (11s prograde, day {burn_days[0]:.2f}, east trigger 42.53 degE)' if len(burn_days) > 0 else None,
    f'Burn 2 (7s prograde, day {burn_days[1]:.2f}, east trigger 42.53 degE, SMA-matched)' if len(burn_days) > 1 else None,
]
for i, (bd, bl) in enumerate(zip(burn_days, burn_lons), 1):
    lbl = burn_labels[i-1] if i <= len(burn_labels) else None
    ax.axvline(bd, color='#ff9800', lw=1.5, ls='-', alpha=0.8, zorder=6)
    ax.plot(bd, bl, 'v', color='#ff9800', ms=11, zorder=7, label=lbl)
    dur_label = '11s' if i == 1 else '7s'
    ax.annotate(f'B{i}\n{dur_label}',
                xy=(bd, bl), xytext=(bd + 0.2, bl + 0.004),
                color='#ff9800', fontsize=9, fontweight='bold', zorder=8)

# Axes
ax.set_xlim(0, xmax)
ax.set_ylim(WEST_LIMIT - 0.015, EAST_LIMIT + 0.015)
ax.set_xlabel('Elapsed Days', color='#c9d1d9', fontsize=12)
ax.set_ylabel('Earth Longitude (deg E)', color='#c9d1d9', fontsize=12)
ax.set_title(
    'NigComSat-1R @ 42.5 degE  |  GEO East-West Station-Keeping  |  GMAT Scenario 09b\n'
    'Full Operational Cycle: Burn 1 (11s) + Burn 2 (7s, SMA-matched) prograde  |  '
    'Deadband +/-0.05 deg  |  Slot: 42.5 degE',
    color='#e6edf3', fontsize=13, pad=12)
ax.tick_params(colors='#8b949e')
for spine in ax.spines.values():
    spine.set_edgecolor('#30363d')

ax.grid(True, color='#21262d', lw=0.7, ls='--', zorder=0)
x_ticks = list(range(0, int(xmax) + 1, 5))
ax.set_xticks(x_ticks)
ax.set_xticklabels([f'Day {d}' for d in x_ticks], color='#8b949e', fontsize=9)

yticks = [42.45, 42.47, 42.49, 42.50, 42.51, 42.53, 42.55]
ax.set_yticks(yticks)
ax.set_yticklabels([f'{y:.2f} degE' for y in yticks], color='#8b949e', fontsize=9)

ax.legend(loc='upper right', framealpha=0.85, facecolor='#161b22',
          edgecolor='#30363d', labelcolor='#c9d1d9', fontsize=9)

# Compliance badge
badge_color = '#238636' if sk_compliant else '#da3633'
badge_text  = 'SK ARC COMPLIANT' if sk_compliant else 'VIOLATION DETECTED'
ax.text(0.99, 0.06, badge_text,
        transform=ax.transAxes, ha='right', va='bottom',
        color='white', fontsize=11, fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.4', facecolor=badge_color, alpha=0.9),
        zorder=9)

plt.tight_layout()
plt.savefig(OUT_PNG, dpi=150, bbox_inches='tight',
            facecolor=fig.get_facecolor())
plt.close()
print(f"Plot saved: {OUT_PNG}")

# ---- Statistics --------------------------------------------------------
print(f"\nReport statistics ({len(days)} data points):")
print(f"  Epoch lon   : {lons[0]:.4f} degE")
print(f"  Min lon     : {lons.min():.4f} degE  {'PASS' if lons.min()>=WEST_LIMIT else 'FAIL'}")
print(f"  Max lon     : {lons.max():.4f} degE  {'PASS' if lons.max()<=EAST_LIMIT else 'FAIL'}")
if len(m_lons) > 0:
    print(f"  Min mean lon: {m_lons.min():.4f} degE  {'PASS' if m_lons.min()>=WEST_LIMIT else 'FAIL'}")
    print(f"  Max mean lon: {m_lons.max():.4f} degE  {'PASS' if m_lons.max()<=EAST_LIMIT else 'FAIL'}")
print(f"  End lon     : {lons[-1]:.4f} degE  (day {days[-1]:.2f})")
print(f"  Fuel start  : {fuels[0]:.4f} kg")
print(f"  Fuel end    : {fuels[-1]:.4f} kg")
print(f"  Fuel used   : {fuels[0]-fuels[-1]:.4f} kg")
print(f"  Burns found : {len(burn_days)} at days {[f'{b:.3f}' for b in burn_days]}")
print(f"\nCompliance (mean lon, day 0 to end):")
if mask_m.sum() > 0:
    print(f"  Min mean lon: {m_lons[mask_m].min():.4f} degE  {'PASS' if m_lons[mask_m].min()>=WEST_LIMIT else 'FAIL'}")
    print(f"  Max mean lon: {m_lons[mask_m].max():.4f} degE  {'PASS' if m_lons[mask_m].max()<=EAST_LIMIT else 'FAIL'}")
print(f"\nResult: {'PASS -- Full SK cycle within deadband' if sk_compliant else 'FAIL -- deadband violated'}")
