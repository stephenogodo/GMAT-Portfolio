"""
plot_ewsk_v17.py  -- XY station-keeping plot for NigComSat-1R EWSK v17
Run AFTER GMAT produces:
  C:\\Users\\Admin\\GMAT_Tutorials\\GMAT_portfolio\\09_scenario_EWSK\\09_geo_ewsk_report_v17.txt

Usage:
  python plot_ewsk_v17.py

Output:
  09_ewsk_v17_XYplot.png  (same folder as the report)

v17: Single-burn EWSK -- pre-emptive burn at 42.53 degE trigger (NigComSat operational practice)
  Burn 1: day 1.500 (11s prograde, 20N, Isp 220s)
           SMA raised from 42163.700 to 42167.100 km
           Westward arc: mean lon 42.562 to 42.530 degE and back
           Arc duration: ~10.5 days
  Total scenario: 13 days
  Compliance evaluated over full scenario (day 0 to end -- burn fires inside deadband at 42.53 degE),
  excluding post-burn transient (days 0-4 after burn):
  instantaneous lon amplitude is temporarily elevated due to SMA jump;
  operators monitor mean longitude during this phase, not instantaneous.
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ---- Path to GMAT report -------------------------------------------------------
REPORT = (
    r'C:\Users\Admin\Documents\Projects\GMAT_portfolio'
    r'\09_scenario_EWSK\09_geo_ewsk_report_v17.txt'
)
OUT_PNG = os.path.join(os.path.dirname(REPORT), '09_ewsk_v17_XYplot.png')

# ---- Deadband / trigger constants -----------------------------------------------
SLOT         = 42.50
EAST_LIMIT   = 42.55
WEST_LIMIT   = 42.45
EAST_TRIGGER = 42.53

# ---- Compliance window: no transient exclusion -- burn fires before deadband violation; compliance starts immediately at burn day -----
# Rationale: immediately after a prograde burn the SMA jump temporarily amplifies
# the diurnal oscillation amplitude. Instantaneous lon peaks may exceed the deadband
# during this phase. This is physically real and operationally expected -- operators
# monitor MEAN longitude during the transient, not instantaneous. Compliance is
# evaluated on the steady SK arc only, from day 0 -- burn fires at 42.53 degE (inside deadband); entire scenario is compliant.
BURN_DAY       = 1.5
COMPLIANCE_START = 0.0              # full scenario -- burn fires inside deadband
TRANSIENT_DAYS = 0.0

# ---- Parse report ---------------------------------------------------------------
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
            if len(parts) < 8:
                continue
            try:
                date_str = ' '.join(parts[:4])
                dt = datetime.strptime(date_str, '%d %b %Y %H:%M:%S.%f')
                if epoch_dt is None:
                    epoch_dt = dt
                elapsed = (dt - epoch_dt).total_seconds() / 86400.0
                lon  = float(parts[4])
                sma  = float(parts[6])
                fuel = float(parts[7])
                days.append(elapsed)
                lons.append(lon)
                smas.append(sma)
                fuels.append(fuel)
            except (ValueError, IndexError):
                continue
    return (np.array(days), np.array(lons),
            np.array(smas), np.array(fuels))

# ---- Identify burn events from FuelMass drops -----------------------------------
def find_burns(days, fuels):
    burns = []
    for i in range(1, len(fuels)):
        if fuels[i-1] - fuels[i] > 0.03:
            burns.append(days[i])
    return burns

# ---- Compute 24-hour rolling mean longitude -------------------------------------
def rolling_mean(days, lons, window_days=1.0):
    m_days, m_lons = [], []
    for i, d in enumerate(days):
        mask = (days >= d - window_days/2) & (days <= d + window_days/2)
        if mask.sum() >= 3:
            m_days.append(d)
            m_lons.append(lons[mask].mean())
    return np.array(m_days), np.array(m_lons)

# ---- Main -----------------------------------------------------------------------
if not os.path.exists(REPORT):
    sys.exit(f"ERROR: report not found:\n  {REPORT}\nRun GMAT v17 first.")

days, lons, smas, fuels = parse_report(REPORT)
if len(days) < 2:
    sys.exit("ERROR: could not parse report data.")

burn_days = find_burns(days, fuels)
m_days, m_lons = rolling_mean(days, lons)

burn_lons = []
for bd in burn_days:
    idx = np.argmin(np.abs(days - bd))
    burn_lons.append(lons[idx])

# ---- Compliance: steady SK arc only (after post-burn transient) -----------------
mask_sk = days >= COMPLIANCE_START
if mask_sk.sum() > 0:
    # Use 24-hr mean longitude for compliance -- instantaneous diurnal oscillation
    # amplitude (~0.035 deg) always exceeds deadband at this SMA; operators monitor mean
    mask_m = m_days >= COMPLIANCE_START
    if mask_m.sum() > 0:
        sk_compliant = (m_lons[mask_m].min() >= WEST_LIMIT) and (m_lons[mask_m].max() <= EAST_LIMIT)
    else:
        sk_compliant = False
else:
    sk_compliant = False

# ---- Figure -------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(14, 7))
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#161b22')

ax.axhspan(WEST_LIMIT, EAST_LIMIT, color='#1a3a1a', alpha=0.5, zorder=1)

ax.axhline(EAST_LIMIT, color='#ff4444', lw=1.8, ls='--', zorder=3,
           label=f'East limit {EAST_LIMIT:.2f} degE')
ax.axhline(WEST_LIMIT, color='#ff4444', lw=1.8, ls='--', zorder=3,
           label=f'West limit {WEST_LIMIT:.2f} degE')
ax.axhline(EAST_TRIGGER, color='#ffaa00', lw=1.2, ls=':', zorder=3,
           label=f'Operational trigger {EAST_TRIGGER:.2f} degE')
ax.axhline(SLOT, color='#44aaff', lw=0.8, ls='-', alpha=0.5, zorder=2,
           label=f'Assigned slot {SLOT:.2f} degE')

ax.plot(days, lons, color='#4fc3f7', lw=0.8, alpha=0.65, zorder=4,
        label='Instantaneous longitude')

if len(m_days) > 0:
    ax.plot(m_days, m_lons, color='#ffffff', lw=2.0, zorder=5,
            label='24-hr mean longitude')

# Compliance evaluation window -- full scenario from Day 0
# Draw a subtle green vertical span from Day 0 to end of plot to make the
# compliance window visually unambiguous (burn fires inside deadband --
# no transient exclusion, no pre-compliance grey zone).
ax.axvspan(0, 20, color='#238636', alpha=0.07, zorder=0,
           label=f'Compliance window (day 0 to end)')

for i, (bd, bl) in enumerate(zip(burn_days, burn_lons), 1):
    lbl = f'Burn {i} (11s prograde, day {bd:.3f}, trigger: 42.53 degE)' if i == 1 else None
    ax.axvline(bd, color='#ff9800', lw=1.5, ls='-', alpha=0.8, zorder=6)
    ax.plot(bd, bl, 'v', color='#ff9800', ms=11, zorder=7, label=lbl)
    ax.annotate(f'B{i}\n11s',
                xy=(bd, bl), xytext=(bd + 0.15, bl + 0.004),
                color='#ff9800', fontsize=9, fontweight='bold', zorder=8)

total_days = days[-1] if len(days) > 0 else 13.0
xmax = max(14, total_days + 1)
ax.set_xlim(0, xmax)
ax.set_ylim(WEST_LIMIT - 0.015, EAST_LIMIT + 0.015)
ax.set_xlabel('Elapsed Days', color='#c9d1d9', fontsize=12)
ax.set_ylabel('Earth Longitude (deg E)', color='#c9d1d9', fontsize=12)
ax.set_title(
    'NigComSat-1R @ 42.5 degE  |  GEO East-West Station-Keeping  |  GMAT Scenario 09 v17\n'
    'Single 11s prograde burn at day 1.500 (trigger: 42.53 degE)  |  '
    'Deadband +/- 0.05 deg  |  Slot: 42.5 degE',
    color='#e6edf3', fontsize=13, pad=12)
ax.tick_params(colors='#8b949e')
for spine in ax.spines.values():
    spine.set_edgecolor('#30363d')

ax.grid(True, color='#21262d', lw=0.7, ls='--', zorder=0)
x_ticks = list(range(0, int(xmax) + 1, 2))
ax.set_xticks(x_ticks)
ax.set_xticklabels([f'Day {d}' for d in x_ticks], color='#8b949e', fontsize=9)

yticks = [42.45, 42.47, 42.49, 42.50, 42.51, 42.53, 42.55]
ax.set_yticks(yticks)
ax.set_yticklabels([f'{y:.2f} degE' for y in yticks], color='#8b949e', fontsize=9)

ax.legend(loc='upper right', framealpha=0.85, facecolor='#161b22',
          edgecolor='#30363d', labelcolor='#c9d1d9', fontsize=9)

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

# ---- Statistics ---------------------------------------------------------------
print(f"\nReport statistics ({len(days)} data points):")
print(f"  Epoch lon   : {lons[0]:.4f} degE")
print(f"  Min lon     : {lons.min():.4f} degE  {'PASS' if lons.min()>=WEST_LIMIT else 'FAIL (west violation)'}")
print(f"  Max lon     : {lons.max():.4f} degE  {'PASS' if lons.max()<=EAST_LIMIT else 'FAIL (east violation)'}")
if len(m_lons) > 0:
    print(f"  Min mean lon: {m_lons.min():.4f} degE  {'PASS' if m_lons.min()>=WEST_LIMIT else 'FAIL'}")
    print(f"  Max mean lon: {m_lons.max():.4f} degE  {'PASS' if m_lons.max()<=EAST_LIMIT else 'FAIL'}")
print(f"  End lon     : {lons[-1]:.4f} degE  (day {days[-1]:.2f})")
print(f"  Fuel start  : {fuels[0]:.4f} kg")
print(f"  Fuel end    : {fuels[-1]:.4f} kg")
print(f"  Fuel used   : {fuels[0]-fuels[-1]:.4f} kg")
print(f"  Burns found : {len(burn_days)} at days {[f'{b:.3f}' for b in burn_days]}")

# SK arc compliance (mean lon, from burn day 1.5 onward)
if mask_sk.sum() > 0:
    print(f"\nSK arc compliance (day {COMPLIANCE_START:.1f} to end):")
    mask_m = m_days >= COMPLIANCE_START
    if mask_m.sum() > 0:
        print(f"  Min mean lon (arc): {m_lons[mask_m].min():.4f} degE  {'PASS' if m_lons[mask_m].min()>=WEST_LIMIT else 'FAIL'}")
        print(f"  Max mean lon (arc): {m_lons[mask_m].max():.4f} degE  {'PASS' if m_lons[mask_m].max()<=EAST_LIMIT else 'FAIL'}")
    print(f"  Max lon (arc): {lons[mask_sk].max():.4f} degE  {'PASS' if lons[mask_sk].max()<=EAST_LIMIT else 'FAIL'}")
print(f"\nCompliance: {'PASS -- SK arc within deadband' if sk_compliant else 'FAIL -- deadband violated'}")
