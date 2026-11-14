# Healthy-model assumptions and limits

The current scope is [NASA_MONITORING_PLAN.md](../NASA_MONITORING_PLAN.md). The registry is the executable inventory; [channel_catalog.md](channel_catalog.md) lists its units, specimen/device and policy. [ranges.md](../ranges.md) supplies clinical interpretation and source qualifications. None of these synthetic waveforms has been validated against an individual astronaut's telemetry.

## Time and collection

The active frequency authority is [frequency_table.md](frequency_table.md), interpreted in [frequency_mapping.md](frequency_mapping.md), and implemented in `frequency.py`. This supersedes earlier six-second sampling and sparse NASA research-session defaults. NASA examples remain evidence about actual study protocols, not the active simulator's requested cadence.

Run day 0 begins at `start`; routine hours are relative to that boundary. HR and HRV use complete 60-second windows, once per minute; respiration also uses 60 seconds. Initial result phases are 60, 61 and 77 s respectively. Scalar temperature, SpO2, CO2, light, dose rate and SPE are 1 Hz with independent phases. Sweat flow/concentration are 1 Hz only while active/wet; 60-second local sodium-loss windows publish once per minute. CGM evaluates 5-second latent inputs over a complete 300-second reporting window. Integrated monitor dose publishes once per minute.

Mass and spot USG have daily 07:00/18:30 pre/post-activity sessions. Urine volume is completed daily; normalized NTx and baseline change are weekly from a completed 24-hour specimen. Cortisol is at 07:00/11:00/15:00/19:00/23:00 daily; viral results are every 48 hours. Vitamin D remains every 30 days. IL-6 and troponin only use configured assay-event gates, with baseline fixtures by default. Lactate retains the existing exercise-session schedule because the matrix does not specify it. Hourly BP is unbounded by default from 08:00, with an optional finite session and explicitly configured 10 Hz / 180 s stand-test pressure burst.

`lab_delay_s` defaults to 3600 simulation seconds for synthetic lab fixtures. This is an illustrative result-processing delay, not NASA sample-return turnaround. Communication delay is added separately to **all** results. Headers declare result availability and acquisition-window duration. `measured_at` stays at point acquisition/window end. Sending/retrying does not re-date a specimen. A late real-time collection uses actual simulation time, coalesces missed polls, and does not replay fabricated measurements. Its completed window ends at that actual time. A missed finite cuff session emits nothing after its end.

Acceleration scales time, including lab delay and communication delay; network timeout, backoff and shutdown drain remain wall-clock durations. Very high acceleration necessarily coalesces dense wearable polls when the process cannot keep up. Use the sparse research configuration for mission-long demonstrations and moderate speeds for wearable traces. Logical-clock tests exercise exact protocols without wall-time jitter. Set `max_age_s` longer than expected specimen processing plus communication delay; otherwise such results expire by design.

## Physiology and fixtures

All coefficients below are **simulation assumptions** chosen to lie comfortably within the qualified ranges. Source references support interpretation, not the exact waveform coefficients.

| Driver / measurement | Implemented healthy assumption |
| --- | --- |
| Adult baseline | Default 75 kg adult male, resting HR 66 bpm, BP 114/73 mmHg, RMSSD 40 ms, NTx 45 nmol BCE/mmol creatinine, vitamin D 40 ng/mL. Sex and menopause select the appropriate NTx/troponin interval; no other sex/age adaptation is claimed. |
| Routine and activity | Smooth daily moderate work/exercise peak at 17:30 with faster onset and slower recovery. Activity is a continuous model input in [0,1]. There are no sleep/mood channels. |
| HR / respiration / BP | HR adds up to 48 bpm plus a 3 bpm daily component; respiration adds up to 9/min; exercise BP adds up to 18/3 mmHg. Temporal noise is small and bounded. BP and respiration represent acquisition-window estimates, not raw waveforms. |
| HRV | A temporary 60-second NN sequence with pulse peaks localized to a 100 Hz time grid follows modeled HR and a 0.23 Hz respiratory modulation. Actual RMSSD is calculated from adjacent complete NN intervals. Activity gradually lowers its target. No universal disease cutoff is used. |
| Core-equivalent temperature | Baseline 36.85°C, daily amplitude 0.18°C and a 10-minute delayed activity response up to 0.25°C. This is a simplified thermal-lag model, not a calibrated commercial ZHF device. |
| SpO2 | Baseline 98.1%, exercise variation −0.25% plus at most 0.25% correlated noise. Assumes a nominal cabin atmosphere. Environmental hypoxia physiology is deferred. |
| Glucose | Baseline 5.1 mmol/L; smooth meal responses following 08:00/13:00/19:00, peaking about 39 minutes later, with modest exercise effect. This approximates CGM lag and is not a validated insulin/absorption compartment model. |
| Saliva cortisol | Exponential post-waking decline from about 10 nM, an awakening response near +30 min and a low evening floor. Named saliva interval, not ISF or serum; intermediate daytime assessment uses a synthetic curve allowance. |
| Troponin / IL-6 | hs-cTnI baseline about 3.5 ng/L; IL-6 about 1.4 pg/mL with modest delayed activity influence. Selected assay-compatible fixtures; no inflammation or myocardial-injury scenario. |
| NTx / vitamin D | NTx baseline-relative amplitude 3% over 60 days; vitamin D amplitude 0.7 ng/mL over 90 days. No claim that normal astronauts universally follow these trajectories. |
| Hydration | A small activity-related deficit plus daily fluid variation drives body mass, USG and urine-flow suppression. Urine volume integrates a ~2.7 L/day slow flow over a complete day using fixed five-minute midpoint quadrature. This is a phenomenological hydration/replacement model, not a full validated fluid/mass balance or kidney model. |
| Sweat | Local 10 cm² patch, synthetic scaling from a nominal 1.8 m² body area. Local sodium around 42–46 mmol/L; local sodium loss equals local flow times local concentration. Emit only when flow has been sufficient throughout the preceding 60-second interval. No whole-body loss channel or serum sodium inference. |
| Viral results | EBV/VZV saliva and CMV urine are separate Boolean not-detected fixtures. An illustrative limit of 2 copies/reaction is dictionary metadata for this mock assay, not a general clinical limit or cross-virus validation. |

Noise is a seeded, channel/owner-specific mixture of smooth sinusoids. The phase is derived with SHA-256 and a local seeded RNG, so Python hash randomization, polling rate, retries and adding another channel cannot change an existing trajectory. Noise phase caching contains model constants only. A process restart begins a new delivery run; repeated seeds can intentionally reproduce the same synthetic experiment.

## Environment and assessments

CO2 is 250 ±29 Pa, with no dependence on crew count or a crew's collection state. This is a compartment fixture, not a validated ventilation/metabolic mass-balance simulation. Ambient photopic light follows a smooth 0.5–350 lux configured lighting routine. It is not melanopic EDI, at-eye exposure or sleep inference. Pressure is explicit environment configuration for ppm conversion.

The monitor dose-equivalent rate is `base_rate * (1 + 0.12*sin(2π*t/5400))`; its integral is analytic, nonnegative and monotonic. The 90-minute modulation is a synthetic orbital demonstration. The same latent rate produces rate and integrated outputs, so skipped polls do not lose dose. The counter includes only configured initial **monitor** dose and this run's integral; it is never personal career effective dose. No Sv/Gy conversion is assumed. SPE is false with a configurable heartbeat; disease/event switching remains deferred.

The generator emits measurements only. Result evaluation, severity labels, clinical thresholds and diagnosis belong to the receiving backend.

The CO2 reading's local synthetic baseline band is 150–350 Pa. It is **not** an implementation of NASA's completed one-hour ≤400 Pa compliance window. The backend owns that averaging and exposure history, so no partial first-hour window can appear compliant by default.

## Memory, delivery and ownership

Production keeps one scheduler event per owner/acquisition group, per-channel sequence counters, fixed model parameters, at most `queue_capacity` queued observations and one in-flight request. Lab delays live in that same bounded queue. Queue overflow removes the oldest acquisition, finite retries reuse the payload and idempotency key, and expiry is measured from acquisition (including laboratory time). Operational stderr contains only run setup and aggregate counters. It never contains measurement JSON or authentication credentials.

HTTP 2xx acknowledges delivery. Connection/timeout errors and HTTP 408/425/429/500/502/503/504 retry up to `max_attempts`; other responses fail immediately. Backoff uses wall seconds. Numeric Retry-After is supported and capped at 60 seconds; HTTP-date Retry-After currently falls back to configured backoff. A single asynchronous sender limits concurrent requests; bounded overflow is the deliberate behavior when generation exceeds receiver capacity. There is no guaranteed durable/exactly-once delivery. The receiver must deduplicate the stable idempotency key.

Normal mode has no inbound HTTP server or medical-history API. Explicit `--preview` instead uses a read-only loopback JSON server and bounded latest-value RAM state, replacing outbound backend delivery; lab/communication delays still apply. Configuration and dependency/build/test caches are files, but measurements, pending requests, raw histories and checkpoints are not written to disk. Static dictionary export is an explicit user command. Tests retain example observations in RAM only. Backend history, dictionary serving, exposure attribution and clinical analysis remain separate responsibilities.


## Dehydration / electrolyte review

The implemented hydration inputs follow the updated PDF page 2 row: body-mass loss, urine specific gravity, local sweat rate and local sodium flux, with concentration and 24-hour urine volume alongside them. The mass comparison is `(mass / configured_mass - 1) * 100%`; negative means mass loss, positive means mass gain. Neither is automatically a measured water deficit or retention. The existing acquisition schedules are retained: daily pre/post mass and spot USG, daily completed urine volume, weekly timed NTx, and sweat only while the active patch is wet. Unsampled values remain awaiting, never fabricated to fill missing samples.

Local sweat reference flow defaults to `0.42/1800 L/h` and reference sodium to `44 mmol/L`; reference flux is their product. These are synthetic patch references near moderate activity, not clinical cutoffs or measured preflight baselines. They are configurable per astronaut as `sweat_reference_rate_l_h` and `sweat_reference_sodium_mmol_l`. Compare like activity and collection conditions. Baseline comparisons are preview context only and do not introduce new backend biomarker channels or change the four-field POST body. The PDF's >2% acute loss and USG >1.020 screening statements are visible as research context; generic USG reference intervals and clinical limitations remain in ranges.md.


## Local JSON inspection

The optional preview exposes the latest available result per owner/channel, along with source-unit and configured-baseline context, in a JSON snapshot. It does not retain historical observations or run frontend code. The root path, `/readings` and `/json` return the same schema; `/dictionary` contains measurement and timing metadata. Backend POST delivery and its four-field JSON body are independent of preview mode.
