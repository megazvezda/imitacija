# Active frequency-table mapping

[frequency_table.md](frequency_table.md) now takes precedence over the earlier six-second override and the original NASA-inspired simulator intervals. The executable mapping is `src/imitacija/frequency.py`. These are project timing requirements; adopting them does not establish that NASA operates these exact sensors or intervals.

## Startup override

The user-requested run-start initialization supersedes waiting for a channel's first scheduled session: every enabled owner/channel emits one immediately available `startup_baseline` at time zero, then follows the normal schedule below. This includes assays with empty event lists, unless the channel itself is disabled. Startup replaces any event already at time zero; later event times and periodic/calendar phases are not shifted. Startup values have no completed collection window and bypass laboratory processing delay; communication delay still applies. See [backend_contract.md](backend_contract.md#startup-initialization) for provenance and aggregate-window interpretation.

## Acquisition versus publication

The matrix contains three different layers. Raw acquisition describes a sensor input; windowed publication describes a computed measurement; clinical evaluation describes analysis of those measurements. A 100 Hz PPG input is not 100 independent heart-rate or RMSSD results per second.

The current service publishes its implemented scalar channels as follows. All durations are **simulation time**. Acquisition phase offsets remain independent; laboratory processing and communication delays still apply after collection.

| Implemented channel(s) | Raw model input / acquisition | Published acquisition schedule |
| --- | --- | --- |
| `heart_rate` | 100 Hz PPG timing tier | Once per minute, complete 60-second estimate; first at second 60. |
| `hrv_rmssd` | Synthetic beat peaks localized on a 100 Hz / 10 ms grid | Once per minute from a complete 60-second NN window; first at second 61. |
| `bp_systolic`, `bp_diastolic` | Paired cuff fixture normally; synthetic continuous pressure during explicit stand test | Hourly from configured session start, unlimited session by default. Optional 10 Hz, exactly 180-second burst. |
| `spo2` | 1 Hz scalar pulse-oximetry fixture | Every second, phase 0.2 s. Five-second acute alarm checks belong to the receiving analysis backend. |
| `body_temperature` | 1 Hz core-equivalent fixture | Every second, phase 0.4 s. |
| `respiratory_rate` | Estimated over 60 seconds | Once per minute; first complete window ends at second 77. |
| `glucose` | One latent interstitial sample every 5 s (0.2 Hz) | One five-minute mean every 300 s; first at second 343 after a complete window. Averaging is the simulator's declared processing choice. |
| `sweat_rate`, `sweat_sodium_concentration` | 1 Hz during active, wet sampling; no resting acquisition | Every second while available. |
| `sweat_sodium_flux` | Complete preceding 60 samples of local flow × local sodium | Once per minute while active/wet, expressed as the mean loss rate over that window. |
| `body_mass` | Prompted mass-device fixture | Daily pre/post-activity sessions at 07:00 and 18:30. These are chosen example times for the matrix's daily sessions. |
| `urine_specific_gravity` | **Spot urine**, separately prompted | Daily 07:00 / 18:30, independent of 24-hour urine collections. This channel no longer represents a composite 24-hour specimen. |
| `urine_volume_24h` | Integrated urine flow over one completed day | Daily, first at elapsed day 1. Use exact 24 h, not literal 25 h implied by rounding 1/24 to 0.04 per hour. |
| `urinary_ntx`, `bone_ntx_pct_baseline` | Completed timed-urine fixture | Weekly, first at elapsed day 7; weekly is the selected option from “weekly/monthly.” Both outputs share the specimen timestamp. |
| `vitamin_d_25oh` | Serum laboratory fixture | Baseline then every 30 days; 30 days is the simulator's monthly convention. |
| `cortisol_saliva` | Scheduled saliva assay, no continuous raw stream | Every four waking hours: 07:00, 11:00, 15:00, 19:00 and 23:00 daily. Slope remains backend-derived. |
| `viral_ebv_detected`, `viral_vzv_detected` | Scheduled saliva PCR | Every 48 h at 09:00, selecting the matrix's daily/48-hour option. |
| `viral_cmv_detected` | Scheduled urine PCR | Every 48 h at 10:00; an explicit adaptation for the existing urine channel, not saliva. |
| `il6_serum` | Gated serum assay fixture, not a proven continuous GFET | Only configured assay events; default one synthetic baseline. The matrix gives no numerical gate, so the simulator does not invent an infection trigger. |
| `troponin_i` | Event-driven assay fixture | Only configured assay events; default one synthetic baseline. |
| `lactate` | Existing exercise-test plasma fixture | Unchanged: baseline plus configured pre-test/recovery sessions. The matrix does not specify lactate timing. |
| `ambient_ppco2` | 1 Hz | Every second. Five-second acute checks and hourly exposure trends remain backend-owned. |
| `ambient_light_lux` | 1 Hz photopic light | Every second, phase 0.6 s; no sleep inference. |
| `ambient_dose_rate` | 1 Hz monitor dose-equivalent model | Every second by default. |
| `spe_flag` | 1 Hz event heartbeat | Every second, phase 0.8 s, independently of crew activity. |
| `ambient_integrated_dose` | Integral of the same latent radiation rate | Once per minute, first at second 60. Hourly mission/career-dose review remains analysis work; this monitor counter is not personal effective dose. |

PPG is represented by procedural beat timing with 10 ms peak localization, not a validated optical waveform or an exposed raw PPG channel. CGM and sweat windows evaluate their latent input samples on demand and discard the temporary calculation. This preserves the timing distinction without retaining raw telemetry. There is no continuous raw-waveform API.

## Optional tests and gated collections

The default BP session begins at 08:00 and repeats hourly indefinitely. `bp_session_duration_s` can still restrict it to an explicit finite session. Set `stand_test_start_s = 600` to request a 10 Hz paired-pressure burst over `[600, 780)` seconds. This is synthetic continuous pressure, **not ten cuff inflations per second**; it does not introduce illness or a POTS diagnosis. No burst runs by default.

`il6_event_times_s = [0, 43200]` schedules a baseline and one explicitly requested IL-6 collection. An empty list disables later scheduled assays; the mandatory startup baseline is still emitted. `troponin_event_times_s` follows the same convention. Configured event lists are the gates; no clinical rule or mandatory two-hour exercise exclusion is inferred from the word “gated.” Result availability remains delayed by `lab_delay_s`, which is separate from sampling frequency.

`radiation_interval_s` and `spe_heartbeat_s` default to 1 s. Explicit configuration overrides remain supported and appear in the dictionary. A deliberately different configured interval is a project override of the matrix default.

## Names, scope and analysis ownership

Stable channel identifiers remain in place: matrix `hs_ctni` → `troponin_i`; `zhf_core_temp` → `body_temperature`; `il6` → `il6_serum`; `cabin_co2` → `ambient_ppco2`; `sweat_sodium` → `sweat_sodium_concentration`; `urinary_ntx_pct_baseline` → `bone_ntx_pct_baseline`; `dose_rate` / `radiation_dose` → the explicitly ambient monitor channels. Latent shedding remains separated by virus and specimen.

This task tunes existing channels. The table's unimplemented fluid-intake prompts, urine calcium, activity counts, EEG/PVT, mood, sleep, kinematics, visual tests and cephalic/ICP measurements are not silently added. NEWS2/qSOFA/SIRS, shock index, hydration balance, cumulative sweat-volume summaries, circadian/slope features, five-second alarm decisions and hourly trend reviews belong to the backend. Existing local sodium-loss rate is windowed, but no extra cumulative sweat-volume channel is introduced.

The dictionary exposes `raw_acquisition_hz`, `frequency_matrix_rows`, `frequency_basis`, actual collection schedule and observation-window duration. JSON-preview refresh, HTTP retry/backoff, laboratory availability and measurement acquisition remain separate clocks. Accelerated previews may omit intermediate 1 Hz results between JSON-preview refreshes. After the separately labelled startup fixture, not-yet-available scheduled windows remain absent; no regular readings are fabricated to fill a shared tick.
