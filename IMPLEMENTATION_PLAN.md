# Python astronaut telemetry simulator: implementation plan

> **Frequency update:** [docs/frequency_table.md](docs/frequency_table.md) is now the sampling authority. [docs/frequency_mapping.md](docs/frequency_mapping.md) records the active raw/windowed/clinical interpretation and overrides the older interval tables and six-second settings retained below for research/design history.

> **Superseded scope and schedules:** use [NASA_MONITORING_PLAN.md](NASA_MONITORING_PLAN.md) for the updated 10-page PDF, included biochemical/vital channels, independent environment stream, NASA evidence and proposed acquisition intervals. This earlier plan is retained for design history. Its instructions to implement every README row, sleep/mood/EEG, sensor physics and derived diagnostic outputs do not apply to the current scope. Its push-only/no-persistence architecture and type-hint/documentation requirements remain applicable where consistent with the new plan.

## 1. Scope and outcome

Build a Python service that simulates every measurement channel in `readme.md`, maintains independent collection times, and POSTs each new reading to the receiving backend in place of a real NASA data source. This is a push-only generator with no persistent telemetry storage, inbound telemetry API, or NASA connection. The first version represents one healthy astronaut with a regular sleep, meal, work, and moderate exercise routine. Disease scenarios and scenario-switching controls are explicitly deferred.

Use `docs/backend_contract.md` as the response-contract source. Emit only `channel`, `value`, `unit`, and `measured_at`. Result evaluation belongs to a separate backend.

This document is a plan only. Implementation will include source code, configuration, tests, runnable examples, and documentation.

## 2. Establish a complete typed channel registry

Create a registry before writing generators. It will be the single source for channel identifiers, units, schedules, generators, dictionary metadata, and outbound routing. Map every row in the README to one or more channels or an explicit backend-owned output. Keep stable identifiers from `nigelNote.md` and existing PDF channels where practical.

Suggested channel inventory:

| Group | Channels to register | Implementation approach |
| --- | --- | --- |
| Biochemical | `glucose`, `cortisol`, `troponin_i`, `lactate`, `bone_ntx_pct_baseline`, `vitamin_d_25oh`, `sweat_sodium_flux`, `viral_shedding_status` | Smooth biochemical trajectories; slow trends for NTx and vitamin D; negative shedding fixture in the healthy profile. |
| Cardiovascular | `heart_rate`, `hrv_rmssd`, `bp_systolic`, `bp_diastolic`, `spo2` | Shared activity, recovery, sleep, and posture context with channel-specific responses. |
| General physiology | `body_temperature`, `respiratory_rate`, `body_mass`, `urine_specific_gravity`, `urine_volume_24h`, `sweat_rate` | Circadian variation, hydration balance, activity, meals, and rolling accumulation where appropriate. |
| Fluid distribution | `segmental_bioimpedance`, `cephalic_fluid_index` | Regional impedance measurements and a documented synthetic index mapping; do not claim a validated diagnostic mapping. |
| EEG | `eeg_power_spectral_density`, `eeg_theta_power`, `eeg_alpha_power`, `eeg_theta_alpha_ratio` | Generate a consistent spectrum, integrate its bands, and derive the ratio from those powers. |
| Sleep | `actigraphy`, `sleep_stage`, `sleep_duration`, `sleep_efficiency`, `sleep_debt` | One sleep timeline drives observations and summaries. |
| Performance and questionnaires | `pvt_reaction_time`, `pvt_lapse_count`, `phq9_score`, `gad7_score`, `mood_score`, `headache_flag` | Reaction-time trials within scheduled test sessions; scheduled questionnaire fixtures. Mood scale must be explicitly defined as synthetic. |
| Vision and exercise | `visual_acuity_logmar`, `amsler_grid_result`, `exercise_compliance` | Scheduled assessment fixtures and compliance derived from completed planned exercise. |
| Kinematics | `joint_kinematics`, `left_knee_flexion`, `right_shoulder_abduction`, `lumbar_asymmetry_ratio`, `form_status` | A shared movement model covering elbow, wrist, knee, shoulder, and lumbar movement; scalar channels are projections of that model. |
| Environment | `ambient_ppco2`, `light_exposure`, `radiation_dose`, `dose_rate`, `spe_flag` | Healthy environmental profile, lighting schedule, nonnegative radiation rate, cumulative dose integration, no SPE. |
| Hydrogel | `hydrogel_displacement`, `hydrogel_strain`, `hydrogel_resistance`, `hydrogel_delta_r_over_r0`, `hydrogel_gauge_factor` | Derive all quantities from the same motion state and the declared sensor calibration. |
| GFET | `gfet_delta_ids_over_i0`, `gfet_threshold_voltage_shift` | Cortisol binding formula; explicitly documented synthetic calibration for the incomplete troponin model. |
| Additional derived observations | `postural_sbp_drop`, `postural_hr_rise`, `shock_index`, `body_mass_weekly_slope`, `ntx_resorption_slope`, `cortisol_diurnal_slope`, `estimated_icp` | Compute where sufficient inputs exist. An ICP estimate requires a labelled synthetic calibration because the PDF supplies none. |
| Clinical scores | `news2_score`, `qsofa_score` | Implement only after establishing cited component definitions and adding any missing prerequisite channels. Healthy defaults alone are not a scoring algorithm. |

The CFE channel is `eeg_theta_alpha_ratio`; do not generate a second independent CFE value. NTx percent change needs a precise convention: zero means unchanged from baseline, rather than 100 meaning baseline.

Array/object-valued channels are necessary for regional impedance, EEG spectra, actigraphy windows, and joint vectors. Specify their shapes through typed models and the dictionary; keep scalar measurements individually identified by channel. A shared physical acquisition may produce several dependent outputs with the same timestamp. Independence does not require artificially separating measurements that belong to one acquisition.

`overall_status`, `primary_hazard`, and `recommended_actions` remain the analysis backend's outputs. Account for them in the coverage manifest, but do not manufacture diagnostic advice in the sensor simulator. Derived observations above can support integration and consistency checks without taking over that decision engine.

## 3. Freeze units and JSON contracts

Use SI units on the wire as requested by the note, with explicit metadata. Use conventional clinical units in profile configuration where convenient, then convert at the boundary. Examples: pressure in Pa, temperature in K, time in s, angles in rad, and mass in kg. Select and document precise SI-compatible concentration, flow, and rate conventions for each channel. Dimensionless ratios, questionnaire scores, flags, and statuses need explicit encodings rather than fabricated units.

The value `118` in the note's BP example appears to be mmHg, so it must not be silently described as Pa. Channel identifiers inherited from the PDF that contain a unit suffix need either that exact unit or an explicit rename; never change their meaning silently. The NTx percentage convention is one such case and must be declared in the dictionary.

Preserve this single-reading envelope:

```json
{
  "channel": "bp_systolic",
  "value": 15732.0,
  "unit": "Pa",
  "measured_at": "2026-11-08T07:12:00Z"
}
```

This example is approximately the note's 118 mmHg expressed in Pa. `measured_at` is acquisition time in UTC, not HTTP request time, calculation completion time, or retransmission time.

Extend the channel dictionary while retaining all required fields from the note:

- Environment: `id`, `gravity_g`, `comm_delay_s`.
- Each channel: `channel`, `name`, `domain`, `body_regions`, `explanation`.
- Additional explicit metadata: `unit`, `value_schema`, state-dependent sampling rules, expected freshness, citations, baseline provenance, and whether the value is measured, derived, or a synthetic assessment/calibration.
- Citations identify the PDF page for extracted requirements and the primary reference for any added ranges or scoring rules. Unsupported choices are labelled simulation assumptions.
- Include dictionary/profile version identifiers in startup metadata; the receiving backend owns dictionary serving and caching. Do not add an environment-switching UI in this version.

Result evaluation and severity classification belong to a separate backend. The simulator emits measurements without local assessment policies.

## 4. Model natural, coherent healthy behavior

Create a typed `AstronautProfile`, a daily routine, and a shared physiological context evaluated at simulation time. A configurable random seed and separate random streams per channel make runs reproducible; adding a channel must not change existing channels' noise sequences.

Use a baseline plus smooth circadian variation, activity/meal responses, gradual recovery, and small time-correlated measurement noise. Noise evolution must account for elapsed time so changing the polling interval does not change the underlying physiology. Avoid independent uniform random draws and abrupt resets at state boundaries.

Model relationships explicitly:

- Activity influences HR, respiratory rate, HRV, sweat, lactate, and movement through separate response and recovery times.
- Meals influence glucose through smooth rises and recovery; cortisol follows a daily rhythm instead of constant noise.
- Hydration connects intake, sweat, body mass, urine output, specific gravity, and sodium flux.
- Sleep drives actigraphy, stage progression, light exposure, sleep summaries, and performance context.
- Bone and vitamin-D trends change slowly; a fast polling schedule must not imply fast biochemical change.
- Radiation dose is the integral of dose rate, with unit conversion and a configured starting mission dose.
- EEG power, band integrals, and theta/alpha ratio agree; do not apply an awake fatigue threshold blindly to normal sleep.
- Hydrogel and GFET outputs follow their source motion/concentration, rather than being separately randomized.

Healthy means plausible, state-appropriate behavior, not every value frozen in the middle of a range. Choose a conservative activity routine compatible with the intended healthy demo. Do not distort physiology merely to force every context-free alert rule to return normal. Expose mismatches between source thresholds and normal exercise/sleep as documented policy issues.

Before implementation, research primary sources for missing healthy baselines, units, and clinical scoring definitions. Record population, sample medium, state, and limitations where relevant; cortisol in different sample media is not interchangeable. The supplied PDF is a project requirement, not sufficient evidence for every physiological model. No new numerical healthy ranges are asserted by this plan.

For unknown sensor mappings, define a deterministic, bounded synthetic calibration, cite the missing specification, and label its output accordingly. In particular, review the troponin Debye formula's dimensions and sign as well as its missing concentration-to-bound-density relationship. Do not claim physical validation.

## 5. Schedule each channel independently

Use an `asyncio` scheduler with a priority queue of next-due events. Each channel has its own interval policy, initial phase offset, next collection time, minimal transient model state, and sequence number. Use a monotonic clock for waiting and an injectable simulation clock for physiological time and UTC timestamps.

Initial phase offsets prevent synchronized bursts. Optional bounded timing jitter represents collection variability; keep the safety domain at its prescribed 1 Hz. Timing is independent of measurement noise. The same-domain channels may have equal intervals but different phases; distinct domains naturally have different intervals.

| Domain | Active | Resting | Sleeping | Policy |
| --- | --- | --- | --- | --- |
| Radiation / SPE | 1 s | 1 s | 1 s | Continuous safety collection. |
| Cardiovascular | Channel-specific 15–30 s | 300 s | 900 s | Preserve the PDF intervals; use separate phases. |
| Sweat / movement | 60 s | 900 s | Paused | Resume without replaying every missed collection. |
| Passive fluid tracking | 60 s | 900 s | Configurable slow collection | Explicit resolution of the PDF's conflicting sleep instructions; document the selected default as an assumption. |
| Glucose / lactate / cortisol / NTx | 300 s | 1800 s | 3600 s | Preserve slow biological evolution between readings. |
| EEG | 900 s | 3600 s | 3600 s | Schedule actigraphy separately. |
| Actigraphy | Configurable | Configurable | Continuous, discretized into configured epochs | PDF does not specify an acquisition frequency. |
| PVT | Daily scheduled session while awake | Daily scheduled session while awake | No tests | Individual trials belong to a 5-minute session; 15/60-minute availability checks must not invent new test results. |
| Questionnaires, lab-like markers, eye tests, other inputs | Individually configured | Individually configured | Defer nonessential assessments | Fill missing schedules explicitly in configuration; distinguish assumptions from PDF requirements. |

On a state change, recompute next due times without creating a synchronized collection burst. Serialize updates within each channel. If acquisition is late, record its actual acquisition time and schedule the next event according to a documented skip/coalesce policy; do not backdate fabricated real-time measurements.

A due collection creates one immutable reading and hands it to the outbound sender. Paused channels emit nothing. Sending and retrying never create new measurements or advance physiological random streams.

Derived observations use shared model state at acquisition time or minimal dependency values and timestamps held temporarily in RAM. Apply age/skew tolerances to sampled dependencies. Document dependency/window provenance in transport metadata; a calculation or retry must not make old inputs appear fresh.

Compute windowed measurements such as 24-hour urine volume and weekly slopes from the model over a defined interval or from bounded running summaries, without retaining raw telemetry history. Label model-derived pre-start windows synthetic, or wait for a complete interval. Keep only transient model variables, counters, accumulators, and a bounded delivery buffer in RAM. All are discarded on exit. There is no database, telemetry file, persistent queue, historical archive, or measurement-payload logging.

## 6. Push-only backend delivery and ownership

Run a Python worker with `asyncio`, Pydantic validation, and an asynchronous HTTP client such as `httpx`. No FastAPI server or inbound biomarker endpoints are needed. The receiving backend owns ingestion APIs, storage, history, analysis, and frontend access.

```text
Healthy physiological model
    -> independent per-channel collection schedules
    -> validated JSON reading
    -> bounded in-memory delivery buffer
    -> HTTP POST to receiving backend
```

Use one configurable backend ingestion URL by default: the `channel` field identifies the biomarker. Every biomarker does not need its own endpoint. If the backend requires separate routes, support a channel-to-URL mapping without changing generators. Supply actual receiver routes through configuration when its contract is available.

| Responsibility | Owner |
| --- | --- |
| Generate readings and set acquisition timestamps | Simulator |
| POST each reading in the note's four-field JSON envelope | Simulator |
| Ingestion endpoint and durable telemetry/history storage | Receiving backend |
| Dictionary serving and caching | Receiving backend; simulator supplies a static metadata manifest or configured startup registration |
| Health-history uploads and baseline extraction | Receiving backend |
| Diagnosis, overall status, hazards, and recommended actions | Receiving backend |

The health-history upload mentioned in `nigelNote.md` belongs to the receiving backend. Start with a configured synthetic healthy baseline. A later integration can accept a validated baseline profile supplied by that backend; do not import, retain, or expose raw medical history in this worker.

POST each new reading immediately, subject to communication delay and sender capacity. The PDF's repeated 1-second latest-value snapshot broadcast is superseded by this event-driven requirement. A 1 Hz channel generates each second; a 300-second channel generates every 300 seconds. Do not repeatedly broadcast old values to fill a shared tick.

Run delivery outside the sampling loop with timeouts, bounded retry attempts/backoff, a maximum pending-reading age, and a bounded RAM queue. Retry transient connection errors, throttling, and appropriate server errors; report permanent payload/authentication errors without endless retries. Preserve timestamps and payloads during retries. Use a stable idempotency header if supported by the backend, incorporating a per-run identifier and per-channel sequence number.

On queue overflow, discard the oldest pending reading and increment a dropped-reading counter. Also discard and count expired readings and exhausted retries. After recovery, resume current delivery without an unbounded backlog. A request may time out after the backend accepted it, so the receiver should deduplicate retries. Durable or exactly-once delivery is not promised.

Report operational counters and transport errors without logging measurement payloads. On shutdown, allow a bounded drain period and discard remaining pending readings. Restart begins a fresh configured run; there is no checkpoint or recovery of unsent readings.

## 7. Python structure, type hints, and comments

Suggested package layout:

```text
pyproject.toml
config/healthy.yaml
src/imitacija/
    main.py                 # Worker startup, configuration, and graceful shutdown
    models.py               # Typed readings, metadata, and baseline configuration
    registry.py             # Complete channel definitions and coverage mapping
    clock.py                # Real-time and accelerated/test clocks
    scheduler.py            # Independent sampling and state transitions
    physiology.py           # Shared healthy context and daily routine
    generators/             # Biochemical, vital, EEG, motion, environment models
    derived.py              # Formula-based observations and dependency policies
    units.py                # Explicit conversions between profile and wire units
    baseline.py             # Synthetic healthy profile validation
    delivery.py             # Required HTTP POST transport and bounded RAM retries
tests/
docs/channel_catalog.md
docs/model_assumptions.md
```

Use type hints on all functions and methods, including return values. Define typed configuration and immutable measurement records, and `Protocol` interfaces for clock, generator, and transport. Represent scalar and structured readings with explicit typed models; avoid unvalidated `dict[str, Any]` payloads.

Write module and public-function docstrings explaining responsibilities, units, time semantics, formulas, and failure behavior. Add thorough comments around correlated noise, state transitions, timestamp retention, unit conversions, dependencies, and calibration choices. Comments should explain why the model behaves that way and cite assumptions; they should not just paraphrase assignments. Include worked examples showing two channels sampled at different times.

Run static type checking with mypy and lint/format checks with Ruff. Pin compatible dependencies during implementation and document the supported Python version and commands.

## 8. Verification and acceptance criteria

Use a fake clock and fixed seeds so tests do not require hours of wall-clock waiting.

- **Coverage:** every README row maps to implemented channels or the explicitly backend-owned decision outputs. Every registered channel has an outbound route, type, unit, schedule, source/assumption,.
- **JSON contract:** valid JSON, exact reading field names, valid enum values, timezone-aware UTC timestamps, and dictionary metadata matching the registry.
- **Independent timing:** two channels with unequal periods and offsets collect at the expected distinct times. Delivery latency and retries do not alter collection schedules or values. State transitions, pauses, late collection, and resume behavior are deterministic.
- **Healthy dynamics:** accelerated multi-day runs show smooth variation, recovery, sleep/meal patterns, plausible state-dependent values, and no unintended illness scenario. Check correlations, maximum change rates, and boundaries as well as means.
- **Physical consistency:** glucose and SI conversions; systolic BP greater than diastolic BP; nonnegative fluxes; accumulated dose; EEG band integrations; cortisol GFET formula; hydrogel strain/resistance relations; windowed totals and trend calculations.
- **Derived freshness:** missing/stale dependencies defer calculations; old readings never acquire new timestamps merely through calculation or retransmission.
- **Baseline configuration:** invalid profiles and units fail validation; the default healthy profile needs no uploaded medical records.
- **Delivery resilience:** a local fake receiving backend verifies routing, timeouts, retry identity, out-of-order arrivals, retained timestamps, continued sampling during outages, bounded memory, queue overflow, expiry, and shutdown behavior.
- **Reproducibility:** identical seed, profile, start time, and configuration produce the same acquisition sequence; changing delivery latency or retries has no effect on generated values.
- **No storage:** operation writes no measurements to disk, logs, databases, or persistent queues; acknowledged/expired readings leave the delivery buffer, and restarts recover no prior telemetry.
- **Documentation:** include worker startup instructions, destination/authentication configuration, outbound JSON examples, independent timing, retry/drop semantics, and cited requirements versus simulation assumptions.

## 9. Execution order and future extension

1. Complete the channel coverage manifest, research missing model definitions, and record unit/sampling/calibration decisions.
2. Define typed configuration, JSON schemas, the registry, and contract tests.
3. Implement the injectable clock, shared healthy context, and independent scheduler with timing tests.
4. Implement all channel generators and consistent derived observations; validate an accelerated healthy run.
5. Add required outbound delivery, configurable receiver routing, and transient retries; verify with a fake receiver.
6. Verify no telemetry persistence, bounded memory, operational counters, and graceful shutdown.
7. Run coverage, type/lint, consistency, JSON-contract, and integration checks; finish user documentation and runnable examples.

Keep healthy physiology behind a small model interface accepting time, profile, and context. A future scenario engine can change physiological drivers gradually while preserving the scheduler and outbound JSON contract. Do not implement diseases, disease presets, disease switching, or scenario-control endpoints now.
