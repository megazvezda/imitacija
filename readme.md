# Imitacija

Generate synthetic sensor telemetry and send it to a separate backend for analysis.

**Current plan:** [NASA monitoring, acquisition schedules and implementation](NASA_MONITORING_PLAN.md). Current scope is biochemical biomarkers (including newly specified IL-6), vital signs and objective hydration/nutrition measurements, plus an independent environmental stream. Sleep, mood, cognitive/visual assessments and sensor-physics/digital-twin outputs are excluded. The worker POSTs readings and does not persist telemetry. See [ranges.md](ranges.md) for cited, context-specific ranges and [nigelNote.md](nigelNote.md) for the reading contract.

The source is now the [updated 10-page specification](Tiered%20Master%20System%20Specification%20%26%20Implementation%20Plan%20%281%29-1.pdf). The tables below are a **historical extraction of the previous six-page edition**; their page numbers, thresholds, formulas and broad scope are not current implementation requirements. Retained for traceability only. Values labelled **example** are sample payload values, not normal ranges. **Unspecified** means the previous PDF did not supply that detail.

## Biochemical biomarkers to simulate

| Biomarker | Measurement / unit in PDF | Values or behavior specified in PDF | Pages |
| --- | --- | --- | --- |
| Blood glucose | mg/dL in health findings; `blood_sugar_mM` in payload | Hypoglycemia: <70 mg/dL. Example: 5.2 mM. | 1, 2, 5, 6 |
| Cortisol | nM; diurnal slope | Nominal: 10.0 nM; warning threshold: 22.4 nM; critical: >30.0 nM. Diurnal slope flattening is a behavioral-health indicator. Example: 18.2 nM. | 1–3, 5, 6 |
| Cardiac troponin I (hs-cTnI) | ng/mL | Warning: 0.01–0.04 ng/mL; critical: >0.04 ng/mL. Example: 0.005 ng/mL. | 4, 6 |
| Lactate | Unit unspecified | Listed as a metabolic/GFET channel; no range, threshold, or sample value supplied. | 5 |
| Urinary NTx (bone resorption marker) | % change from baseline; resorption slope | Track baseline-relative change and kinetics; no numerical alarm threshold supplied. Channel: `bone_ntx_pct_baseline`. | 1, 2, 5 |
| 25-OH vitamin D | Unit unspecified; trend | Track nutritional trend; no concentration range or threshold supplied. | 2 |
| Sweat sodium (Na+) flux | Unit unspecified; baseline-relative flux | Used with sweat rate to detect dehydration/electrolyte loss. | 2 |
| Latent viral shedding status | Status; encoding unspecified | Input to infection/immune-dysregulation assessment. No virus, assay, or numerical range specified. | 2 |

## Physiological and behavioral inputs to simulate

These include vital signs and sensor or assessment inputs, which are broader than biochemical biomarkers. Assessment results can be synthetic fixtures; the PDF does not establish that they come from physical sensors.

| Input | Measurement / unit in PDF | Values or behavior specified in PDF | Pages |
| --- | --- | --- | --- |
| Heart rate | bpm | Postural rise ≥30 bpm is a detection criterion. Example: 74 bpm. | 1, 2, 4, 6 |
| Heart-rate variability | RMSSD; unit unspecified | Channel: `hrv_rmssd`; no range or threshold supplied. | 4 |
| Systolic and diastolic blood pressure | mmHg | Postural systolic drop ≥20 mmHg is a detection criterion. Examples: 118/78 mmHg. | 1, 2, 4, 6 |
| Oxygen saturation (SpO2) | % | Warning: <94%. | 1, 2 |
| Core/body temperature | °C in payload | Example: 36.8 °C; no temperature thresholds supplied. | 1, 6 |
| Respiratory rate | Unit unspecified | Elevated rate contributes to hypoxia/CO2 detection; no numerical threshold supplied. | 2 |
| Body mass | Absolute unit unspecified; relative loss in % | Loss >2% supports dehydration detection; weekly mass slope supports nutrition assessment. | 2 |
| Urine specific gravity | Specific-gravity value | Dehydration criterion: >1.020. | 2 |
| Urine volume over 24 hours | L/day | Renal-stone-risk criterion: <2.0 L/day. | 2 |
| Sweat rate | Unit unspecified; relative to baseline | Dehydration input; no absolute range supplied. | 2, 4 |
| Segmental bioimpedance / cephalic fluid shift | Fluid-shift index; unit and mapping unspecified | Channel: `cephalic_fluid_index`; used to trigger SANS eye self-tests. | 2, 4 |
| Prefrontal EEG | Spectral power density S(f), μV²/Hz; band power, μV² | Theta band: 4–8 Hz; alpha band: 8–13 Hz. Used to derive the fatigue ratio. | 1, 4, 5 |
| Actigraphy / sleep observations | Sleep duration, efficiency, and stages; units/encoding unspecified | Continuous actigraphy during sleep; used for sleep deficiency and circadian assessment. | 2, 5 |
| Psychomotor vigilance test (PVT) reaction time | ms | Daily 5-minute test in health findings; lapses are responses >500 ms. | 1, 2, 5 |
| PHQ-9 and GAD-7 check-ins | Questionnaire scores; ranges unspecified | Daily behavioral-health check-ins. | 2 |
| Headache flag | Flag; encoding unspecified | Used with ambient CO2 and respiratory observations. | 2 |
| Visual acuity / Amsler grid result | LogMAR acuity; Amsler result encoding unspecified | Software self-tests triggered by fluid-shift findings. | 2 |
| Exercise compliance | Unit/encoding unspecified | Input to bone-health assessment. | 2 |
| Joint movement / kinematics | Joint angles; degrees in payload, radians in strain formula | Examples: left knee flexion 112.4°, right shoulder abduction 90.0°. Elbow, wrist, and knee flexion also described. | 1–3, 4, 6 |

## Environmental and sensor-physics telemetry to simulate

These are required supporting channels in the PDF, rather than biological markers. Sensor outputs should be consistent with the simulated underlying concentration or motion.

| Channel | Measurement / unit in PDF | Values or behavior specified in PDF | Pages |
| --- | --- | --- | --- |
| Ambient CO2 | Partial pressure (`ppCO2`); unit unspecified | Elevated exposure is a hazard input; no numerical threshold supplied. | 2 |
| Ambient light exposure | lux | Used for sleep/circadian assessment; no exposure threshold supplied. | 2 |
| Cumulative effective radiation dose | mSv | PDF cites a 600 mSv limit. Channel: `radiation_dose`. | 2, 4 |
| Live radiation dose rate | μSv/h | Channel: `dose_rate`; no numerical threshold supplied. | 2, 4 |
| Solar particle event | `spe_flag`; flag encoding unspecified | Safety override input. | 2, 4 |
| Hydrogel displacement and strain | ΔL in mm; ε = ΔL/L0; percentage in payload | ΔL: 0–9.99 mm; L0 ≈50 mm; film thickness 1.2 mm. Also ε = (tfilm × θ)/(2 × L0), with θ in radians. | 3, 6 |
| Hydrogel resistance response | R and R0 in Ω; ΔR/R0 unitless | R0 = 0.45089 Ω at t=0; ΔR/R0 = GF(ε) × ε. | 1, 3, 6 |
| Dynamic gauge factor (GF) | Unitless | Strain 0–5%: 1180.75; 5–15%: 233.48–389.58; 15–30%: 74.34–114.86. | 3 |
| GFET normalized current shift | ΔIds/I0, unitless | Cortisol binding model: ΔIds/I0 = 0.65 × [Target]/(14.8 + [Target]), concentration in nM. | 1, 3, 6 |
| GFET threshold voltage shift | ΔVt in mV | Troponin-related Debye-screening formula supplied; no concentration-to-bound-density mapping supplied. | 4 |

## Derived quantities for the analysis backend

Prefer deriving these from related synthetic inputs where a formula is supplied. If the receiving backend requires these as input fields, simulate them consistently; the PDF does not fully specify every calculation.

| Derived quantity | Basis / specification | Pages |
| --- | --- | --- |
| Postural BP drop and HR rise | Compare measurements across posture changes; thresholds ≥20 mmHg systolic drop and ≥30 bpm HR rise. | 2 |
| Shock index | HR / systolic BP; detection threshold >0.9. | 2 |
| NEWS2 and qSOFA | NEWS2 ≥5: review; ≥7: urgent. qSOFA ≥2. Component definitions and complete scoring rules are not supplied. | 2 |
| Sleep debt and mood score | Dashboard outputs; calculation and scale unspecified. | 1, 2 |
| Body-mass, NTx, and cortisol trends | Weekly mass slope, baseline-relative NTx/resorption slope, and diurnal cortisol flattening. Computation windows are only partly specified. | 1, 2 |
| Cognitive fatigue estimate (CFE) | Theta power / alpha power. Nominal <0.70; warning 0.70–1.20; critical >1.20. Example: 0.65. | 4, 6 |
| PVT lapse count | Count reaction times >500 ms; no abnormal count threshold supplied. | 2 |
| Estimated intracranial pressure | `estimated_icp_mmHg`; example: 14.8 mmHg. Estimation formula unspecified. | 6 |
| Lumbar asymmetry and exercise form status | Example ratio: 1.28; example `form_status`: `WARNING`. Calculation and thresholds unspecified. | 6 |
| Overall status, primary hazard, recommended actions | Decision-engine outputs in the example payload; generate in the analysis backend rather than treating them as measured biomarkers. | 6 |

## Sampling and transmission requirements

The PDF distinguishes adaptive sensor polling from a **1000 ms payload broadcast**. Implementation interpretation: transmit the latest available readings each second, preserving each reading's acquisition timestamp so retained values are not mistaken for fresh samples.

| Domain / explicit channels | Active | Resting | Sleeping | Pages |
| --- | --- | --- | --- | --- |
| Radiation dose, dose rate, SPE flag | 1 Hz | 1 Hz | 1 Hz | 4 |
| HR, HRV RMSSD, systolic/diastolic BP | Every 15–30 sec | Every 5 min | Every 15 min | 4 |
| Cephalic fluid index, sweat rate, joint kinematics | Every 1 min | Every 15 min | Table says suspended/paused, but accompanying text retains passive SANS tracking | 4 |
| Glucose, lactate, cortisol, NTx | Every 5 min | Every 30 min | Every 60 min | 5 |
| EEG theta/alpha ratio, PVT | Every 15 min | Every 60 min | Continuous actigraphy / hourly EEG; sleeping PVT behavior unspecified | 5 |

Include `timestamp` and `user_state` as payload metadata. The state machine describes active, resting, and sleeping states; the sample JSON uses `ACTIVE`. Polling frequencies for other listed inputs are unspecified.

## Specification gaps to resolve before implementation

- The page 6 JSON is only a partial example: it omits many channels listed elsewhere, including SpO2, lactate, NTx, and radiation. Use the full tables above as the inventory.
- Glucose uses mg/dL in the findings and mM in the payload. Choose a canonical unit and convert thresholds explicitly.
- The hydrogel example is inconsistent with the formulas: 1.42% strain falls in the GF=1180.75 segment, whereas the JSON uses GF=312.4 and ΔR/R0=0.145. Even using GF=312.4, multiplying by fractional strain 0.0142 gives 4.43608, not 0.145. Generate the response from the chosen model instead of copying those sample values.
- The stated 9.99 mm maximum displacement at L0≈50 mm reaches approximately 20% strain, while the GF table extends to 30%. Segment-boundary handling and selection within GF ranges are unspecified.
- The cortisol example also differs from its model: 18.2 nM gives ΔIds/I0≈0.3585, while the JSON uses 0.312.
- Page 1 describes EEG “Alpha/Theta” ratios, but the explicit CFE formula and channel name on pages 4–6 use **theta/alpha**. Use theta/alpha for that channel.
- Sleep polling conflicts with the text retaining passive SANS tracking. PVT is described both as a daily test and as an adaptively polled channel; distinguish test sessions from reporting stored results.
- The troponin formula specifies a fixed bound density but does not connect concentration to that density. It cannot yet define a concentration-dependent voltage simulation without an additional model.
- Many inputs lack units, baseline ranges, noise models, or conversion/scoring rules. These need explicit simulation assumptions; they should not be presented as values extracted from the PDF.
- Serotonin and dopamine appear only in a reference title on page 6, not as requested measurement channels, so they are excluded from the simulation inventory.
