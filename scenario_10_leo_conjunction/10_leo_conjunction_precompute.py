"""
Scenario 10 - LEO Conjunction Analysis and Collision Avoidance Maneuver
Pre-computation script: orbital geometry, TCA, Pc, and CAM sizing

Author: Stephen Ogodo
Date:   2024-Jan-01
"""

import numpy as np
import sys
import os

# ============================================================
# Report file setup — all terminal output mirrored to file
# ============================================================
_report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '10_precompute_report.txt')

class _Tee:
    """Write to both stdout and a file simultaneously."""
    def __init__(self, *streams):
        self._streams = streams
    def write(self, data):
        for s in self._streams:
            s.write(data)
    def flush(self):
        for s in self._streams:
            s.flush()

_report_file = open(_report_path, 'w', encoding='utf-8')
sys.stdout = _Tee(sys.__stdout__, _report_file)

print("=" * 70)
print("Scenario 10 - LEO Conjunction Analysis & CAM Pre-computation")
print("=" * 70)

# ============================================================
# Orbital parameters
# ============================================================
mu      = 398600.4418   # km^3/s^2 (Earth GM)
R_earth = 6378.137      # km
h_orbit = 550.0         # km
a       = R_earth + h_orbit   # SMA [km]

V       = np.sqrt(mu / a)          # Circular velocity [km/s]
T_p     = 2 * np.pi * np.sqrt(a**3 / mu)  # Orbital period [s]

inc_p   = 97.6   # deg  -- primary (SSO)
inc_d   = 60.0   # deg  -- debris
RAAN_p  = 45.0   # deg
delta_RAAN = 0.000417  # deg  (50 m cross-track miss distance)
RAAN_d  = RAAN_p + delta_RAAN

print(f"\n--- Orbit Parameters ---")
print(f"  SMA        = {a:.4f} km")
print(f"  Altitude   = {h_orbit:.1f} km")
print(f"  V_circ     = {V:.4f} km/s")
print(f"  T_period   = {T_p:.3f} s  ({T_p/60:.2f} min)")

# ============================================================
# TCA geometry
# ============================================================
# Both objects cross u=0 after T_p/4 from their starting positions
# Primary: TA=90 -> travels 270 deg of arc ... wait, TA=90 -> u=0 is 270 deg away
# Actually: starting at TA=90 (u=90), crossing at u=0 means travelling -90 deg
# i.e., T_p * 90/360 = T_p/4
TCA_t = T_p / 4.0   # seconds

print(f"\n--- Conjunction Geometry ---")
print(f"  Primary inc     = {inc_p} deg  (SSO)")
print(f"  Debris inc      = {inc_d} deg")
print(f"  Delta_inc       = {inc_p - inc_d:.1f} deg")
print(f"  RAAN_primary    = {RAAN_p:.6f} deg")
print(f"  RAAN_debris     = {RAAN_d:.6f} deg")
print(f"  Delta_RAAN      = {delta_RAAN:.6f} deg")
print(f"  TCA time        = {TCA_t:.3f} s  (T_p/4)")

# ============================================================
# Relative velocity at crossing
# ============================================================
# Both objects on circular orbits at same altitude -> same |V|
# Velocity vectors: at u=0 (ascending node):
#   V_p = V * [0, cos(inc_p), sin(inc_p)]  in (x,y,z) ECEF-like at node
#   V_d = V * [0, cos(inc_d), sin(inc_d)]
# (assuming same RAAN ~ 45 deg, difference is only inclination)
inc_p_rad = np.radians(inc_p)
inc_d_rad = np.radians(inc_d)

V_p_vec = V * np.array([0.0, np.cos(inc_p_rad), np.sin(inc_p_rad)])
V_d_vec = V * np.array([0.0, np.cos(inc_d_rad), np.sin(inc_d_rad)])

dV_rel = V_p_vec - V_d_vec
V_rel  = np.linalg.norm(dV_rel)

print(f"\n--- Relative Velocity at Crossing ---")
print(f"  |V_p| = |V_d|  = {V:.4f} km/s")
print(f"  V_rel          = {V_rel:.4f} km/s")

# ============================================================
# Miss distance from RAAN offset
# ============================================================
delta_RAAN_rad = np.radians(delta_RAAN)
d_miss = a * delta_RAAN_rad   # km

print(f"\n--- Miss Distance ---")
print(f"  delta_RAAN     = {delta_RAAN:.6f} deg  = {delta_RAAN_rad:.8f} rad")
print(f"  d_miss         = {d_miss*1000:.2f} m  ({d_miss:.6f} km)")

# ============================================================
# Probability of Collision -- Foster 2D method
# ============================================================
R_p   = 5.0     # m  -- primary hard-body radius estimate (satellite ~10 m body, half-size)
R_d   = 0.1     # m  -- debris fragment radius
R_HB  = R_p + R_d   # combined hard-body radius [m]

sigma_p = 50.0  # m  (1-sigma position uncertainty, primary)
sigma_d = 50.0  # m  (1-sigma position uncertainty, debris)
sigma   = np.sqrt(sigma_p**2 + sigma_d**2)   # combined [m]

d_m    = d_miss * 1000.0  # miss distance in metres

# A_HB = pi * R_HB^2  (hard-body cross-section area, m^2)
A_HB   = np.pi * R_HB**2

# Pc = A_HB / (2*pi*sigma^2) * exp(-d^2 / (2*sigma^2))
Pc     = (A_HB / (2 * np.pi * sigma**2)) * np.exp(-d_m**2 / (2 * sigma**2))

print(f"\n--- Probability of Collision (Foster 2D method) ---")
print(f"  R_primary  = {R_p:.1f} m")
print(f"  R_debris   = {R_d:.1f} m")
print(f"  R_HB       = {R_HB:.1f} m")
print(f"  A_HB       = {A_HB:.4f} m^2")
print(f"  sigma_p    = {sigma_p:.1f} m")
print(f"  sigma_d    = {sigma_d:.1f} m")
print(f"  sigma_comb = {sigma:.4f} m")
print(f"  d_miss     = {d_m:.2f} m")
print(f"  Pc         = {Pc:.4e}")

Pc_threshold = 1.0e-4
print(f"  Threshold  = {Pc_threshold:.1e}")
if Pc > Pc_threshold:
    print(f"  RESULT: Pc > threshold -- CAM WARRANTED")
else:
    print(f"  RESULT: Pc < threshold -- No CAM required")

# ============================================================
# CAM sizing (Clohessy-Wiltshire approximation)
# ============================================================
dV_cam   = 0.002   # km/s  (retrograde)
n        = 2 * np.pi / T_p   # mean motion [rad/s]
T_coast  = TCA_t              # coast time to TCA [s]

# In-track separation from retrograde burn via CW solution:
# delta_I(t) = -(2*dV/n) + 1.5*n*dV*t ... approximation for t << T_p
# More precise: delta_I(t) ~ (2*dV/n)*(1 - cos(n*t)) + (3*dV)*t ... but simpler:
# For a prograde/retrograde burn dV at epoch, in-track drift (CW):
# x(t) = -(2*dV/n)*sin(n*t)   (radial)
# y(t) = -(2*dV/n)*(cos(n*t) - 1) - (3*dV/2)*t  -- wait, sign convention
# Using standard CW (negative dV = retrograde means dV < 0 in along-track):
# delta_y = -3/2 * n * delta_x0 * t  ... from SMA change
# SMA change: delta_a = -2*a*dV/V  (retrograde burn)
# In-track drift: delta_I = 3/2 * n * |delta_a| * t

delta_a  = 2 * a * dV_cam / V   # SMA change magnitude [km] (retrograde -> lower SMA)
delta_I  = 1.5 * n * delta_a * T_coast   # in-track separation at TCA [km]

print(f"\n--- CAM Parameters ---")
print(f"  Burn magnitude  = {dV_cam*1000:.1f} m/s  (retrograde at epoch)")
print(f"  Coast time      = {T_coast:.2f} s  (to TCA)")
print(f"  Delta_SMA       = {delta_a:.4f} km  (retrograde lowers SMA)")
print(f"  Mean motion n   = {n*1000:.6f} mrad/s")
print(f"  In-track sep    = {delta_I*1000:.1f} m  at TCA")
print(f"  In-track sep    = {delta_I:.4f} km  at TCA")

# Post-CAM miss distance (dominated by in-track)
d_post_cam = np.sqrt(d_m**2 + (delta_I*1000)**2)   # metres
Pc_post    = (A_HB / (2 * np.pi * sigma**2)) * np.exp(-d_post_cam**2 / (2 * sigma**2))

print(f"\n--- Post-CAM Assessment ---")
print(f"  Cross-track miss   = {d_m:.1f} m  (unchanged)")
print(f"  In-track sep added = {delta_I*1000:.1f} m")
print(f"  Total miss dist    = {d_post_cam:.1f} m")
print(f"  Post-CAM Pc        = {Pc_post:.4e}")
print(f"  Threshold          = {Pc_threshold:.1e}")
if Pc_post < Pc_threshold:
    print(f"  RESULT: Pc << threshold -- SAFE PASSAGE CONFIRMED")
else:
    print(f"  RESULT: WARNING: Pc still above threshold")

# ============================================================
# GMAT Parameter Summary
# ============================================================
print(f"\n{'=' * 70}")
print(f"GMAT Script Parameters")
print(f"{'=' * 70}")
print(f"  LEOSat.SMA   = {a:.4f}")
print(f"  LEOSat.ECC   = 0.0001")
print(f"  LEOSat.INC   = {inc_p:.4f}")
print(f"  LEOSat.RAAN  = {RAAN_p:.4f}")
print(f"  LEOSat.AOP   = 0.0000")
print(f"  LEOSat.TA    = 90.0000")
print()
print(f"  DebrisObject.SMA    = {a:.4f}")
print(f"  DebrisObject.ECC    = 0.0001")
print(f"  DebrisObject.INC    = {inc_d:.4f}")
print(f"  DebrisObject.RAAN   = {RAAN_d:.6f}")
print(f"  DebrisObject.AOP    = 0.0000")
print(f"  DebrisObject.TA     = 270.0000")
print()
print(f"  TCA ElapsedSecs     = {TCA_t:.2f}  (T_p/4)")
print(f"  CAM.Element1        = {-dV_cam:.6f}  (retrograde VNB)")
print(f"{'=' * 70}")

# ============================================================
# Close report file
# ============================================================
sys.stdout = sys.__stdout__
_report_file.close()
print(f"\nReport written to: {_report_path}")
