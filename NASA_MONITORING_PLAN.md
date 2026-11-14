# NASA-informed biomarker simulation plan

> **Frequency update:** [docs/frequency_table.md](docs/frequency_table.md) is now the sampling authority. [docs/frequency_mapping.md](docs/frequency_mapping.md) records the active raw/windowed/clinical interpretation and overrides the older interval tables and six-second settings retained below for research/design history.

Reviewed: **2026-11-14**. This is the current implementation scope and overrides the older all-channel inventory and plan. Source specification: [updated 10-page PDF](Tiered%20Master%20System%20Specification%20%26%20Implementation%20Plan%20%281%29-1.pdf). Clinical evidence and detailed interpretation remain in [ranges.md](ranges.md); transport fields come from [nigelNote.md](nigelNote.md).

## 1. Deliverable and scope

Build a typed Python worker that generates healthy synthetic biochemical measurements and vital signs, and POSTs each newly acquired reading to a separate analysis backend. Environmental generators run independently, once per compartment/sensor, rather than once per astronaut. No database, telemetry files, historical API, or disk-backed retry queue. Short-lived model state, running accumulators and bounded in-memory delivery queues are permitted. This document is the plan; disease scenarios and their switching controls remain future work.

| Decision | Channels / functionality |
| --- | --- |
| Include biochemical measurements | Glucose, cortisol, hs-cTnI, lactate, urinary NTx, 25-OH vitamin D, **IL-6**, sweat sodium concentration/flux, and virus-specific shedding results. Vitamin D remains required by the existing README even though the updated PDF emphasizes other markers. |
| Include vital signs | Heart rate, HRV RMSSD, systolic/diastolic BP, SpO2, core-equivalent temperature and respiratory rate. |
| Include objective supporting measurements | Body mass, urine specific gravity, timed urine volume and sweat rate. These support hydration, nutrition and renal interpretations but are not all wearable sensor outputs. |
| Include separate environmental telemetry | Cabin ppCO2, ambient photopic light, radiation dose rate, integrated monitor dose and SPE flag. Cabin pressure is required configuration for converting CO2 to ppm. |
| Exclude from this implementation | Sleep/stages/debt, mood, PHQ-9/GAD-7, PVT, EEG/CFE, headache self-report, visual/Amsler tests, exercise-compliance scores, joint/digital-twin signals, cephalic impedance/index, jugular strain/estimated ICP, hydrogel/GFET electrical outputs. These are outside the revised biochemical/vital-sign scope. |
| Backend responsibilities | Long-term history, trends, clinical scores, multi-marker interpretation, recommendations, and environmental-to-person exposure attribution. NEWS2/qSOFA cannot be completed from these measurements alone because oxygen therapy/consciousness or mentation inputs are missing. |

A known simulation routine may drive meals, exercise and circadian phase. It is an input to the generator, not a claim that sleep, mood or activity has been detected. Resting/exercise context may affect physiological sampling; it must never stop the independent environment tasks.

## 2. What NASA actually documents

Public evidence supports three different acquisition patterns: scheduled medical evaluations, session-based research collections, and ongoing environmental monitoring. It does **not** establish that NASA continuously measures every biochemical marker in this PDF.

Evidence keys for the cadence tables:

| Key | Verified source and applicable schedule | Limits |
| --- | --- | --- |
| M | [NASA OCHMO-STD-100.1A Rev. A, 2024][N1], §6.1.2: health evaluations include temperature, BP, pulse and respiration. Long-mission example: L+14/21, L+90, L+180, L+270 and R−21/14 days, plus as clinically indicated. §6.1.15: mass L+7, then monthly and as indicated. §6.7.1: vitamin D test timing at crew-surgeon discretion. | The standard explicitly describes example schedules. L = launch; R = return. A daily/weekly supplement schedule is **not** a blood-test schedule. |
| V | [Spaceflight Standard Measures program report][N2] includes temperature, BP, pulse, oxygen saturation and respiration in health-status assessments. | Does not establish universal continuous SpO2 or temperature sampling. |
| N | [NASA Nutritional Status Assessment protocol][N3]: blood/24-hour urine sessions at FD15 ±5 days and FD30/60/120/180 ±14 days. | Research collections, not 5-minute sensing. Samples were frozen for later Earth analysis. FD = flight day. Do not assume every assay is performed in every collection without its assay protocol. |
| B | [Norsk et al., primary ISS ambulatory BP study][N4]: a 24-hour in-flight session at FD85–192; BP/HR hourly 08:00–23:00 and every 2 hours overnight. | Eight male participants; one research session, not an operational daily cuff schedule. |
| C | [Mehta et al., ISS cortisol/latent-virus study][N5]: cortisol on sampling days at waking, +30 minutes, +6 hours, +10 hours and retiring; viral sampling used repeated collections around study time points. | Saliva cortisol and saliva/urine PCR, not continuous interstitial sensors. Analysis was performed after sample return. |
| I | [Crucian et al., NASA primary cytokine study][N6]: plasma cytokine collections at FD15, 30, 60, 120 and 180, with pre/postflight sessions. | Research multiplex assay; not a serum clinical IL-6 reference interval or wearable validation. |
| E | [NASA-STD-3001 Vol. 2, current Rev. F (2026), §6.2.5.1, V2 6020][N7]: continuous pressure, humidity, temperature, ppO2 and ppCO2 records per isolatable habitable compartment. | No universal frequency in Hz specified. NASA's recording requirement describes the spacecraft system; storage belongs to our receiving backend. |
| R | [NASA BEAM radiation report][N8]: REM instruments supplied radiation quantities at **1-minute cadence**. | Device-specific example; absorbed dose, dose equivalent and effective dose are different quantities. It does not establish a universal 1 Hz policy. |

The last column below is the **proposed simulator configuration**, not a NASA requirement. Use a declared wearable demonstration plus scheduled synthetic laboratory results. A configurable simulation clock can advance through sparse research sessions without pretending that blood is collected every minute. Distinguish acquisition time, lab-result availability and HTTP delivery time.

## 3. Acquisition plan for every retained crew channel

| Channel identifier / specimen | NASA or spaceflight evidence and actual cadence | Proposed first implementation schedule |
| --- | --- | --- |
| `heart_rate` | M/V periodic medical observations; B session measurements. | Project cadence override: every **6 s (10/min)**, independent of activity. This supersedes the earlier 15/60-second simulator choice; it is not a NASA cadence claim. |
| `hrv_rmssd` | [Primary long-duration cardiac study][N9] used 48-hour Holter sessions, including an in-flight session near R−15. No universal RMSSD publishing period established. | One result per **5-minute** clean beat-interval window. Generate NN intervals internally; sparse 15-second HR values cannot reconstruct HRV. |
| `bp_systolic`, `bp_diastolic` | M clinical checks; B documents hourly/2-hour cuff acquisitions within a study session. | Paired cuff acquisition every **60 min during a configured monitoring session**; no readings outside that session. Same acquisition timestamp for both components. This is a study-inspired demo choice. |
| `spo2` | V health-status observations; no universal continuous cadence verified. | Wearable assumption: **30 s**. |
| `body_temperature` | M/V assessments; NASA routine use of the PDF's particular ZHF device was not verified. | Core-equivalent sensor assumption: **60 s**, with sensor lag and declared measurement site/method. |
| `respiratory_rate` | M/V assessments. | Project cadence override: every **6 s (10/min)**, first result at 31 s after the 30-second observation-window warm-up. Independent phase from other channels. |
| `glucose` — interstitial CGM estimate | NASA reports an [ISS Vascular Aging oral glucose tolerance session][N10]; no routine all-crew CGM interval established. [NIDDK][N11] describes CGM interstitial measurement every few minutes. | **5 min** for a clearly labelled synthetic CGM. Venous fasting/OGTT results would be a separate specimen-specific channel/session; do not apply venous diagnostic rules directly to CGM. |
| `cortisol_saliva` | C: five timed collections per sampling day. | Five scheduled samples on configured collection days using C's relative times. Baseline plus a sampling day every **30 mission days** is a project choice, not C's exact mission schedule. Declare lab delay. |
| `troponin_i` — serum/plasma hs-cTnI | No routine in-flight NASA sampling interval verified in the reviewed public sources. | One explicitly synthetic baseline laboratory fixture; later samples only at configured clinical events. No healthy 5-minute stream. Future repeat testing must follow the selected assay/event protocol. |
| `lactate` — plasma | Spaceflight exercise studies measured lactate during test protocols ([primary example][N12]); no universal routine interval verified. | Baseline plus configured exercise-test samples, e.g. pre-test and 5/15/30 min recovery. Those times are simulation assumptions; a resting lab result is not a sweat-lactate measurement. |
| `urinary_ntx`, `bone_ntx_pct_baseline` | NASA nutrition/bone research includes urine collections (N; [NASA adaptation report][N13]). No continuous urinary NTx sensor cadence verified. | Use N's session days as a **research-inspired schedule assumption**; normalized urinary result and its derived baseline change share a timestamp. Verify specimen collection/creatinine normalization in registry. |
| `vitamin_d_25oh` — serum | M discretionary testing; nutritional research uses session-based collections, not minute-to-minute vitamin monitoring. | Baseline then every **30 mission days**, explicitly a simulator lab schedule. Slow evolution over weeks. |
| `il6_serum` | I documents in-flight **plasma** cytokine research at five session days. Routine serum wearable monitoring is not established. | Serum laboratory fixture at FD15/30/60/120/180, **adapting** I's timing while explicitly using a different declared serum assay. Never claim the research assay validates the serum cutoff. |
| `sweat_sodium_concentration`, `sweat_sodium_flux` | [NASA-funded sweat-sensor development][N14] includes electrolyte/metabolite sensing; funding is not evidence of routine operational deployment. No flight cadence verified. | **60 s while sufficient sweat exists**. Flux derived from concentration and matching local flow; no concentration result from an unfilled/dry sensor. |
| `viral_ebv_detected`, `viral_vzv_detected` — saliva PCR; `viral_cmv_detected` — urine PCR | C studies virus-specific PCR shedding, including repeated/alternate-day saliva collections around time points. No continuous viral sensor established. | Configurable research sessions; four alternate-day saliva samples per demo session. Use a separately configured urine collection for CMV. Demo session every **30 mission days** is an assumption. Include assay detection limit; positive ≠ symptomatic disease. |
| `body_mass` | M: L+7 then monthly and as indicated. | Follow that example schedule; configure additional measurements only for an explicit test scenario. Model the latent hydration state between samples without inventing measurements. |
| `urine_specific_gravity` | Urinalysis/nutrition assessment documented; no universal standalone in-flight USG frequency verified. | One sample per configured **24-hour collection session**, paired with specimen metadata. A spot sample requires a distinct collection method. |
| `urine_volume_24h` | N uses **24-hour collections at specified sessions**, not a new 24-hour result every second. | Publish at the end of each completed collection; retain its window. Do not extrapolate an incomplete collection to a measured full-day total. |
| `sweat_rate` | N14 developmental monitoring; no universal flight frequency verified. | Same **60-second** local acquisition as sodium when sampling is possible. Optional whole-body modeled rate must have a distinct identifier/calibration. |

Keep irregular laboratory schedules explicit. A baseline fixture is a simulator-created result, not an assertion that NASA runs that panel preflight. A result from an earlier collection keeps its original acquisition timestamp; retransmission or display refresh does not create a fresh measurement. Default intervals can have small configurable jitter for wearable acquisition, but protocol windows and paired samples must remain consistent.

## 4. Re-reviewed ranges and severity rules

The table summarizes the current retained scope. [ranges.md](ranges.md) contains the source links and detailed clinical prerequisites for each row; the new IL-6 and NASA vitamin D qualifications have been added there. The units here are conventional source units, not necessarily wire units. **A reference interval is not automatically a critical alarm threshold.**

| Marker | Reference / expected context | Concerning or severe interpretation to retain |
| --- | --- | --- |
| Glucose | Venous fasting **70–99 mg/dL**; ordinary healthy CGM values vary with meals and have lag. | Fasting 100–125 impaired; ≥126 requires diagnostic confirmation. Low 54–<70 is ADA level 1; <54 level 2; severe assistance-requiring hypoglycemia is not defined by one number. Do not diagnose DKA/HHS from glucose alone. |
| Saliva cortisol | Named Mayo assay: waking **85–620 ng/dL (2.35–17.11 nmol/L)**; before bed **<127 ng/dL (<3.50 nmol/L)**. | Time/assay dependent; no universal critical value. Serum, saliva, sweat and ISF are not interchangeable. The PDF's ISF 15–30/>30 nM bands remain unvalidated for the chosen saliva channel. |
| hs-cTnI | UW Beckman assay example: women **0–15 ng/L**, men **0–20 ng/L**. | Above the assay-specific upper limit indicates injury; acute change/clinical evidence matter. PDF >0.04 ng/mL =40 ng/L is not a universal critical threshold. |
| Plasma lactate | Adult Mayo assay **0.5–2.0 mmol/L**. | >2 above interval; exercise can elevate it. >5 with pH<7.25 describes significant lactic acidosis in the cited lab interpretation. PDF resting >4 is a project escalation trigger, not a universal diagnosis. |
| Urinary NTx | UW assay: men **21–83**, premenopausal women **17–94**, postmenopausal women **26–124 nmol BCE/mmol creatinine**. | Compare like specimens and personal baseline. PDF >+25% is an unvalidated project trend flag, not a universally established emergency cutoff. |
| 25-OH vitamin D | NIH: <12 ng/mL deficiency risk, 12–<20 inadequate, ≥20 adequate for most; >50 potential adverse effects. NASA's preflight desired interval is **35–90 ng/mL** [N1]. | These serve different populations/purposes and conflict at the upper end. Preserve separate policy IDs. A **35–45 ng/mL** healthy demo target is our conservative assumption, not a new official range. No immediate critical alarm solely for exceeding 50. |
| IL-6 | [Mayo IL6DX serum assay][N15]: **<6.4 pg/mL**. | ≥6.4 above this interval, nonspecific. No transferable critical cutoff. Normal does not exclude inflammation. PDF >3 pg/mL and a fixed 2-hour postexercise exemption are not validated for this assay. |
| Sweat sodium concentration / flux | Sweat concentration and rate vary substantially; published exercise observations are not disease reference intervals. | No verified universal normal/critical flux. Derive local loss from local flow; extrapolation to whole-body loss requires calibration. Never substitute serum sodium ranges. |
| Viral shedding | Virus/specimen-specific PCR not detected for the simplest healthy fixture; assay limit must be declared. | Detection can occur without illness in astronauts. No common copies/mL critical threshold across EBV, VZV and CMV. |
| Heart rate | General adult resting **60–100 bpm**, with lower athletic baselines possible. | Context, rhythm, duration and symptoms determine urgency. NEWS2 bands apply to its acute-care setting, not healthy exercise classification. |
| HRV RMSSD | Personal baseline for a declared recording duration, beat quality, posture and method. | No universal normal/concerning/critical milliseconds. Do not transplant 10-second population distributions into 5-minute windows. |
| BP | AHA normal **SBP<120 AND DBP<80 mmHg**; elevated 120–129 AND<80; stage 1 130–139 OR80–89; stage 2 ≥140 OR≥90. | Use highest applicable class. >180 and/or >120 severe, with symptoms determining emergency context. A single reading does not establish chronic hypertension. Low BP requires perfusion/context rather than the inverse of the hypertension bands. |
| SpO2 | Common healthy reference **95–100%**, conditional on atmosphere/device. | PDF <94% warning/<90% critical can be a labelled project escalation policy. Clinical guidance differs: cited MedlinePlus advises assessment at ≤92 and immediate attention at ≤88. Never flag 99–100% as abnormal because the PDF nominal band ends at 98. |
| Temperature | General resting reference **36.5–37.3°C**, method dependent. | >38 or <36 in the PDF are inflammatory-screening criteria, not infection/sepsis diagnoses. ZHF estimates need method-specific interpretation; do not substitute skin temperature. NEWS2 bands are separately documented in ranges.md. |
| Respiratory rate | General resting **12–18/min**; NEWS2 zero-score band 12–20 has a different purpose. | NEWS2 ≤8 or ≥25 contributes 3 points, but a complete score needs other inputs. Exercise tachypnea is not automatically illness. |
| Body mass | Stable individual baseline with hydration/nutritional variation. | >2% acute water-related loss is a dehydration concern in exercise guidance. PDF >1% weekly loss is a project nutrition flag; neither is a universal critical mass. |
| Urine specific gravity | General **1.005–1.030**, assay dependent. | >1.020 may support concentrated urine but is still within the broad reference interval. No universal critical cutoff. |
| 24-hour urine volume | Intake/body-size dependent; adult stone prevention target **≥2.5 L/day**. | PDF <2 L/day is not kidney failure. KDIGO uses <0.5 mL/kg/h over ≥6 h and more severe timed criteria; a daily aggregate cannot establish all shorter windows. |
| Sweat rate | Rest can produce little measurable sweat; exercise/thermal load increase it. | No universal critical rate. Interpret losses against replacement, body mass and symptoms; absent fluid in a patch is not zero circulating sodium. |

Result evaluation, severity labels and clinical interpretation belong to a separate backend. The generator emits measurements only.

## 5. Environmental stream: cadence and ranges

Environment records identify a compartment and sensor, never a required astronaut. Personal occupancy/shielding history and personal career dose remain distinct. An ambient monitor's integrated reading is not automatically an astronaut's effective dose.

| Channel | NASA evidence / cadence | Proposed simulator timing and interpretation |
| --- | --- | --- |
| `ambient_ppco2` | E requires continuous monitoring. A NASA [SAM technology demonstration][N16] transmitted gas data every **2 s**, a device-specific reporting interval. | Every **2 s**, a demo choice. Nominal **1-hour mean ≤3 mmHg ≈400 Pa**, V2 6004 [N7]. An instantaneous exceedance and a completed 1-hour exceedance are different. No universal NASA emergency concentration is supplied by this requirement. |
| `ambient_light_lux` | Light exposure is documented in NASA [wearable research][N17]; no universal cabin photometer cadence verified. | Every **60 s**, independent compartment lighting schedule. No universal normal/critical photopic lux. Melanopic EDI targets in ranges.md require spectral/at-eye measurements; they must not classify ordinary lux. No sleep inference. |
| `ambient_dose_rate` | R documents 1-minute radiation reporting. | Every **60 s** for a declared modeled dose-equivalent rate, SI Sv/s. If mimicking an instrument reporting absorbed dose instead, use a separate Gy/s channel; no implicit conversion. PDF >50 µSv/h is a project alert, not a universal NASA medical limit. |
| `ambient_integrated_dose` | Time-resolved monitoring supports integration; personal effective-dose requirements are different. | Every **6 s (10/min)**, integrate the same latent rate over elapsed time, independently of the dose-rate publication interval. Never label this career effective dose. Initialize from run configuration and identify run resets. |
| `spe_flag` | NASA specifies protection for a design-reference SPE; no universal public Boolean polling rule verified. | Event-driven changes plus **60 s heartbeat**, false in healthy default. Optional 1 Hz PDF mode is explicitly a project schedule, not NASA practice. |

Radiation interpretation: [NASA V1 4030–4033][N18] distinguishes career effective dose **<600 mSv**, design-SPE protection **<250 mSv**, and long-duration GCR design limits **<1.3 mSv/day free space / <0.9 mSv/day planetary surface**. These are not interchangeable instantaneous illness alarms. A personal effective-dose channel can later be added with an explicit exposure model and prior-career baseline; it must not merely rename the ambient counter.

`ppCO2 = CO2_ppm × cabin_pressure / 1_000_000`. At 760 mmHg total pressure, 3 mmHg ≈3947 ppm; “4000 ppm” is not pressure-independent. Configure pressure explicitly. NASA also monitors ambient pressure, oxygen, humidity and temperature (E), but these are **optional scope extensions**, not silently added mandatory biomarkers. Any future extension needs its own ranges, units and cadence policy.

The backend computes exposure windows and stores environment history. The generator may retain bounded rolling state to evaluate a local window, but cannot present a partially filled first-hour window as a completed 1-hour average. Shared environmental exposure may influence a future physiological scenario without coupling the environment scheduler to any astronaut's sampling.

## 6. Differences from the updated PDF that implementation must preserve

| PDF statement | Research-informed decision |
| --- | --- |
| Page 6: biochemistry every 5/30/60 min | This is the project's hypothetical sensor schedule. Apply frequent acquisition only to a declared sensor such as synthetic CGM; use specimen sessions for lab-only channels. Do not represent NTx, vitamin D, IL-6 or PCR as established continuous NASA telemetry. |
| Pages 1/6: radiation 1 Hz, vital cadence tied to sleep | Keep 1 Hz as an optional demo setting. Default follows the documented radiation example; no sleep-tracking dependency. HRV needs a window, BP a declared device/session. |
| Page 3: IL-6 >3, ISF cortisol 15–30/>30, NTx +25% | Preserve as unvalidated PDF policies only; use the declared specimen/assay evidence for active channels. Do not borrow saliva cortisol or serum IL-6 limits for ISF. |
| Pages 2–3: troponin >0.04 ng/mL, SpO2 94–98%, urine <2 L/day | Use assay-specific troponin limits, allow healthy SpO2 up to 100, distinguish stone prevention from acute urine-output criteria. |
| Page 3: ppCO2 >3 mmHg / ~4000 ppm | Use the NASA 1-hour averaging period and actual total pressure. Keep this in the environment domain. |
| Pages 4–5: jugular/ICP and revised hydrogel formulas | Excluded from this implementation; their existence does not validate a diagnostic measurement. Old six-page-PDF constants in historical documents are not current requirements. |

## 7. Python implementation sequence

1. **Create the typed registry and coverage manifest.** Every channel above gets a stable ID, crew/environment scope, specimen, assay/device, source unit, wire unit, collection schedule, averaging window, availability delay, baseline policy and citations. Record exclusions explicitly. Use `Enum`, dataclasses/Pydantic models and typed protocols; no ambiguous reuse of `cortisol` across specimens or `radiation_dose` across dose quantities.
2. **Freeze the outbound contract.** Emit only `channel`, `value`, `unit`, `measured_at` as specified in docs/backend_contract.md and valid JSON syntax. Correct the note's apparent mmHg/SI mismatch at conversion: 118 mmHg ≈15732 Pa. Dictionary metadata retains `environment.id`, `gravity_g`, `comm_delay_s`, and channel `name`, `domain`, `body_regions`, `explanation`; add unit, specimen, method, source and window definitions. Environment channels use empty body regions.
3. **Use one data route without implementing a server.** All crew and environment readings POST to the configured `data_route` (default `/data`) under `base_url`. Scope and owner are carried in headers; `channel` identifies the biomarker. Identify sensor/run and deduplication key in agreed headers. Dynamic sample/window/quality context can travel in agreed metadata headers while keeping the four-field body. Contract changes require receiver compatibility before code integration, not another local API.
4. **Build elapsed-time physiological models.** Shared activity, meals, circadian phase and hydration produce correlated responses with separate time constants; use seeded, per-channel random streams and modest correlated sensor noise. Generate latent continuous physiology independently of when it is observed. Slow NTx/vitamin D changes must not jump at sample ticks. Use baseline fixtures for assays without a continuous model. Serum IL-6, sweat concentration and cortisol remain different specimen models.
5. **Build independent environment models.** Compartment CO2/lighting/radiation have their own clocks and RNG streams. Integrate nonnegative latent radiation rate; noisy measurements do not make accumulated dose decrease. Publish each environment acquisition once even with multiple astronauts. Keep environmental state alive when a crew sensor pauses.
6. **Implement acquisition and result availability.** Use `asyncio` with monotonic scheduling; UTC for measurement timestamps. Support periodic sensors, event sampling, multi-time-point sessions and window aggregates. The same physical acquisition may have multiple paired results. `measured_at` is point collection time or window end with a defined window, not HTTP send time. Lab samples become sendable only after configured processing delay. Accelerated simulation declares its clock mapping/run identity to the backend.
7. **Add bounded delivery.** Validate, convert, then POST new readings with `httpx`. Bounded RAM queue, finite retries/backoff for transient errors, idempotency keys, explicit overflow/drop metrics and clean cancellation. Do not re-stamp retries. Configuration and code may be files; generated telemetry is never persisted. Restart begins a new run with configured initial state, not fabricated continuity.
8. **Validate before integration.** Test different clocks, paired BP, 5-minute HRV windows, laboratory availability, completed urine windows, dry sweat, SI conversions, assay boundaries, unfilled CO2 windows, dose integration, independent environment ownership, bounded retry behavior and restart semantics. Use deterministic accelerated runs covering meals/exercise and sparse laboratory sessions. Confirm that excluded channels and inferred medical advice are never emitted.

Use full type hints on public functions and model fields. Docstrings/comments should explain why schedules differ, how source units convert, why specimen-specific thresholds cannot be shared, how observation time differs from delivery time, and which choices are simulation assumptions. Comments should explain the model's limits as well as its calculations.

## 8. Acceptance criteria and future scenarios

- Every included measurement has a source, specimen/device, unit, schedule; unknown NASA cadence is labelled unknown rather than filled with the PDF's numbers.
- Healthy traces are physiologically coherent, including ordinary exercise effects; they are not independent uniform random numbers constrained to resting reference bands.
- The receiver sees newly acquired readings at independent times and sparse lab results with correct windows and collection timestamps.
- Environmental telemetry has independent ownership and cadence; no astronaut identifier is required for a cabin sensor record.
- No generated measurement survives process exit in local storage. Backend analysis/history remain backend concerns.
- Disease scenarios are not implemented now. Future condition-specific trajectories must preserve assay, timing and clinical prerequisites. Current channels cannot alone establish sepsis, myocardial infarction, DKA, SANS or radiation sickness.

## 9. Source ledger and confidence

NASA standards support requirements and example operational schedules; they are not proof of a particular flight device. Primary studies support the exact study protocol and cohort, not all missions. Performing-laboratory catalogs support only the named assay interval. NASA project pages establish development or a specific reported activity, not deployment across the fleet. Public absence of a cadence is a research limitation, not proof that NASA never collects the measurement.

N1/N3/N6/N8 are NASA-hosted documents; N2 is a program-authored review of its measurements; N4/N5/N9 are primary study reports; N7 is NASA's current standard text, cross-checked against the [Rev. F listing][N19]. N15 is the performing laboratory's current catalog. The clinical guideline/laboratory provenance and cross-checks for the other ranges are listed in ranges.md. No exact threshold has been accepted solely because the project PDF calls itself “verified.”

[N1]: https://www.nasa.gov/wp-content/uploads/2024/09/ochmo-std-100-1a-rev-a-signed.pdf "NASA OCHMO-STD-100.1A Revision A, 2024"
[N2]: https://pmc.ncbi.nlm.nih.gov/articles/PMC12612093/ "Spaceflight Standard Measures program report"
[N3]: https://ntrs.nasa.gov/api/citations/20090014816/downloads/20090014816.pdf "NASA Nutritional Status Assessment protocol"
[N4]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4324706/ "Norsk et al., ambulatory blood pressure during long-duration spaceflight"
[N5]: https://www.nature.com/articles/s41526-017-0015-y "Mehta et al., latent virus reactivation on the ISS, 2017"
[N6]: https://ntrs.nasa.gov/api/citations/20130014603/downloads/20130014603.pdf "Crucian et al., plasma cytokines during long-duration spaceflight"
[N7]: https://www.nasa.gov/reference/6-0-natural-and-induced-environments-vol-2/ "NASA-STD-3001 Volume 2, natural and induced environments"
[N8]: https://ntrs.nasa.gov/api/citations/20240011436/downloads/BEAM-Report-NASA-TP-new.pdf "NASA BEAM radiation environment report"
[N9]: https://www.jacc.org/doi/10.1016/j.jacc.2023.05.058 "Cardiac Effects of Long-Duration Spaceflight, 2023"
[N10]: https://www.nasa.gov/blogs/stationreport/2024/02/22/iss-daily-summary-report-2-22-2024/ "NASA ISS report: Vascular Aging glucose tolerance test"
[N11]: https://www.niddk.nih.gov/health-information/diabetes/overview/managing-diabetes/continuous-glucose-monitoring "NIDDK: continuous glucose monitoring"
[N12]: https://pubmed.ncbi.nlm.nih.gov/9293350/ "Primary spaceflight exercise-capacity investigation"
[N13]: https://www.nasa.gov/wp-content/uploads/2023/03/human-adaptation-2020-final.pdf "NASA Human Adaptation to Spaceflight, nutrition/bone markers"
[N14]: https://techport.nasa.gov/projects/97106 "NASA TechPort: developmental multimodal sweat sensing"
[N15]: https://www.mayocliniclabs.com/test-catalog/overview/618776 "Mayo IL6DX, Interleukin-6, Serum"
[N16]: https://www.nasa.gov/blogs/stationreport/2020/08/25/iss-daily-summary-report-8-25-2020/ "NASA ISS report: SAM gas data reporting every two seconds"
[N17]: https://www.nasa.gov/humans-in-space/wearable-tech-for-space-station-research/ "NASA wearable research including light exposure"
[N18]: https://www.nasa.gov/reference/4-0-human-performance/ "NASA Volume 1 radiation protection requirements"
[N19]: https://standards.nasa.gov/node/237 "NASA-STD-3001 Volume 2 Revision F, 2026-07-14"


## Implemented dehydration review and cadence override

The PDF page 2 “Dehydration & Electrolyte Loss” row specifies acute body-mass loss >2%, urine specific gravity >1.020, and baseline-relative local sweat rate / sodium flux. The researcher dashboard groups these inputs together, with sodium concentration and timed urine volume as supporting measurements. Body mass and local sweat channels expose comparisons against configured synthetic reference values. Activity affects sweat flow, and monthly mass / session-based urine observations cannot establish an acute event by themselves. No standalone water-retention or total-body-water sensor is specified by that row; mass gain must not be labelled fluid retention without additional evidence.

The user's current override fixes heart rate, respiratory rate and integrated monitor dose at one acquisition every six simulation seconds. Respiration retains a 30-second estimation window and first-result warm-up. Integrated monitor dose now has an independent acquisition group; dose rate retains its separately configured publication interval. These are project requirements, not newly asserted NASA practices.
