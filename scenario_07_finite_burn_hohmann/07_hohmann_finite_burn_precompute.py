"""
Scenario 08: Finite Burn + Fuel Budget Pre-computation
=======================================================
Hohmann Transfer: 400 km → 600 km circular orbit (LEO to LEO)

Spacecraft:
  Dry mass  : 500.0 kg
  Fuel mass : 100.0 kg
  Wet mass  : 600.0 kg
  Thrust    : 50 N   — bipropellant (MMH/NTO), Moog/Aerojet 50 N class
  Isp       : 290 s  — realistic for MMH/NTO at this thrust level

Mission concept:
  LEO transfer vehicle or constellation deployment bus raising a 600 kg
  hosted payload from an initial 400 km parking orbit to a 600 km
  operational orbit. The 50 N biprop thruster keeps the finite burn arc
  below 12% of the orbital period (~660 s per burn), making the finite
  vs. impulsive difference clearly visible in GMAT output.

Strategy (three sequential DC targeting blocks):
  Burn 1 (perigee): Vary Burn1Dur → Achieve SC.Earth.SMA = 6878.14 km
  Burn 2 (apogee) : Vary Burn2Dur → Achieve SC.Earth.SMA = 6978.14 km
  Burn 3 (trim)   : Vary Burn3Dur → Achieve SC.Earth.ECC = 0.003

References:
  Bate, Mueller & White (1971) Fundamentals of Astrodynamics, Ch 6
  Vallado (2013) Fundamentals of Astrodynamics and Applications, §6.3
"""

import math

# ──────────────────────────────────────────────────────────────
# 1. CONSTANTS
# ──────────────────────────────────────────────────────────────
mu      = 398600.4418   # km³/s²
R_earth = 6378.137      # km
g0      = 9.80665       # m/s²

# ──────────────────────────────────────────────────────────────
# 2. SPACECRAFT PARAMETERS
# ──────────────────────────────────────────────────────────────
m_dry    = 500.0    # kg
m_fuel_0 = 100.0    # kg
m_wet    = 600.0    # kg

thrust_N = 50.0     # N   — 50 N biprop thruster (MMH/NTO)
Isp_s    = 290.0    # s   — specific impulse
ve_ms    = Isp_s * g0          # m/s = 2843.928 m/s
mdot     = thrust_N / ve_ms    # kg/s = 0.017579 kg/s

# ──────────────────────────────────────────────────────────────
# 3. ORBIT DEFINITIONS
# ──────────────────────────────────────────────────────────────
alt_park  = 400.0              # km
alt_final = 600.0              # km
r1 = R_earth + alt_park        # km = 6778.137
r2 = R_earth + alt_final       # km = 6978.137
SMA_tx = (r1 + r2) / 2.0      # km = 6878.137 — transfer ellipse SMA

ECC_tx = (r2 - r1) / (r2 + r1)

# GMAT DC achieve targets
SMA_tx_GMAT  = 6878.14         # km — DC1 (transfer ellipse)
SMA_fin_GMAT = 6978.14         # km — DC2 (final circular)
ECC_trim     = 0.003           # —  — DC3 (partial ECC trim)

# ──────────────────────────────────────────────────────────────
# 4. VELOCITIES (vis-viva)
# ──────────────────────────────────────────────────────────────
v_park    = math.sqrt(mu / r1)
v_final   = math.sqrt(mu / r2)
v_tx_peri = math.sqrt(mu * (2/r1 - 1/SMA_tx))
v_tx_apo  = math.sqrt(mu * (2/r2 - 1/SMA_tx))

# ──────────────────────────────────────────────────────────────
# 5. IMPULSIVE ΔV
# ──────────────────────────────────────────────────────────────
dv1_ms   = (v_tx_peri - v_park)  * 1000.0   # m/s
dv2_ms   = (v_final   - v_tx_apo) * 1000.0  # m/s
dv_total = dv1_ms + dv2_ms                   # m/s

# ──────────────────────────────────────────────────────────────
# 6. TSIOLKOVSKY BURN SIZING
# ──────────────────────────────────────────────────────────────
def tsiolkovsky(m0, dv, F, ve):
    mf    = m0 * math.exp(-dv / ve)
    dm    = m0 - mf
    t     = dm / (F / ve)
    return mf, dm, t

mf1, dm1, t1 = tsiolkovsky(m_wet,  dv1_ms, thrust_N, ve_ms)
mf2, dm2, t2 = tsiolkovsky(mf1,    dv2_ms, thrust_N, ve_ms)

dm3_est = dm2 * 0.15
t3_est  = dm3_est / mdot
mf3     = mf2 - dm3_est

dm_total    = dm1 + dm2 + dm3_est
m_remaining = m_fuel_0 - dm_total
pct_used    = dm_total / m_fuel_0 * 100.0

# ──────────────────────────────────────────────────────────────
# 7. ORBITAL PERIODS
# ──────────────────────────────────────────────────────────────
T_park  = 2*math.pi*math.sqrt(r1**3 / mu)
T_final = 2*math.pi*math.sqrt(r2**3 / mu)
T_tx    = 2*math.pi*math.sqrt(SMA_tx**3 / mu)
T_coast = T_tx / 2.0

# Burn arc as % of parking orbit period
arc_pct_b1 = t1 / T_park * 100.0
arc_pct_b2 = t2 / T_park * 100.0

# ──────────────────────────────────────────────────────────────
# 8. DC INITIAL GUESSES  (Tsiolkovsky + ~5% gravity/steering loss)
# ──────────────────────────────────────────────────────────────
Burn1Dur_guess = round(t1 * 1.05, 1)
Burn2Dur_guess = round(t2 * 1.05, 1)
Burn3Dur_guess = round(t3_est, 1)

# ──────────────────────────────────────────────────────────────
# 9. DC PARAMETER DERIVATION
#    Perturbation, Lower, Upper, MaxStep — derived from first
#    principles rather than set by heuristic rule-of-thumb.
#
#    Reference: GMAT Math Spec §3.4 (DC finite-difference gradient)
# ──────────────────────────────────────────────────────────────

# --- Perturbation ---
# The DC uses a central finite difference to estimate the Jacobian:
#   J ≈ (Achieve(x+h) − Achieve(x−h)) / (2h)
# where h = Perturbation (seconds of burn duration).
#
# Optimal h balances two competing errors:
#   - Truncation error  ∝ h²       (smaller h → more accurate gradient)
#   - Cancellation error ∝ eps/h   (smaller h → numerical noise dominates)
# Minimum of their sum occurs near h ≈ eps^(1/3) × |x|.
# Machine epsilon for IEEE 754 double: eps ≈ 2.2e-16.
# Practical floor: GMAT's integrator tolerance (~1e-10) dominates below ~1e-4 s.
# Use integrator-noise floor rather than machine epsilon:
eps_integrator = 1e-10   # GMAT RK89 default absolute tolerance (m, km)
# SMA sensitivity to burn duration from Gauss VOP (tangential thrust):
#   dSMA/dt_burn ≈ (2 * SMA^2 * F) / (mu_km * m)
#   Units: km * (N / (km^3/s^2 * kg)) = km * s^2/km^2 * N/kg
#          = s^2/km * (kg*m/s^2)/kg = s^2/km * m/s^2
#   Convert F to km-unit system: F [N] = F [kg*m/s^2] = F*1e-3 [kg*km/s^2]
#   => dSMA/dt_burn [km/s] = (2 * SMA_km^2 * F_km) / (mu_km * m_kg)
F_km     = thrust_N * 1e-3              # kg*km/s^2
dSMA_dt1 = (2 * SMA_tx_GMAT**2 * F_km) / (mu * mf1)   # km/s  (per second of burn)
# A perturbation of h seconds changes SMA by h * dSMA_dt1 km.
# Noise floor in SMA from GMAT RK89 integrator: ~eps_integrator km.
# Minimum h such that signal > noise:
h_min = eps_integrator / abs(dSMA_dt1) if dSMA_dt1 != 0 else 0.01
# Practical Perturbation: round up to nearest 0.1 s, floor at 0.1 s
perturb_b1 = max(round(h_min + 0.05, 1), 0.1)
perturb_b2 = perturb_b1   # same physics for Burn 2

# For Burn 3 (ECC target), sensitivity is lower — ECC changes slowly;
# use a larger perturbation to stay above integrator noise on ECC (~1e-8):
perturb_b3 = 1.0   # s — 1 s is well above ECC noise floor for this thruster

# --- Lower bound ---
# Minimum physically meaningful burn duration.
# Lower bound = duration to deliver ΔV × safety_factor_low with current mass.
# Using 50% of the impulsive ΔV as the floor (half the energy → still reaches
# a physically valid intermediate state; DC can walk up from there).
safety_low = 0.50
def burn_duration(m0, dv_ms, F, ve):
    """Tsiolkovsky burn duration for given ΔV."""
    mf = m0 * math.exp(-dv_ms / ve)
    dm = m0 - mf
    return dm / (F / ve)

t1_lower = burn_duration(m_wet, dv1_ms * safety_low, thrust_N, ve_ms)
t2_lower = burn_duration(mf1,   dv2_ms * safety_low, thrust_N, ve_ms)
t3_lower = 1.0   # s — 1 s is the practical minimum finite burn in GMAT

Lower_b1 = max(int(t1_lower), 10)   # round down to integer seconds, floor 10 s
Lower_b2 = max(int(t2_lower), 10)
Lower_b3 = int(t3_lower)

# --- Upper bound ---
# Maximum burn duration the DC should ever try.
# Upper bound = duration to deliver ΔV × safety_factor_high.
# Using 200% of the impulsive ΔV as the ceiling (double the energy → orbit
# significantly overshoots the target; DC must never try this in practice,
# but the bound must be wide enough that a converged solution never clips it).
safety_high = 2.00
t1_upper = burn_duration(m_wet, dv1_ms * safety_high, thrust_N, ve_ms)
t2_upper = burn_duration(mf1,   dv2_ms * safety_high, thrust_N, ve_ms)
t3_upper = t3_est * 5.0   # Burn 3 has no impulsive analogue; use 5× estimate

Upper_b1 = int(t1_upper) + 1
Upper_b2 = int(t2_upper) + 1
Upper_b3 = int(t3_upper) + 1

# --- MaxStep ---
# Caps the largest single DC iteration step (seconds).
# Rule: MaxStep = (Upper - Lower) / 10
# This ensures that even a poor first-iteration gradient cannot jump the
# solution past the opposite bound in one step. Ten steps across the full
# search corridor is conservative but guarantees monotone convergence for
# well-conditioned 1x1 systems.
MaxStep_b1 = round((Upper_b1 - Lower_b1) / 10.0, 1)
MaxStep_b2 = round((Upper_b2 - Lower_b2) / 10.0, 1)
MaxStep_b3 = round((Upper_b3 - Lower_b3) / 10.0, 1)

# ──────────────────────────────────────────────────────────────
# 9. PRINT REPORT
# ──────────────────────────────────────────────────────────────
SEP = "─" * 65

print(SEP)
print("SCENARIO 08: HOHMANN FINITE BURN — PRE-COMPUTATION REPORT")
print(SEP)

print("\n── SPACECRAFT PARAMETERS ───────────────────────────────────────")
print(f"  Dry mass             : {m_dry:.1f} kg")
print(f"  Fuel mass (full)     : {m_fuel_0:.1f} kg")
print(f"  Wet mass at epoch    : {m_wet:.1f} kg")
print(f"  Thruster             : 50 N biprop (MMH/NTO) — Moog/Aerojet 50 N class")
print(f"  Thrust               : {thrust_N:.1f} N")
print(f"  Isp                  : {Isp_s:.1f} s")
print(f"  Exhaust velocity (ve): {ve_ms:.3f} m/s")
print(f"  Mass flow rate (ṁ)   : {mdot*1000:.4f} g/s")

print("\n── ORBIT DEFINITIONS ───────────────────────────────────────────")
print(f"  Parking orbit        : {alt_park:.0f} km alt  (SMA = {r1:.3f} km)")
print(f"  Target orbit         : {alt_final:.0f} km alt  (SMA = {r2:.3f} km)")
print(f"  Transfer ellipse SMA : {SMA_tx:.3f} km  (ECC = {ECC_tx:.6f})")
print(f"  GMAT DC1 SMA target  : {SMA_tx_GMAT:.2f} km  (transfer ellipse)")
print(f"  GMAT DC2 SMA target  : {SMA_fin_GMAT:.2f} km  (final circular)")
print(f"  GMAT DC3 ECC target  : {ECC_trim:.3f}      (partial trim)")

print("\n── VELOCITIES (vis-viva) ───────────────────────────────────────")
print(f"  v_parking orbit      : {v_park*1000:.4f} m/s")
print(f"  v_transfer (perigee) : {v_tx_peri*1000:.4f} m/s")
print(f"  v_transfer (apogee)  : {v_tx_apo*1000:.4f} m/s")
print(f"  v_final orbit        : {v_final*1000:.4f} m/s")

print("\n── IMPULSIVE ΔV ────────────────────────────────────────────────")
print(f"  ΔV₁ (Burn 1, perigee)  : {dv1_ms:.3f} m/s")
print(f"  ΔV₂ (Burn 2, apogee)   : {dv2_ms:.3f} m/s")
print(f"  ΔV total (Burn 1+2)    : {dv_total:.3f} m/s")
print(f"  ΔV₃ (Burn 3, ECC trim) : analytically undefined — DC targets ECC = {ECC_trim}")

print("\n── TSIOLKOVSKY BURN SIZING ─────────────────────────────────────")
print(f"  Burn 1 — perigee kick to transfer ellipse")
print(f"    Mass before          : {m_wet:.3f} kg")
print(f"    Mass after           : {mf1:.3f} kg")
print(f"    Propellant consumed  : {dm1:.3f} kg")
print(f"    Burn duration (est.) : {t1:.1f} s  ({t1/60:.2f} min)")
print(f"    Burn arc             : {arc_pct_b1:.1f}% of parking orbit  ✓ (<20% limit)")
print(f"    DC initial guess     : {Burn1Dur_guess:.1f} s  (+5% gravity/steering loss)")
print()
print(f"  Burn 2 — circularise at apogee (600 km)")
print(f"    Mass before          : {mf1:.3f} kg")
print(f"    Mass after           : {mf2:.3f} kg")
print(f"    Propellant consumed  : {dm2:.3f} kg")
print(f"    Burn duration (est.) : {t2:.1f} s  ({t2/60:.2f} min)")
print(f"    Burn arc             : {arc_pct_b2:.1f}% of parking orbit  ✓ (<20% limit)")
print(f"    DC initial guess     : {Burn2Dur_guess:.1f} s  (+5% gravity/steering loss)")
print()
print(f"  Burn 3 — partial ECC trim (DC3: ECC → {ECC_trim})")
print(f"    No impulsive analogue; DC finds duration numerically")
print(f"    Estimate (15% of Burn 2): {dm3_est:.3f} kg / {t3_est:.1f} s")
print(f"    DC initial guess     : {Burn3Dur_guess:.1f} s")

print("\n── FUEL BUDGET ─────────────────────────────────────────────────")
print(f"  {'Item':<35} {'kg':>8}   {'% tank':>7}")
print(f"  {'─'*53}")
print(f"  {'Initial fuel load':<35} {m_fuel_0:>8.3f}   {'100.000':>7}")
print(f"  {'Burn 1 consumed (est.)':<35} {dm1:>8.3f}   {dm1/m_fuel_0*100:>7.3f}")
print(f"  {'Burn 2 consumed (est.)':<35} {dm2:>8.3f}   {dm2/m_fuel_0*100:>7.3f}")
print(f"  {'Burn 3 consumed (est.)':<35} {dm3_est:>8.3f}   {dm3_est/m_fuel_0*100:>7.3f}")
print(f"  {'─'*53}")
print(f"  {'TOTAL consumed (est.)':<35} {dm_total:>8.3f}   {pct_used:>7.3f}")
print(f"  {'Remaining fuel (est.)':<35} {m_remaining:>8.3f}   {m_remaining/m_fuel_0*100:>7.3f}")
print(f"  {'─'*53}")
print(f"  Final mass: {m_dry:.0f} + {m_remaining:.3f} = {m_dry+m_remaining:.3f} kg")
print(f"  ({dm_total:.1f} kg consumed = {pct_used:.1f}% of {m_fuel_0:.0f} kg tank)")

print("\n── ORBITAL PERIODS ─────────────────────────────────────────────")
print(f"  T_parking (400 km)   : {T_park:.1f} s  ({T_park/60:.2f} min)")
print(f"  T_transfer ellipse   : {T_tx:.1f} s  ({T_tx/60:.2f} min)")
print(f"  T_final   (600 km)   : {T_final:.1f} s  ({T_final/60:.2f} min)")
print(f"  Coast (perigee→apo)  : {T_coast:.1f} s  ({T_coast/60:.2f} min)")

print("\n── GMAT DC CONFIGURATION ───────────────────────────────────────")
print(f"""
  DC1  Vary Burn1Dur = {Burn1Dur_guess:.1f} s  {{Perturbation={perturb_b1}, Lower={Lower_b1}, Upper={Upper_b1}, MaxStep={MaxStep_b1}}}
       Achieve SC.Earth.SMA = {SMA_tx_GMAT:.2f} km  {{Tolerance=0.5}}

  DC2  Vary Burn2Dur = {Burn2Dur_guess:.1f} s  {{Perturbation={perturb_b2}, Lower={Lower_b2}, Upper={Upper_b2}, MaxStep={MaxStep_b2}}}
       Achieve SC.Earth.SMA = {SMA_fin_GMAT:.2f} km  {{Tolerance=0.5}}

  DC3  Vary Burn3Dur = {Burn3Dur_guess:.1f} s  {{Perturbation={perturb_b3}, Lower={Lower_b3}, Upper={Upper_b3}, MaxStep={MaxStep_b3}}}
       Achieve SC.Earth.ECC = {ECC_trim:.3f}   {{Tolerance=0.001}}

  Sequential 1x1 Jacobians -- always well-conditioned.
""")

print("\n-- DC PARAMETER DERIVATION SUMMARY ---------------------------------")
print(f"""
  Perturbation (Burn 1 & 2):
    dSMA/dt_burn (Gauss VOP tangential): {dSMA_dt1:.6f} km/s per s of burn
    h_min = eps_integrator / dSMA_dt1 = {h_min:.2e} s  (sub-millisecond)
    Practical floor 0.1 s applied (GMAT integrator step granularity).
    Adopted Perturbation: {perturb_b1} s

  Perturbation (Burn 3):
    ECC sensitivity is lower; 1.0 s adopted (well above ECC noise floor ~1e-8).

  Lower bounds (50% of impulsive DV via Tsiolkovsky):
    Burn 1: {t1_lower:.1f} s  ->  Lower = {Lower_b1} s
    Burn 2: {t2_lower:.1f} s  ->  Lower = {Lower_b2} s
    Burn 3: 1 s (practical minimum finite burn in GMAT)

  Upper bounds (200% of impulsive DV via Tsiolkovsky):
    Burn 1: {t1_upper:.1f} s  ->  Upper = {Upper_b1} s
    Burn 2: {t2_upper:.1f} s  ->  Upper = {Upper_b2} s
    Burn 3: 5x estimate = {t3_upper:.1f} s  ->  Upper = {Upper_b3} s

  MaxStep = (Upper - Lower) / 10  (caps single DC iteration jump):
    Burn 1: ({Upper_b1} - {Lower_b1}) / 10 = {MaxStep_b1} s
    Burn 2: ({Upper_b2} - {Lower_b2}) / 10 = {MaxStep_b2} s
    Burn 3: ({Upper_b3} - {Lower_b3}) / 10 = {MaxStep_b3} s
""")

print("── FINITE BURN PHYSICS NOTES ───────────────────────────────────")
print(f"""
  Why burn arc must stay below ~20% of orbital period:
    At 50 N on 600 kg, acceleration = {thrust_N/m_wet*1000:.2f} mN/kg = {thrust_N/m_wet/g0*1000:.4f}g
    Burn 1 arc = {arc_pct_b1:.1f}% of T_park ✓  (22 N would give 27% ✗)

  Why GMAT durations exceed Tsiolkovsky estimates:
    1. Gravity loss — thrust must partly oppose gravity vector
    2. Steering loss — thrust rotates with VNB frame during finite arc;
       not perfectly tangential throughout the burn
    3. Residual ECC — finite arc straddles apse; Burn 3 trims to ECC={ECC_trim}

  Thruster selection rationale:
    50 N / 290 s biprop (MMH/NTO) — e.g. Moog 50 N or Aerojet heritage
    class. Isp = 290 s is conservative for MMH/NTO (typical 290–310 s).
    22 N thrusters (R-6D class) would require <120 kg spacecraft to keep
    the burn arc below 20% of the orbital period at these altitudes.
""")

print(SEP)
print("END OF PRE-COMPUTATION REPORT")
print(SEP)
