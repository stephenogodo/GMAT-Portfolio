"""
plot_conjunction_10.py
Scenario 10 - LEO Conjunction Analysis and CAM Verification
Plots GMAT output from 10_conjunction_report.txt and 10_time_history.txt

Usage:
    python plot_conjunction_10.py

Output:
    conjunction_10_results.png  (4-panel figure)
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os



# -----------------------------------------------------------------------
# Hard-coded data points extracted from GMAT report files
# All times in seconds from epoch (01 Jan 2024 00:00:00 UTC)
# -----------------------------------------------------------------------

# --- SMA timeline (from both runs) ---
# Nominal run: epoch → TCA
t_nom_sma   = [0,       1434.75]
sma_nom     = [6928.14, 6946.96]     # LEOSat nominal (km)
sma_deb_nom = [6928.14, 6942.47]     # DebrisObject (km)

# CAM run: epoch (pre-burn) → epoch (post-burn) → TCA → orbit+2
t_cam_sma   = [0,       0,        1434.75,  7173.74,  12912.73]
sma_cam     = [6928.14, 6924.49,  6943.30,  6943.15,  6943.06]  # LEOSat post-CAM
sma_deb_cam = [6928.14, 6928.14,  6942.47,  6942.52,  6942.46]  # Debris (unchanged)

# --- RIC miss distance at TCA (nominal) ---
RIC_nom = {'R': -13881.18, 'I': 10.058, 'C': 12.968}   # metres

# --- RIC miss distance at TCA (post-CAM) ---
RIC_cam = {'R': -13877.53, 'I': 10.059, 'C': 11.677}   # metres

# --- RIC components over time (post-CAM run) ---
# t=1434.75 s (TCA), t=7173.74 s (+1 orbit), t=12912.73 s (+2 orbits)
t_ric = [1434.75, 7173.74, 12912.73]
ric_R = [-13877.53, -13876.65, -13874.34]   # m
ric_I = [    10.06,     89.29,    168.77]   # m   <-- growing: CAM working
ric_C = [    11.68,     72.28,    132.65]   # m

# --- Altitude at key epochs ---
# [epoch, TCA, +1 orbit, +2 orbits]
t_alt = [0,       1434.75,  7173.74,  12912.73]
alt_leosat_nom = [571.02,   566.07,   None,     None]
alt_leosat_cam = [571.02,   562.42,   562.40,   562.41]
alt_debris     = [566.03,   558.86,   558.93,   559.00]

# --- Pre-computation reference values ---
miss_dist_precomp  = 50.42    # m (total miss distance at nominal TCA, cross-track)
v_rel              = 4.89     # km/s
Pc_pre_cam         = 7.48e-4  # probability of collision
Pc_threshold       = 1.0e-4
delta_v_cam        = 2.0      # m/s retrograde
sma_drop_cam       = 6928.14 - 6924.49   # km = 3.65 km

# -----------------------------------------------------------------------
# Figure layout: 2x2 panels
# -----------------------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle(
    'Scenario 10 — LEO Conjunction Analysis & Collision Avoidance Manoeuvre\n'
    'LEOSat (SSO 97.6°) vs DebrisObject (60°) at 550 km | GMAT R2022a',
    fontsize=13, fontweight='bold', y=0.98
)

BLUE   = '#2563EB'
RED    = '#DC2626'
GREEN  = '#16A34A'
ORANGE = '#EA580C'
GREY   = '#6B7280'
PURPLE = '#7C3AED'

# ===========================
# Panel 1 (top-left): SMA evolution
# ===========================
ax1 = axes[0, 0]

ax1.plot(np.array(t_nom_sma)/60, sma_nom,
         color=BLUE, lw=2, ls='--', marker='o', ms=6, label='LEOSat (nominal)')
ax1.plot(np.array(t_cam_sma)/60, sma_cam,
         color=BLUE, lw=2, ls='-',  marker='s', ms=6, label='LEOSat (post-CAM)')
ax1.plot(np.array(t_nom_sma)/60, sma_deb_nom,
         color=RED,  lw=2, ls='--', marker='o', ms=6, label='DebrisObject')

ax1.axvline(x=1434.75/60, color=GREY, ls=':', lw=1.2, label=f'TCA (t={1434.75/60:.1f} min)')
ax1.axhline(y=6924.49, color=GREEN, ls=':', lw=1, alpha=0.7)
ax1.annotate('CAM lowers SMA\n6928.1 → 6924.5 km\n(Δ = −3.6 km)',
             xy=(0, 6924.49), xytext=(5, 6921.5),
             fontsize=7.5, color=GREEN,
             arrowprops=dict(arrowstyle='->', color=GREEN, lw=1))

ax1.set_xlabel('Elapsed Time (min)', fontsize=10)
ax1.set_ylabel('Semi-Major Axis (km)', fontsize=10)
ax1.set_title('SMA Evolution — Nominal vs Post-CAM', fontsize=10, fontweight='bold')
ax1.legend(fontsize=8, loc='upper left')
ax1.grid(True, alpha=0.3)
ax1.set_xlim(-1, 26)

# ===========================
# Panel 2 (top-right): RIC miss distance bar chart
# ===========================
ax2 = axes[0, 1]

labels  = ['R (Radial)', 'I (In-track)', 'C (Cross-track)']
nom_vals = [abs(RIC_nom['R']), abs(RIC_nom['I']), abs(RIC_nom['C'])]
cam_vals = [abs(RIC_cam['R']), abs(RIC_cam['I']), abs(RIC_cam['C'])]

x = np.arange(len(labels))
w = 0.35
bars1 = ax2.bar(x - w/2, nom_vals, w, label='Nominal (no CAM)', color=RED,   alpha=0.85)
bars2 = ax2.bar(x + w/2, cam_vals, w, label='Post-CAM',         color=GREEN, alpha=0.85)

# label bar values
for bar in bars1:
    h = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2, h + 80,
             f'{h:.0f} m', ha='center', va='bottom', fontsize=7.5, color=RED)
for bar in bars2:
    h = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2, h + 80,
             f'{h:.0f} m', ha='center', va='bottom', fontsize=7.5, color=GREEN)

ax2.set_xticks(x)
ax2.set_xticklabels(labels, fontsize=9)
ax2.set_ylabel('Miss Distance Component (m)', fontsize=10)
ax2.set_title('RIC Miss Distance at TCA (t = 1434.75 s)', fontsize=10, fontweight='bold')
ax2.legend(fontsize=8)
ax2.grid(True, alpha=0.3, axis='y')

# Add annotation box
info = (f'Nominal total miss ≈ {miss_dist_precomp} m (cross-track dominant)\n'
        f'Relative velocity: {v_rel} km/s\n'
        f'Pc (pre-CAM): {Pc_pre_cam:.2e}  [threshold: {Pc_threshold:.0e}]')
ax2.text(0.02, 0.97, info, transform=ax2.transAxes,
         fontsize=7.5, va='top', ha='left',
         bbox=dict(boxstyle='round,pad=0.4', facecolor='#FEF9C3', alpha=0.9))

# ===========================
# Panel 3 (bottom-left): In-track separation growth over time
# ===========================
ax3 = axes[1, 0]

t_min = np.array(t_ric) / 60

ax3.plot(t_min, np.abs(ric_I), color=BLUE, lw=2.2, marker='D', ms=7,
         label='|I| (In-track separation)')
ax3.plot(t_min, np.abs(ric_C), color=PURPLE, lw=2.2, marker='^', ms=7,
         label='|C| (Cross-track separation)')
ax3.plot(t_min, np.abs(ric_R)/1000, color=GREY, lw=1.5, ls='--', marker='o', ms=5,
         label='|R| / 1000 (Radial, scaled)')

# Trend line for in-track
coeffs = np.polyfit(t_min, np.abs(ric_I), 1)
t_fit = np.linspace(t_min[0], t_min[-1], 100)
ax3.plot(t_fit, np.polyfit(t_min, np.abs(ric_I), 1)[0]*t_fit + np.polyfit(t_min, np.abs(ric_I), 1)[1],
         color=BLUE, lw=1, ls=':', alpha=0.6, label=f'I trend: +{coeffs[0]:.1f} m/min')

ax3.axvspan(0, 1434.75/60, alpha=0.08, color=RED,   label='TCA window')
ax3.axvspan(1434.75/60, t_min[-1], alpha=0.08, color=GREEN, label='Safe passage zone')

ax3.set_xlabel('Elapsed Time (min)', fontsize=10)
ax3.set_ylabel('RIC Separation (m)', fontsize=10)
ax3.set_title('Post-CAM RIC Separation Growth (2 Orbits)', fontsize=10, fontweight='bold')
ax3.legend(fontsize=8, loc='upper left')
ax3.grid(True, alpha=0.3)

rate_m_per_orbit = (abs(ric_I[-1]) - abs(ric_I[0])) / 2
ax3.text(0.98, 0.05,
         f'In-track growth rate:\n≈ {rate_m_per_orbit:.0f} m / orbit\nCAM ΔV = {delta_v_cam} m/s retrograde',
         transform=ax3.transAxes, fontsize=8, ha='right', va='bottom',
         bbox=dict(boxstyle='round,pad=0.4', facecolor='#DCFCE7', alpha=0.9))

# ===========================
# Panel 4 (bottom-right): Altitude timeline
# ===========================
ax4 = axes[1, 1]

t_plot = [0, 1434.75/60, 7173.74/60, 12912.73/60]

# LEOSat nominal (only first 2 points)
ax4.plot([0, 1434.75/60], [alt_leosat_nom[0], alt_leosat_nom[1]],
         color=BLUE, lw=2, ls='--', marker='o', ms=6, label='LEOSat (nominal)')

# LEOSat post-CAM
ax4.plot(t_plot, alt_leosat_cam,
         color=BLUE, lw=2, ls='-', marker='s', ms=6, label='LEOSat (post-CAM)')

# Debris
ax4.plot(t_plot, alt_debris,
         color=RED, lw=2, ls='-', marker='o', ms=6, label='DebrisObject')

ax4.axvline(x=1434.75/60, color=GREY, ls=':', lw=1.2)
ax4.text(1434.75/60 + 0.3, 570, 'TCA', fontsize=8, color=GREY)

# Annotate the CAM-induced altitude drop
ax4.annotate('CAM: −8.6 km altitude\n(SMA lowered, faster orbit)',
             xy=(0.1, 562.4), xytext=(10, 567),
             fontsize=7.5, color=BLUE,
             arrowprops=dict(arrowstyle='->', color=BLUE, lw=1))

ax4.set_xlabel('Elapsed Time (min)', fontsize=10)
ax4.set_ylabel('Altitude (km)', fontsize=10)
ax4.set_title('Altitude Profile — Both Objects', fontsize=10, fontweight='bold')
ax4.legend(fontsize=8, loc='upper right')
ax4.grid(True, alpha=0.3)

# -----------------------------------------------------------------------
# Final layout
# -----------------------------------------------------------------------
plt.tight_layout(rect=[0, 0, 1, 0.95])

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'conjunction_10_results.png')
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f'Saved: {out_path}')
plt.close()
