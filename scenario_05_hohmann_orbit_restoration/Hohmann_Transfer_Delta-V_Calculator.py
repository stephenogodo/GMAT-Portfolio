"""
Hohmann Transfer Delta-V Calculator
====================================
Run this script BEFORE writing the GMAT script.
It derives the two burn magnitudes from first principles
using the vis-viva equation, then prints the values
ready to copy into the GMAT ImpulsiveBurn definitions.

Usage:
    python hohmann_deltav.py

Change r1_km and r2_km to suit any LEO-to-LEO Hohmann transfer.
"""

import math

# ── Constants ─────────────────────────────────────────────────────────────────
MU = 398600.4418          # Earth gravitational parameter  [km³/s²]

# ── Mission Parameters ────────────────────────────────────────────────────────
# Define your two circular orbit radii (Earth-centre to satellite)
# Earth mean radius ≈ 6371 km; add your altitude above surface.

r1_km = 6758.14           # Degraded orbit SMA  [km]
r2_km = 6778.14           # Nominal  orbit SMA  [km]

# ── Transfer Ellipse ──────────────────────────────────────────────────────────
# Perigee of transfer = r1, apogee = r2
a_transfer = (r1_km + r2_km) / 2.0

# ── Vis-Viva: v = sqrt( mu * (2/r - 1/a) ) ───────────────────────────────────
def vis_viva(r, a):
    """Orbital speed at radius r in an orbit with semi-major axis a."""
    return math.sqrt(MU * (2.0 / r - 1.0 / a))

# Four key velocities
v1    = vis_viva(r1_km, r1_km)          # circular speed at r1
v_tp  = vis_viva(r1_km, a_transfer)     # transfer ellipse speed at perigee (r1)
v_ta  = vis_viva(r2_km, a_transfer)     # transfer ellipse speed at apogee  (r2)
v2    = vis_viva(r2_km, r2_km)          # circular speed at r2

# Delta-V for each burn
dv1 = v_tp - v1     # Burn 1: prograde at perigee  → raises apogee to r2
dv2 = v2  - v_ta    # Burn 2: prograde at apogee   → raises perigee to r2
dv_total = dv1 + dv2

# ── Report ────────────────────────────────────────────────────────────────────
print("=" * 60)
print("  HOHMANN TRANSFER  —  DELTA-V DERIVATION")
print("=" * 60)
print(f"\n  Initial orbit  SMA  r1 = {r1_km:.3f} km")
print(f"  Target  orbit  SMA  r2 = {r2_km:.3f} km")
print(f"  Altitude difference    = {(r2_km - r1_km):.3f} km")
print(f"  Transfer ellipse SMA   = {a_transfer:.3f} km")
print()
print("  Velocities (vis-viva):")
print(f"    v1   (circular at r1)          = {v1:.6f} km/s")
print(f"    v_tp (transfer at perigee r1)  = {v_tp:.6f} km/s")
print(f"    v_ta (transfer at apogee  r2)  = {v_ta:.6f} km/s")
print(f"    v2   (circular at r2)          = {v2:.6f} km/s")
print()
print("  Delta-V:")
print(f"    ΔV1 = v_tp - v1  = {dv1:.6f} km/s  ({dv1*1000:.3f} m/s)  ← Burn1.Element1")
print(f"    ΔV2 = v2  - v_ta = {dv2:.6f} km/s  ({dv2*1000:.3f} m/s)  ← Burn2.Element1")
print(f"    ΔV_total         = {dv_total:.6f} km/s  ({dv_total*1000:.3f} m/s)")
print()
print("  GMAT script values (copy these directly):")
print(f"    GMAT Burn1.Element1 = {dv1:.6f};")
print(f"    GMAT Burn2.Element1 = {dv2:.6f};")
print("=" * 60)