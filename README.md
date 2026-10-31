# GMAT Astrodynamics Portfolio

A structured collection of LEO and GEO mission simulation scenarios built in [GMAT R2022a](https://gmat.gsfc.nasa.gov/) (NASA General Mission Analysis Tool).
Each scenario demonstrates a distinct flight-dynamics engineering skill relevant to satellite operations, constellation design, and manoeuvre planning.

**Author:** Stephen O. Ogodo | [LinkedIn](https://linkedin.com/in/stephenogodo) | [GitHub](https://github.com/stephenogodo)

---

## Background

This portfolio was developed independently to translate 15+ years of GEO satellite operations experience at NigComSat into demonstrable LEO flight-dynamics capability. Scenarios progress from single-satellite propagation through ISL geometry, ground-station scheduling, Walker constellation design, impulsive and finite manoeuvres, GEO station-keeping, conjunction analysis with collision avoidance manoeuvre sizing, and multi-asset ground contact scheduling optimisation.

All manoeuvre scenarios follow a **physics-first methodology**: delta-V and burn parameters are derived analytically in Python before any GMAT scripting, so GMAT serves as verification rather than the source of truth.

---

## Scenario Index

| # | Scenario | Key Skill | Folder |
|---|---|---|---|
| 01 | LEO Orbit Propagation and Ground Track | J2 propagation, ground track geometry | [scenario_01_leo_ground_track](./scenario_01_leo_ground_track/) |
| 02 | Ground Station Access (Abuja) | ContactLocator, pass scheduling, coverage analysis | [scenario_02_ground_station_access](./scenario_02_ground_station_access/) |
| 03a | Two Co-planar Satellites — ISL Range Monitoring | Co-planar ISL, J2 secular drift, range monitoring | [scenario_03a_coplanar_isl_2sat](./scenario_03a_coplanar_isl_2sat/) |
| 03b | Six Co-planar Satellites — ISL Violation Detection | Ring topology ISL, threshold alerting | [scenario_03b_coplanar_isl_6sat](./scenario_03b_coplanar_isl_6sat/) |
| 04 | Inter-planar ISL Geometry | Cross-plane ISL, TCA analysis, link-budget envelope | [scenario_04_interplanar_isl](./scenario_04_interplanar_isl/) |
| 05 | Hohmann Orbit Restoration (Impulsive) | Vis-viva delta-V, two-burn Hohmann, manoeuvre report | [scenario_05_hohmann_orbit_restoration](./scenario_05_hohmann_orbit_restoration/) |
| 06 | Walker 24/3/1 Constellation and Contact Analysis | Walker geometry, fleet-level contact scheduling | [scenario_06_walker_constellation](./scenario_06_walker_constellation/) |
| 07 | Finite Burn Hohmann with Differential Corrector | Finite burn, DC targeting, fuel mass accounting | [scenario_07_finite_burn_hohmann](./scenario_07_finite_burn_hohmann/) |
| 08 | GEO East-West Station-Keeping (Single Arc) | GEO EWSK, tesseral drift, deadband control | [scenario_08_geo_ewsk](./scenario_08_geo_ewsk/) |
| 09 | GEO East-West Station-Keeping (Full Duty Cycle) | Multi-cycle EWSK, XY phase-space plot, burn calibration | [scenario_09_geo_ewsk](./scenario_09_geo_ewsk/) |
| 10 | LEO Conjunction Analysis and CAM Sizing | TCA, miss distance, Foster 2D Pc, CW CAM delta-V | [scenario_10_leo_conjunction](./scenario_10_leo_conjunction/) |
| 11 | Contact Scheduling with Integer Linear Programming | ILP, multi-objective optimisation, ground station scheduling | [scenario_11_contact_scheduling_ilp](./scenario_11_contact_scheduling_ilp/) |

---

## Scenario Detail

---

### Scenario 01 — LEO Orbit Propagation and Ground Track
**Folder:** [`scenario_01_leo_ground_track/`](./scenario_01_leo_ground_track/)

Propagates a single LEO satellite (SMA = 6778.14 km, INC = 51.6°, ~400 km altitude, ISS-class orbit) for 24 hours using the JGM2 4x4 gravity model and an RK89 adaptive integrator. The ground track is visualised in GMAT's GroundTrackPlot and exported as a screenshot.

This scenario establishes the foundational orbital mechanics concepts used in every subsequent scenario: the inclination as a hard latitude coverage ceiling (±51.6°), the ~23 deg/orbit westward longitude shift driven by Earth's rotation during each 92.5-minute period, and ~15.5 orbits per day. The J2 zonal harmonic introduces ~6.96 deg/day nodal regression, visible as a slight systematic eastward offset in successive ground track passes over the 24-hour window.

**Key parameters:** SMA = 6778.14 km | INC = 51.6° | ECC ≈ 0 | Epoch: 01 Jan 2024 00:00:00 UTC
**Propagator:** RK89 | Force model: JGM2 4x4

---

### Scenario 02 — Ground Station Access (Abuja)
**Folder:** [`scenario_02_ground_station_access/`](./scenario_02_ground_station_access/)

Computes all contact windows between the LEO satellite and the Abuja ground station (9.0579°N, 7.4951°E, 342 m, 5° elevation mask) over 24 hours using GMAT's ContactLocator with root-finding interpolation (accurate to millisecond precision). The script is fully commented, documenting every design choice.

GMAT returned three contact events:

| Pass | Start (UTC) | End (UTC) | Duration |
|---|---|---|---|
| 1 | 01 Jan 2024 03:43:00.095 | 03:50:28.597 | 448.5 s (7.47 min) |
| 2 | 01 Jan 2024 05:20:39.019 | 05:24:47.990 | 249.0 s (4.15 min) |
| 3 | 01 Jan 2024 16:54:43.360 | 17:02:55.083 | 491.7 s (8.19 min) |

**Total daily contact: 1189.2 s (~19.8 min/day, ~1.4% duty cycle).** The 11.5-hour gap between Pass 2 and Pass 3 directly illustrates the single-satellite coverage vulnerability that motivates the Walker constellation in Scenario 06. Abuja was chosen as a direct operational parallel to the author's career at the NigComSat ground segment.

---

### Scenario 03a — Two Co-planar Satellites: ISL Range Monitoring
**Folder:** [`scenario_03a_coplanar_isl_2sat/`](./scenario_03a_coplanar_isl_2sat/)

Two co-planar LEO satellites (SMA = 6778.14 km, INC = 51.6°, 45° true anomaly separation) propagated for 24 hours at 60-second reporting intervals. An XYPlot monitors the ISL range continuously, and a ReportFile logs all range data.

Range evolves from 5187 km at epoch with a secular contraction of ~35.5 km/hour superimposed on a ±26 km orbital-period oscillation. The secular trend is caused by J2 differential mean-motion. Without corrective slot-keeping burns, the pair would converge to collision geometry within 3-4 days. This scenario quantifies the delta-V budget required for formation maintenance.

**Key result:** ISL range minimum 4334 km (end of 24 h) | Maximum 5213 km | Secular drift -35.5 km/h

---

### Scenario 03b — Six Co-planar Satellites: ISL Violation Detection
**Folder:** [`scenario_03b_coplanar_isl_6sat/`](./scenario_03b_coplanar_isl_6sat/)

Six co-planar satellites (60° true anomaly spacing, same SMA/INC) with a 7500 km ISL range threshold. The script implements per-pair conditional logic to route only violating pairs to a dedicated violations report, while all six pair ranges are logged continuously.

Three distinct ISL behaviour classes emerge from the J2 differential drift pattern:

| Pair | Behaviour | Threshold Breached? |
|---|---|---|
| R12, R45 | Periodic oscillation (~±380 km amplitude) | No |
| R23, R56 | Near-stable (spread < 25 km over 24 h) | No |
| R34, R61 | Secular divergence | Yes — R61 at 15:58 UTC, R34 at 16:06 UTC |

The asymmetry arises from the interaction between the 60° TA spacing and the J2 perturbation's dependence on argument of latitude.

---

### Scenario 04 — Inter-planar ISL Geometry
**Folder:** [`scenario_04_interplanar_isl/`](./scenario_04_interplanar_isl/)

Two satellites in different orbital planes (different RAAN, same SMA = 6778.14 km and INC = 51.6°) propagated for 24 hours. The ISL range is logged at 60-second intervals, and close-approach events are extracted using a ContactLocator.

Range oscillates between 5,952 km and 9,585 km, with 31 TCA events in 24 hours — one every ~46.5 minutes (half the orbital period). This TCA period = T/2 relationship is a fundamental two-body mechanics result: two satellites in the same orbit but different planes pass through their mutual intersection nodes twice per relative orbit.

---

### Scenario 05 — Hohmann Orbit Restoration (Impulsive Burns)
**Folder:** [`scenario_05_hohmann_orbit_restoration/`](./scenario_05_hohmann_orbit_restoration/)

Restores a LEO satellite from a drag-degraded orbit (SMA = 6758.14 km, ~20 km altitude loss) to its nominal orbit (SMA = 6778.14 km) using a classical two-burn Hohmann transfer. All delta-V values are pre-computed analytically in Python using the vis-viva equation before being entered into GMAT.

**Analytically derived delta-V:**
- dV1 = 5.671 m/s (prograde at periapsis — raises apoapsis)
- dV2 = 5.667 m/s (prograde at apoapsis — circularises)
- **dV_total = 11.338 m/s**

GMAT achieved SMA = 6778.06 km (residual error: 80 m, 0.001% of target).

---

### Scenario 06 — Walker 24/3/1 Constellation and Fleet Contact Analysis
**Folder:** [`scenario_06_walker_constellation/`](./scenario_06_walker_constellation/)

A complete Walker T/P/F = 24/3/1 constellation at INC = 51.6°, SMA = 6778.14 km — 24 satellites across 3 orbital planes (RAAN: 0°, 120°, 240°) with a 15° inter-plane phase offset. Four ground stations are analysed simultaneously: Tromso (69.7°N), London (51.5°N), Nairobi (1.3°S), and Lagos (6.5°N). GMAT generates 24 individual contact report files, aggregated into a summary HTML report.

| Station | Latitude | Fleet Passes / 24 h | Total Fleet Contact |
|---|---|---|---|
| Tromso | 69.7°N | 0 | 0 s (inclination blackout) |
| London | 51.5°N | 128 | ~57,500 s (~16 h) |
| Nairobi | 1.3°S | 79 | ~27,200 s (~7.6 h) |
| Lagos | 6.5°N | 81 | ~27,900 s (~7.8 h) |

**Key finding:** Tromso receives zero passes — the 51.6° inclination is a hard geometric ceiling. London at ~51.5°N sits at the coverage limit and achieves near-continuous coverage (~11-minute revisit interval).

---

### Scenario 07 — Finite Burn Hohmann with Differential Corrector
**Folder:** [`scenario_07_finite_burn_hohmann/`](./scenario_07_finite_burn_hohmann/)

Extends Scenario 05 from impulsive to finite-burn manoeuvres: a two-burn Hohmann transfer raising the orbit from 400 km to 600 km using a 50 N thruster with Isp = 300 s and a 100 kg propellant budget. All burn durations and fuel consumption are pre-computed in Python using the rocket equation. Three sequential Differential Corrector (DC) targeting sequences are used.

| DC Target | Goal | GMAT Result | Residual Error |
|---|---|---|---|
| DC1 — Burn 1 | SMA = 6878.14 km | 6878.142 km | 2 m |
| DC2 — Burn 2 | SMA = 6978.14 km | 6978.146 km | 6 m |
| DC3 — ECC trim | ECC = 0.003 | 0.00223 | Within ±0.001 |

**Fuel consumed: 23.5 kg of 100 kg budget (pre-computed estimate: 24.6 kg, 4.7% conservative).**

---

### Scenario 08 — GEO East-West Station-Keeping (Single Arc Burn)
**Folder:** [`scenario_08_geo_ewsk/`](./scenario_08_geo_ewsk/)

GEO East-West Station-Keeping (EWSK) for a GEO satellite maintained at 42.5°E longitude within a ±0.05° deadband. The tesseral drift acceleration at 42.5°E is -0.000233 deg/day², a gentle westward drift because the slot sits near the 348.7°E unstable equilibrium longitude. A single arc impulsive burn corrects the in-plane longitude error and restores the satellite to its nominal slot. The drift rate, burn timing, and delta-V are derived from the GMAT longitude history report and visualised as an XY drift plot.

This scenario directly replicates the station-keeping manoeuvre cycle executed for NigComSat-1 and NigComSat-1R over 15 years of GEO operations.

---

### Scenario 09 — GEO East-West Station-Keeping (Full Duty Cycle)
**Folder:** [`scenario_09_geo_ewsk/`](./scenario_09_geo_ewsk/)

Extends the single-arc EWSK from Scenario 08 to a full operational duty cycle: multiple correction burns over an extended simulation period, maintaining the GEO satellite within its longitude deadband. Models the complete station keeping strategy with periodic burns timed to the drift cycle, accumulates the total delta-V budget over the cycle, and evaluates slot compliance across the full simulation arc.

The XY plot shows the satellite's trajectory within the deadband boundaries, with burn events visible as discrete jumps in the drift rate axis — equivalent to the operational EWSK analysis charts produced during station-keeping manoeuvre planning at NigComSat.

---

### Scenario 10 — LEO Conjunction Analysis and Collision Avoidance Manoeuvre
**Folder:** [`scenario_10_leo_conjunction/`](./scenario_10_leo_conjunction/)

Simulates a close approach between two LEO satellites with near-identical orbits (RAAN offset of 0.000417 deg, SMA 6928 km, INC 53 deg). Computes the time of closest approach (TCA), miss distance, and relative velocity from GMAT ephemeris output. Applies the Foster 2D Pc formulation to derive collision probability, and sizes a Clohessy-Wiltshire in-track CAM burn to reduce Pc below the operational threshold.

**Key results:**
- TCA miss distance: 50.2 m (cross-track dominated; RAAN geometry floor)
- Relative velocity at TCA: 91.4 m/s
- Foster 2D Pc: 2.02e-3 (above 1e-3 threshold — CAM required)
- CAM delta-V: 0.11 m/s in-track (CW formulation)

**Physics insight:** The 50.2 m miss distance is set by the cross-track geometry floor d = a × delta_RAAN(rad) and cannot be reduced without changing RAAN. The conjunction is not a crossing of the orbits — it is two objects arriving near the same point in space at nearly the same time, on orbits that do not geometrically intersect.

---

### Scenario 11 — Contact Scheduling with Integer Linear Programming (ILP)
**Folder:** [`scenario_11_contact_scheduling_ilp/`](./scenario_11_contact_scheduling_ilp/)

Optimally schedules ground contacts for all 24 satellites of the Walker 24/3/1 constellation from Scenario 06 using Integer Linear Programming (ILP). The problem is formulated as a multi-objective binary program: maximise total scheduled contact time across the fleet while simultaneously minimising the worst-case revisit gap (the longest gap between successive contacts) for any individual satellite. The two objectives are combined as a weighted sum and solved to proven optimality by the HiGHS MILP solver via PuLP 4.x.

**ILP formulation:**
- **Decision variables:** x_i ∈ {0, 1} — whether contact window i is scheduled (284 binary variables)
- **Station exclusivity constraint:** x_i + x_j ≤ 1 for each conflict pair (i, j) — one antenna per station, no simultaneous contacts (5 conflict pairs)
- **Gap linearisation (big-M, M = 86400 s):** 260 auxiliary continuous variables g_k track the active gap for each consecutive satellite pair; G_max tracks the fleet-wide maximum
- **Objective (maximise):** α × Σ(duration_i × x_i) / 100 − β × G_max / 100, with α = 1.0 (contact weight) and β = 2.0 (gap penalty; β > α means gap minimisation is prioritised)

| Metric | Value |
|---|---|
| Solver | HiGHS via PuLP 4.x |
| Solver status | Optimal |
| Windows scheduled | 259 / 284 |
| Total contact time | 106,463.8 s (29.57 h) |
| Worst-case revisit gap | 5,956.4 s (1.65 h) |
| Mean contact per satellite | 4,436 s |
| Min contact per satellite | 3,791 s |

**Ground station utilisation:** London 14.65 h | Lagos 7.88 h | Nairobi 7.05 h

**Key finding:** With β = 2α, the ILP trades a small reduction in total contact time against a significantly improved worst-case revisit gap relative to an unconstrained greedy schedule. The 25 unscheduled windows are all station-conflict casualties — windows whose time slots were contested by a higher-value assignment at the same antenna. Tromso is excluded from scheduling (0 passes, inclination blackout established in Scenario 06).

**Two-step workflow:** Step 1 — run `11_ilp_contact_data.script` in GMAT to generate 24 contact window files into `output_sc11\`; Step 2 — run `11_ilp_contact_scheduler.py` to solve the ILP.

**Outputs:** `schedule_output.txt` (chronological schedule + per-satellite summary), `11_ilp_summary.txt` (formulation detail + solver statistics), `11_schedule_gantt.png` (Gantt chart, coloured by station).

---

## Tools and Tech Stack

| Tool | Role |
|---|---|
| GMAT R2022a | Orbital propagation, manoeuvre planning, contact analysis, finite burn targeting |
| Python 3 | Pre-computation of delta-V, drift rates, burn durations, ILP formulation, plot generation |
| NumPy / SciPy | Numerical integration, orbital mechanics calculations |
| PuLP 4.x / HiGHS | Integer Linear Programming — contact scheduling optimisation (Scenario 11) |
| Git / GitHub | Version control and portfolio hosting |

---

## Repository Structure

```
GMAT_portfolio/
├── README.md
├── LICENSE
├── scenario_01_leo_ground_track/
├── scenario_02_ground_station_access/
├── scenario_03a_coplanar_isl_2sat/
├── scenario_03b_coplanar_isl_6sat/
│   └── output/
├── scenario_04_interplanar_isl/
│   └── output/
├── scenario_05_hohmann_orbit_restoration/
├── scenario_06_walker_constellation/
│   └── output/           (24 contact reports + HTML summary)
├── scenario_07_finite_burn_hohmann/
├── scenario_08_geo_ewsk/
├── scenario_09_geo_ewsk/
├── scenario_10_leo_conjunction/
└── scenario_11_contact_scheduling_ilp/
    ├── 11_ilp_contact_data.script
    └── output_sc11/      (24 contact window files generated by 11_ilp_contact_data.script)
```

---

## Planned Scenarios

| # | Scenario | Skill |
|---|---|---|
| 12 | GEO EWSK with Prolonged Single Arc Burn | Extended finite burn EWSK, burn arc sizing |

---

## Licence

Scripts and Python code: MIT Licence.
GMAT output files: generated data, no licence restriction.
