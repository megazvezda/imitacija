# Evidence and ranges for synthetic astronaut telemetry

Research checked: **2026-11-14**, including the updated 10-page PDF. **Current scope and acquisition plan: [NASA_MONITORING_PLAN.md](NASA_MONITORING_PLAN.md).** Implement biochemical markers (including IL-6), vital signs and objective hydration/nutrition measurements; environmental channels have separate ownership and schedules. The simulator generates readings and POSTs them without persistent telemetry storage.

This file also retains historical research for the broader original README inventory. Sections 3 and 5, movement/fluid-index rows in Section 2, and associated derived outputs are **outside the current implementation scope**. Their old PDF examples and sensor calibration audit are archival, not requirements for the updated PDF. The current plan takes precedence for included channels, identifiers, cadence and PDF discrepancies. A simulated daily routine is model input; sleep and mood are not tracked outputs.

## How the next agent must use this document

This is a **context-qualified evidence reference**, not a universal diagnostic lookup table. A reference interval, a disease diagnostic criterion, an emergency trigger, and a spacecraft engineering limit are different things. A healthy astronaut can have values outside terrestrial resting intervals during exercise, sleep, or adaptation to microgravity.

For each scenario, specify age, sex where the assay requires it, baseline, activity, posture/gravity, sleep phase, specimen, assay/device, and observation window. Preserve independently acquired timestamps. Do not diagnose an episode by combining arbitrarily stale readings.

Evidence labels used below:

| Label | Meaning | Permitted use |
| --- | --- | --- |
| **Clinical** | Guideline or clinical score from its issuing organization | Apply only to its stated setting/population and prerequisites. |
| **Lab** | Reference interval from the laboratory performing a named assay | Use only with the same declared specimen and assay assumptions. |
| **Research** | Primary study or expert consensus; limited external validity | Support relationships and distributions, not an invented universal emergency cutoff. |
| **Operational** | NASA/occupational exposure requirement | Model compliance and exposure duration; do not equate it with current illness. |
| **Unvalidated** | Project-defined quantity or calibration without verified thresholds | Explicit simulator assumption only; no claim of clinical validation. |

**“No established cutoff” below means no transferable cutoff was verified in the sources reviewed, not proof that none could ever exist.** Do not replace this with arbitrary medical limits. Some channels require a categorical or baseline-relative interpretation rather than three numerical ranges.

For `nigelNote.md`'s `evaluation`, `normal` can represent an applicable reference interval; `unusual` can represent a documented abnormality. Reserve `critical` for a specified urgent condition in context. Do not automatically map “severe questionnaire score,” “above laboratory reference,” or “exceeds career exposure limit” to an immediate physiological emergency. `optimal` has no universal definition. Where no clinical policy exists, the dictionary must say `evaluation_basis: synthetic_policy`; missing information must not silently count as normal.

## 1. Biochemical biomarkers

**NASA-specific vitamin D qualification:** NASA OCHMO-STD-100.1A Rev. A §6.7.1 gives a preflight desired 25-OH D interval of **35–90 ng/mL**, with testing at crew-surgeon discretion. This differs from the NIH population interpretation below, particularly above 50 ng/mL. Keep both policies explicitly scoped; do not merge them into a universal normal band. The current plan proposes **35–45 ng/mL** only as a healthy simulation target. Daily/weekly supplementation in NASA's table is not daily/weekly blood collection. [NASA medical standard][S61]

| Channel / specimen | Reference or expected condition | Abnormal / concerning | Severe / urgent interpretation | Evidence and simulation constraints |
| --- | --- | --- | --- | --- |
| **IL-6 / `il6_serum`** — serum, pg/mL | Mayo IL6DX reference: **<6.4 pg/mL**. | **≥6.4** is above this assay's interval; increased IL-6 is nonspecific. A normal result does not exclude inflammation. | **No universal critical value** or autonomous infection/sepsis diagnosis. | **Lab:** [Mayo IL6DX][S60]. The updated PDF's >3 pg/mL warning and fixed 2-hour exercise exemption are not validated for this assay. NASA cytokine studies used plasma and session-based sampling; their assay cannot inherit a serum interval automatically. See the current plan for that distinction. |
| **Glucose** — fasting venous plasma, mg/dL | Fasting <100; combine with the hypoglycemia boundary to use **70–99** as a conventional fasting simulation band. | **100–125**: prediabetes criterion; **≥126**: diabetes criterion, ordinarily requiring confirmation. These are fasting criteria, not post-meal alarm bands. | See separate low-glucose and crisis rules below. | **Clinical:** [NIDDK diagnostic criteria][S01], independently consistent with [CDC testing guidance][S02]. Declare fasting duration; capillary/CGM interstitial readings are not identical to venous diagnostic tests. |
| **Glucose, low** — mg/dL | **≥70** avoids the ADA low-glucose threshold; this alone does not define a healthy upper limit. | Level 1: **54 ≤ glucose <70**. | Level 2: **<54**. Level 3: altered functioning requiring another person's help, **regardless of the measured concentration**. | **Clinical:** [ADA 2025 patient classification][S03], cross-checked against [ADA 2026 classification][S04]. Do not invent a numerical “level 3” boundary. |
| **Glucose, high / crisis** — plasma | Fasting limits above; standardized 2-hour OGTT: <140 mg/dL, 140–199 impaired tolerance, ≥200 diabetes criterion. | A random glucose ≥200 mg/dL has diagnostic significance with classic symptoms. It is not by itself a crisis definition. | HHS includes **glucose ≥600 mg/dL**, but also hyperosmolality and other criteria. DKA requires diabetes/hyperglycemia plus ketosis and acidosis; it can occur without extreme glucose. | **Clinical:** [NIDDK][S01], [2024 multi-society crisis consensus][S05]. A future DKA/HHS scenario needs ketones, pH/bicarbonate, osmolality and clinical context beyond the current channel set. |
| **Cortisol — saliva, LC-MS/MS**, ng/dL or nmol/L | Mayo SALCC: immediately after waking **85–620 ng/dL ≈2.35–17.11 nmol/L**; immediately before bed **<127 ng/dL ≈3.50 nmol/L**. | Outside the time-specific interval merits context-specific assessment; persistent elevation at bedtime differs from a normal waking rise. | **No universal salivary “critical cortisol” value.** Adrenal crisis cannot be assigned from this channel alone. | **Lab:** [current Mayo SALCC assay][S06]. Use time relative to sleep, not an arbitrary UTC hour. Not transferable to sweat, total serum cortisol, or an uncalibrated GFET. |
| **Cortisol — total serum**, µg/dL or nmol/L; alternative specimen, not a second independent signal | Mayo CORT: morning **7–25 µg/dL ≈193–690 nmol/L**; afternoon **2–14 µg/dL ≈55–386 nmol/L**. | Interpret with collection time, medications, binding proteins, illness, and assay. | No universal random serum concentration separates stable from critically ill. | **Lab:** [Mayo CORT][S07]. A different Mayo LC-MS/MS total/free assay has a different morning total interval (5–25): [CORTO][S08]. This cross-check demonstrates why selecting the assay is mandatory. The updated PDF's ISF 15–30/>30 nM warning/critical bands are not generic serum thresholds. |
| **hs-cTnI / `troponin_i`** — serum/plasma, ng/L | Example declared assay: UW Beckman hs-cTnI **0–15 ng/L for women; 0–20 ng/L for men**. These are laboratory reporting intervals tied to 99th-percentile limits. | Above the assay's upper reference limit indicates myocardial injury; serial rise/fall and clinical context distinguish acute processes. | No assay-independent “critical” number or myocardial infarction diagnosis. Symptoms/ECG and serial measurements matter. | **Lab/Clinical:** [UW Beckman guide, effective 2026-04-01][S09]. **1 ng/mL = 1000 ng/L**. The PDF's >0.04 ng/mL (=40 ng/L) is not a universal hs-cTnI rule. |
| **Lactate** — adult plasma, mmol/L | Mayo LACS1: **0.5–2.0**. | **>2.0** is above this assay's adult interval; resting illness and exercise must be distinguished. | Mayo describes **>5 with pH <7.25** as significant lactic acidosis, not lactate alone. Septic shock requires infection/sepsis, vasopressors to maintain MAP ≥65 mmHg, and lactate >2 despite adequate fluids. | **Lab/Clinical:** [Mayo lactate][S10], [Sepsis-3][S11]. Do not transfer blood thresholds to sweat lactate or declare healthy exercise septic shock. |
| **Urinary NTx** — creatinine-normalized, nmol bone-collagen equivalents/mmol creatinine | UW assay: adult men **21–83**; premenopausal women **17–94**; postmenopausal women **26–124**. | Above the relevant assay interval or a reproducible rise from a matched baseline suggests increased turnover. | No verified universal “critical” NTx concentration or percent rise. It is not a direct fracture or renal-stone diagnosis. | **Lab:** [UW NTx assay][S12]. Compare collections at the same time of day. `bone_ntx_pct_baseline = 100 × (current/baseline − 1)`; unchanged = 0%. Absolute reference intervals cannot be reinterpreted as percentages. |
| **25-OH vitamin D** — serum, ng/mL; nmol/L | NIH/NASEM: **≥20 ng/mL (≥50 nmol/L)** generally adequate; avoid interpreting this as “the higher the better.” | **<12 (<30)** deficiency risk; **12 to <20 (30 to <50)** generally inadequate; **>50 (>125)** associated with potential adverse effects. | Toxicity commonly involves **>150 ng/mL (>375 nmol/L)** together with hypercalcemia; this is not a standalone emergency definition. | **Clinical:** [NIH ODS, assessment and excess sections][S13]. Values change over days/weeks, not random minute-to-minute swings. Consensus on a universal optimum is lacking. |
| **Sweat sodium flux** — mmol/h or mol/s; local versus whole-body must be declared | Flux = sweat sodium concentration × matching sweat flow. It has no universal healthy interval. | Large sustained loss relative to replacement can support a dehydration/electrolyte-loss scenario. | No independent critical sweat-sodium flux threshold; it does not measure serum sodium. | **Research:** [Baker et al. primary exercise dataset][S14] reports estimated whole-body concentrations spanning **17–106 mmol/L**. These are observed study values, not disease bands. Local patches require a validated site conversion; see [regional-to-whole-body validation][S15]. |
| **Latent viral shedding** — virus-specific PCR/status | `not_detected` is a reasonable healthy fixture, but asymptomatic `detected` can also occur in astronauts. | Persistent/increased shedding is a monitoring finding, depending on virus, specimen, assay and symptoms. | No universal binary or copies/mL threshold for critical illness. | **Research:** [NASA original investigation report][S16] and [spaceflight HSV clinical study][S17]. Define the virus and assay limit of detection. Do not equate “positive” with acute symptomatic infection. |

## 2. Vital signs, hydration, and movement

| Channel | Expected / reference | Concerning or escalation interpretation | Critical limitations and evidence |
| --- | --- | --- | --- |
| **Heart rate**, beats/min | Resting adults commonly **60–100**; trained people can be around **40** without illness. | Resting >100 or <60 requires context; use the NEWS2 bands below when modeling acute deterioration. | **Clinical:** [AHA heart rate][S18]. Exercise/sleep and personal baseline are essential. A low athletic pulse is not automatically a critical event. |
| **HRV RMSSD**, ms | No universal normal range. Match recording length, age, posture, respiration, rhythm and processing to a reference cohort. | Sustained fall from the individual's comparable baseline can be a useful synthetic feature; it is not disease-specific. | **Research:** [Lifelines reference study][S19], [MESA study][S20]. MESA's selected ≥45-year-old group had median **22.0 ms**, IQR **15.0–34.0**, from short ECG recordings; this is not a universal cutoff or a 5-minute astronaut reference interval. No verified emergency threshold. |
| **Systolic/diastolic BP**, mmHg, seated/resting | AHA normal: **SBP <120 AND DBP <80**; this upper-bound category does not make very low BP safe. | Elevated: **120–129 AND <80**. Stage 1: **130–139 OR 80–89**. Stage 2: **≥140 OR ≥90**, taking the higher category. | **Clinical:** [AHA BP categories][S21]. **>180 systolic and/or >120 diastolic** is severe; with acute concerning symptoms it is an emergency. Repeated resting measurements matter. Acute low SBP is handled in NEWS2, not the chronic-hypertension categories. |
| **SpO2**, % | Common healthy range **95–100** at ordinary terrestrial conditions. | MedlinePlus advises assessment at **≤92**; NEWS2 starts scoring at 95 (different purpose). | **Clinical:** **≤88** is an immediate-attention threshold in [MedlinePlus oximetry guidance][S22]. Measurement error, perfusion, pigmentation, inspired oxygen and cabin pressure matter. Do not treat these as universal EVA/altitude limits. |
| **Body/core temperature**, °C | General resting body-temperature reference **36.5–37.3**; site/device and circadian phase matter. | See NEWS2 temperature bands below for acute-illness scoring. | **Clinical:** [MedlinePlus vital signs][S23]. Skin, oral and core temperatures are not interchangeable. A high value needs symptoms, activity and heat exposure to distinguish fever from hyperthermia; no single generic “critical fever” rule is imposed here. |
| **Respiratory rate**, breaths/min | General resting adult reference **12–18**; NEWS2's zero-score interval is broader. | Persistent deviation at rest is concerning; qSOFA uses ≥22 with suspected infection. | **Clinical:** [MedlinePlus vital signs][S23], [Sepsis-3][S11]. Exercise can raise RR without disease; severe low/high acute bands appear below. |
| **Body mass**, kg; short-term percentage change | Individual baseline with realistic intake/output variation; no universal healthy astronaut mass. | During exercise, **>2% loss attributable to water deficit** is excessive dehydration in ACSM guidance. | **Clinical:** [ACSM position stand][S24]. Percentage loss alone does not establish shock or critical dehydration. In microgravity measure mass with an appropriate device; a normal Earth weighing scale does not provide it. |
| **Urine specific gravity**, unitless | General laboratory interval **1.005–1.030**. | Concentrated urine may support low fluid intake, but the PDF's >1.020 is inside the general reference interval. | **Lab:** [MedlinePlus USG][S25]. No universal critical USG. Solutes, renal concentrating ability and assay matter; use hydration context, not a standalone diagnosis. |
| **Urine volume, 24 h**, L/day | Depends on intake, losses and body size. For adult calcium-stone prevention, AUA recommends output **≥2.5 L/day**. | Falling below that prevention target is not equivalent to acute kidney failure. | **Clinical:** [AUA 2026 guideline][S26], corroborated by [earlier AUA guideline][S27]. For acute disease, use weight-normalized output over timed windows below. |
| **Sweat rate**, whole-body L/h or local flow/area | Highly activity-, heat- and person-dependent; low flow at rest is expected. | Increased losses without replacement can contribute to dehydration; high exercise flow alone is not pathology. | **Research:** the [primary exercise dataset][S14] observed whole-body rates **0.19–5.64 L/h** (mean 1.09). This is an exercise sample, not a normal range for resting astronauts. No universal critical flow. |
| **Segmental bioimpedance / cephalic fluid index**, Ω / defined index | Establish a frequency-, electrode-, region-, posture- and mission-specific baseline. The PDF does not define its index. | A reproducible change can represent fluid redistribution in a simulation. | **Unvalidated:** no verified numerical SANS cutoff for this project index. [SANS expert consensus][S28] supports a multifactorial syndrome, not a universal impedance-to-diagnosis conversion. Do not invent one. |
| **Joint kinematics**, degrees or radians | Task- and joint-specific trajectory within an individual's measured movement capacity. | Reduced excursion, new asymmetry, or movement outside the planned task can be simulated; no universal dangerous angle. | **Research:** [CDC primary ROM dataset][S29] provides age/sex-specific measurements. Its confidence intervals describe estimates, not allowed individual angle bounds. Shoulder flexion is not shoulder abduction; wrist values need their own source/calibration. |
| **Exercise compliance**, fraction or % of prescribed work | 100% means completing the declared prescription, not a medical norm. | Missing planned sessions/load is a compliance finding. | **Unvalidated metric:** define denominator, time window, and how partial sessions count. No clinically validated universal normal/critical percentage. NASA monitors countermeasure outcomes, not a generic compliance threshold: [NASA requirements][S30]. |

### Timed acute urine-output criteria

Use the **published KDIGO 2012** urine-output staging, not an unfinalized 2026 public-review draft. These are AKI classification criteria requiring clinical context, not general “low daily urine” bands:

| Urine-output criterion | KDIGO stage |
| --- | --- |
| <0.5 mL/kg/h for 6–12 h | 1 |
| <0.5 mL/kg/h for ≥12 h | 2 |
| <0.3 mL/kg/h for ≥24 h, or no urine for ≥12 h | 3 |

Source: [KDIGO published guideline, Table 2][S31]. Apply the highest applicable stage. A single small void or a daily volume below 2 L cannot supply these timed criteria. Do not diagnose solely from the simulator's 24-hour aggregate when shorter-window flow is unavailable.

### NEWS2: acute deterioration bands, not healthy reference intervals

Use adult **SpO2 Scale 1** for the ordinary profile. Table entries are **score contributions**. “—” means no band, not missing data. Source: [RCP observation chart][S32]; cross-checked with the [RCP full report, Charts 1–2][S33].

| Channel / unit | Score 0 | Score 1 | Score 2 | Score 3 |
| --- | --- | --- | --- | --- |
| Respirations/min | 12–20 | 9–11 | 21–24 | ≤8 or ≥25 |
| SpO2 % | ≥96 | 94–95 | 92–93 | ≤91 |
| Systolic BP, mmHg | 111–219 | 101–110 | 91–100 | ≤90 or ≥220 |
| Pulse/min | 51–90 | 41–50 or 91–110 | 111–130 | ≤40 or ≥131 |
| Temperature, °C | 36.1–38.0 | 35.1–36.0 or 38.1–39.0 | ≥39.1 | ≤35.0 |

Add 2 for supplemental oxygen; add 3 for new confusion or response only to voice/pain/unresponsiveness. Aggregate **0–4 low**, **5–6 medium/urgent**, **≥7 high/emergency response**; a single component of 3 needs urgent review even with a low sum. No missing component may default to zero. Special Scale 2 is a separate clinician-selected pathway. [RCP full report][S33]

Simulation interpretation: a zero NEWS2 contribution is not proof of health (for example, its SBP zero-score interval includes hypertension). Round observations to the chart's measurement precision before classification; do not leave gaps between decimal temperatures such as 36.0 and 36.1.

## 3. Neurocognitive, sleep, behavioral, and visual channels — historical, excluded

| Channel | Expected / reference | Concerning / severe interpretation | Evidence and limits |
| --- | --- | --- | --- |
| **EEG PSD and band powers** | Nonnegative spectrum; declare montage, reference, filtering, units and epoch. Project bands: theta 4–8 Hz, alpha 8–13 Hz. | Compare like-for-like awake task recordings with baseline; fatigue effects vary by region/task. | **Research:** [primary mental-fatigue EEG experiment][S34]. No universal healthy μV²/Hz or band-power range. Specify nonoverlapping numerical integration at 8 Hz. |
| **Theta/alpha ratio / CFE** | Derive theta power / alpha power from the same epoch, with a nonzero reliable denominator. | A change can be a research feature. | **Unvalidated cutoff:** no support verified for the PDF's <0.70 / 0.70–1.20 / >1.20 classes. [EEG experiment][S34] is not validation of those cutoffs. Normal sleep must not become a “critical microsleep” diagnosis. |
| **Actigraphy / sleep stage** | Device-specific activity measure; wake/NREM/REM classifications need a declared algorithm. | Disrupted movement/sleep patterns can support a scenario, but actigraphy alone is not a universal stage classifier. | **Research:** [AASM actigraphy guideline][S35]. No generic healthy count range or critical actigraphy value. Keep actigraphy and inferred stages distinct. |
| **Sleep duration**, h per 24 h/night | Healthy adults generally need **≥7 h regularly**; **7–9 h** is a reasonable consensus-supported planning interval. | Habitual <7 h is associated with health/performance risk. | **Clinical/consensus:** [AASM/SRS statement][S36], [methodology][S37]. No validated single “critical hours” threshold; cumulative restriction and individual need matter. >9 h is not automatically disease. |
| **Sleep efficiency**, % | Asleep time / time in bed ×100. **>85%** is the good-quality indicator reported in the cited consensus summary, not proof of complete sleep health. | Lower efficiency merits pattern/context assessment. | **Consensus:** [CTA/NSF standard, Table 1][S38] summarizes earlier NSF consensus for context, rather than making it a requirement of the standard. No universal emergency cutoff. High efficiency with very short sleep still permits severe sleep deficiency. |
| **Sleep debt**, h | Explicit model: accumulated deficit relative to the individual's configured sleep need. | Increasing deficit can drive impaired performance. | **Unvalidated scalar:** [sleep consensus][S36] does not define a universal debt score or recovery law. Do not assert that one extra hour repays one hour of biological debt. |
| **PVT reaction time**, ms; **PVT lapse count** | Use a named test protocol and personal rested distribution; not a generic population mean. | The standard 10-minute PVT commonly counts **RT ≥500 ms** as a lapse; shortened protocols may use different thresholds. | **Research:** [Basner protocol study][S39], independently [10- vs 3-minute comparison][S40]. No universal critical count. The PDF's 5-minute test with >500 ms is a project convention, not validated by merely citing the 10-minute rule. |
| **PHQ-9**, integer 0–27 | **0–4** minimal. | **5–9** mild; **10–14** moderate; **15–19** moderately severe; **20–27** severe symptom burden. | **Research/validated questionnaire:** [original Kroenke validation][S41]. Standard recall is the **previous two weeks**, not a new independent daily symptom score. Item-level risk and functioning cannot be recovered from the total alone; “severe” is not a numerical emergency diagnosis. |
| **GAD-7**, integer 0–21 | **0–4** minimal. | **5–9** mild; **10–14** moderate; **15–21** severe symptoms. | **Research/validated questionnaire:** [original Spitzer validation][S42]. Previous-two-week instrument; the labels are screening severity, not autonomous diagnoses or emergency bands. |
| **Mood score** | No named instrument, scale or direction in the PDF. | Cannot define verified normal/concerning/critical ranges. | **Unvalidated:** either select and cite an actual instrument or label a synthetic ordinal scale. Do not equate it with PHQ-9/GAD-7. |
| **Headache flag**, boolean | False means the symptom is absent, not that no neurological risk exists. | True needs onset, severity and accompanying features. | **Clinical:** [NICE headache guidance][S43]: sudden peak within 5 minutes, fever-related worsening, or new neurological/cognitive deficit are red flags. A boolean alone cannot classify urgency or prove CO2 exposure. |
| **Visual acuity**, logMAR, separately per eye | **0.0 = 20/20**; lower/negative values indicate better acuity. | Worsening from corrected baseline is meaningful; example **0.3 ≈20/40**, **1.0 =20/200** describe acuity, not acute severity classes. | **Measurement:** [AAO acuity explanation][S44]. No universal critical logMAR for this simulator. Sudden change, eye, correction and test conditions matter; 20/20 does not exclude disease. |
| **Amsler grid result**, categorical | No new distortion/missing areas relative to baseline. | New wavy/missing regions are an abnormal screening result requiring assessment. | **Clinical:** [AAO Amsler guidance][S45]. No numerical severity scale; neither a normal result nor visual acuity alone excludes SANS. |

## 4. Environmental channels

| Channel | Expected / permitted context | Concerning / high-exposure criterion | Interpretation and evidence |
| --- | --- | --- | --- |
| **Ambient ppCO2**, mmHg or Pa | NASA nominal habitat requirement: **average over 1 h ≤3 mmHg ≈400 Pa**. | Exceeding that average is operationally off-nominal. NASA's cited requirement does not supply a universal off-nominal emergency band. | **Operational:** [NASA-STD-3001 Vol. 2, current Revision F text, V2 6004][S46]. Concentration in ppm requires total cabin pressure: `ppCO2 = ppm × total_pressure / 10^6`. This is not blood PaCO2. |
| **CO2 comparison limits**, ppm, terrestrial occupational | NIOSH REL time-weighted concentration **5000 ppm**. | Short-term **30,000 ppm**; **40,000 ppm IDLH**. | **Operational:** [NIOSH Pocket Guide][S47], [IDLH rationale][S48]. Keep averaging durations (TWA up to 10 h workday; short-term 15 min) and setting explicit; see [NIOSH definitions][S59]. These are not NASA cabin targets. |
| **Light exposure**, photopic lux | No single normal lux value across work, sleep and tasks. | Excess evening/night light or insufficient day light can be a circadian input. | **Consensus:** [Brown et al.][S49] recommends **melanopic EDI ≥250 lux daytime**, **≤10 lux during the 3 h before bed**, **≤1 lux during sleep**, measured at the eye. Photopic lux is not melanopic EDI: do not apply these thresholds to the existing lux channel without spectral information. |
| **Cumulative radiation dose**, mSv | ALARA; NASA **career effective dose <600 mSv**, including prior missions. | ≥600 exceeds that career requirement; it is not the onset of acute radiation syndrome. | **Operational:** [NASA V1 4030][S30]. Effective dose in Sv cannot substitute for organ absorbed dose in Gy or NASA mGy-Eq. |
| **Radiation dose rate**, µSv/h | Mission/location dependent. For systems supporting >60 days, NASA GCR design requirements are **<1.3 mSv/day free space**, **<0.9 mSv/day planetary surface**. | Equivalent constant averages ≈**54.17** and **37.5 µSv/h**, respectively, are design comparisons, not immediate alarm thresholds. | **Operational:** [NASA V1 4033][S30]. Do not treat these as expected healthy ranges or apply planetary limits to every environment. A medical critical rate requires spectrum, duration, shielding and dose definition. |
| **SPE flag**, boolean | False for the ordinary scenario. | True marks an environmental event requiring a mission-specific hazard policy, not proof of current illness. | **Operational:** NASA V1 4031 specifies protection from a **design-reference SPE to <250 mSv effective dose**; it does not define a sensor flag trigger. [NASA][S30]. Never wait for accumulated dose to reach that design limit before representing an event alert. |

Dose consistency: for a µSv/h rate, `delta_dose_mSv = rate × elapsed_seconds / 3_600_000`. Accumulated dose must not decrease because of sensor noise; noisy instantaneous measurements and latent integrated dose are separate model quantities. **Current ownership:** integrate an ambient monitor's declared dose quantity separately from a person's effective/career dose. The career and design limits above do not directly classify an ambient counter. Do not convert absorbed dose in Gy to equivalent/effective dose in Sv without a declared radiation/exposure model. See the current plan for environmental identifiers and schedules.

## 5. Sensor physics — historical, excluded

The following constants and audit refer to the **previous six-page PDF**, not the updated ten-page edition. They are retained as historical research only: do not implement these values. The revised PDF changes displacement/gauge-factor bands and examples; sensor electrical outputs are outside the current scope. Their numerical calibration was not independently validated by this research.

| Channel | Mathematical / project domain | Normal/concerning/critical status |
| --- | --- | --- |
| **Hydrogel displacement** | ΔL in mm, project 0–9.99; L0≈50 mm. ε=ΔL/L0. | Engineering domain only. Out of domain = model/sensor validity issue, not automatically injury. |
| **Hydrogel strain** | Fraction internally; percent=100ε. Project also gives ε=tfilm·θ/(2L0), tfilm=1.2 mm and θ in radians. | Joint geometry must justify that mapping. Do not independently generate mutually inconsistent angle, displacement and strain. |
| **Dynamic gauge factor** | Project: 1180.75 at 0–5%; 233.48–389.58 at 5–15%; 74.34–114.86 at 15–30%. | No verified clinical bands. Boundary ownership, interpolation and discontinuities must be resolved before implementation. |
| **Hydrogel resistance and ΔR/R0** | R0=0.45089 Ω; ΔR/R0=GF·ε; R=R0(1+GF·ε). | No universal healthy resistance. Use model consistency and sensor fault flags. |
| **GFET ΔIds/I0** | Project model `0.65*C/(14.8+C)` for C≥0 nM: response **0 ≤ y <0.65** for finite C. | The bound is mathematical, not a disease cutoff. Inherit a concentration interpretation only after assay/specimen calibration. |
| **GFET threshold shift ΔVt** | Project Debye expression needs SI conversion and a concentration-to-bound-density model. | No trustworthy normal/critical mV range established. With δ=3.5 nm and λD=1 nm its factor `1−δ/(2λD)` is **−0.75**; verify model validity rather than silently clipping the sign. |

Source audit:

- [Bučinskas et al. 2025][S50] is a real carrageenan/iron-oxide force-sensor study. Its published description concerns force/voltage and piezoelectric behavior; it does not, from the material verified here, establish the project's three GF bands or clinical strain alerts. Full-page access was limited; the publisher/PMC indexed content and bibliographic record were available.
- [Lakshmanakumar et al. 2019][S51] is an **antibody-free graphene-quantum-dot electrochemical** experiment using voltammetry/amperometry, not validation of the project's antibody-layer GFET Debye equation. Reported analytical range **0.17–3 ng/mL**, detection limit **0.02 ng/mL**: the PDF's 0.005 ng/mL example is below that experiment's detection limit. Analytical detection limits are not clinical troponin decision limits.
- The [2026 cortisol paper's publisher record][S52] exists and identifies **serum cortisol/SERS**. Full text was inaccessible here. A Raman/SERS title is insufficient evidence for a GFET Kd=14.8 nM or Imax=0.65; those constants remain unverified.
- The PDF's incompletely specified Liu/Cernat references do not identify a verifiable source for the exact EEG cutoffs or all hydrogel coefficients. Treat those claims as unresolved, not validated by association with a reference list.

## 6. Derived quantities and backend-owned decisions

| Quantity | Evidence-based interpretation / implementable rule | Limits |
| --- | --- | --- |
| **Postural SBP drop** | Classic orthostatic hypotension: sustained **SBP fall ≥20 mmHg OR DBP fall ≥10 mmHg within 3 min** of standing/head-up tilt. [EFAS/AAS/EAN consensus][S53] | Specify baseline, posture and timing. A normal-gravity stand-test criterion is not directly applicable to floating in microgravity. |
| **Postural HR rise** | Adult POTS criterion includes **rise ≥30 bpm**, standing symptoms and absence of orthostatic hypotension. [HRS consensus][S54] | Do not equate one postural change with POTS, or apply it during exercise; chronicity/exclusions and test protocol matter. The PDF's BP-drop and HR-rise criteria are different findings. |
| **Shock index** | `HR_bpm / SBP_mmHg`; original ED study describes **0.5–0.7**, with **>0.9** identifying a higher-risk group. [Rady et al.][S55] | No universal critical value. Do not divide SI-wire HR by Pa and expect these numerical limits; convert first. Exercise and medication alter interpretation. |
| **NEWS2** | Use Section 2; all inputs and oxygen/consciousness status required. | Score is an acute-illness escalation tool, not an infection diagnosis or a generic health percentage. |
| **qSOFA** | One point each: **RR ≥22/min**, **SBP ≤100 mmHg**, **altered mentation**; **≥2** indicates higher poor-outcome risk in suspected infection. [Sepsis-3][S11] | Zero/one does not exclude sepsis. [Surviving Sepsis Campaign][S56] advises against using qSOFA alone as the screening tool. Mental status is missing from the present measurement inventory and must be supplied explicitly. |
| **Weekly body-mass slope** | Report kg/week or % baseline/week from a declared model window. | No verified astronaut-specific critical slope. Acute fluid loss is not the same as chronic nutritional tissue loss; use the body-mass guidance above with the correct timescale. |
| **NTx slope / percentage** | Derived from creatinine-normalized, time-matched values. | No verified universal percentage/slope severity bins; use the assay and baseline guidance in Section 1. |
| **Cortisol diurnal slope** | A time-matched decline from waking toward bedtime is expected; define raw versus log-concentration slope and exclude/handle the awakening response consistently. [Mayo SALCC][S06] | No universal nM/h depression or emergency threshold. A flattened curve is not a diagnosis; shift work and circadian timing matter. |
| **CFE, PVT lapse count, sleep debt, mood score** | Covered in Section 3; derive from their source observations or declared synthetic definition. | Do not generate independent contradictory copies. |
| **Estimated intracranial pressure**, mmHg | A project sensor estimate has **no validated reference range until its mapping is validated**. In a separate severe-TBI context, measured ICP **>22 mmHg** is a treatment threshold. [Brain Trauma Foundation guideline][S57] | That TBI threshold does not validate a hydrogel-based ICP estimate or diagnose SANS. [SANS consensus][S28] notes direct in-flight ICP has not been measured. The PDF's 14.8 is an example, not evidence of a normal astronaut ICP. |
| **Lumbar asymmetry ratio** | Must define numerator, denominator, side conventions and task. | No verified threshold for the PDF's ratio 1.28. A ratio of 1 only implies equality if that is how the metric is defined. |
| **Form status** | Derived from a named exercise protocol, valid kinematics and configured technique rules. | No universal normal/warning/critical angle set. “WARNING” in the PDF is a demo output. |
| **Overall status / primary hazard / recommended actions** | Backend-owned contextual decisions, not measured biomarkers. | No numeric range. Do not emit medical advice by merely crossing an unvalidated sensor threshold. |

## 7. Rules for future healthy, ill, and severely ill scenarios

1. **Choose a condition and time course first.** Distinguish infection, hypoxia, dehydration, endocrine disease, sleep restriction and radiation exposure. There is no generic “ill” vector in which every channel becomes abnormal together.
2. **Use the correct specimen and assay.** A simulated blood analyte is not automatically measurable in sweat with the same concentration. Keep the physical sensor response downstream of the physiological model.
3. **Keep clinical prerequisites.** Sepsis/shock needs more than lactate or a positive viral flag; myocardial injury is not automatically infarction; kidney injury needs time windows; diabetes crises need additional chemistry. Add those prerequisites to the scenario definition when implementing that disease.
4. **Model state-dependent exceptions.** Healthy exercise raises pulse, respiration, sweating and lactate; sleep changes EEG. Do not distort them to stay inside resting clinical ranges.
5. **Use time scales.** Pulses and breathing vary rapidly; meals affect glucose over time; cortisol has a daily rhythm; vitamin D and bone turnover should not jump every sampling tick. Severity is a trajectory, duration and symptom pattern, not only a threshold crossing.
6. **Separate synthetic defaults from evidence.** A default astronaut mass, narrow resting HR distribution, mild-illness waveform or calibration constant is a simulation choice. Record its rationale and avoid citing it as a published population range.
7. **Keep nonclinical errors separate.** Missing readings, impossible percentages, negative concentrations, sensor saturation, zero EEG denominator and expired inputs are validity problems. They are not automatically `critical` astronaut health.

This document supplies verified interpretation constraints for scenario design. It does **not** validate every possible disease trajectory; each new disease scenario still needs condition-specific evidence and review.

## 8. Unit conversions to implement and test

The clinical tables intentionally preserve the source units so thresholds remain auditable. Convert explicitly before applying them to SI-wire values.

| Conversion | Rule |
| --- | --- |
| mmHg → Pa | ×133.322387415 (conventional mmHg) |
| °C → K | +273.15 |
| beats/min or breaths/min → s⁻¹ | ÷60 |
| ms → s | ÷1000 |
| degrees → radians | ×π/180 |
| percent → fraction | ÷100; distinguish NTx percent **change** from percent **of** baseline |
| glucose mg/dL → mmol/L | ×0.05551 (approximately ÷18.0156) |
| cortisol µg/dL → nmol/L | ×27.59; cortisol ng/dL → nmol/L: ×0.02759 |
| 25-OH vitamin D ng/mL → nmol/L | ×2.5 |
| troponin ng/mL → ng/L | ×1000; ng/L → kg/m³: ×10⁻⁹ |
| mmol/L → mol/m³ | Numerically identical |
| nmol/L → mol/m³ | ×10⁻⁶ |
| L/h → m³/s | ÷3,600,000 |
| mmol/h → mol/s | ÷3,600,000 |
| L/day → m³/s, mean flow only | ÷86,400,000; keep the original integration window |
| mSv → Sv | ÷1000 |
| µSv/h → Sv/s | ÷3,600,000,000 |
| EEG μV²/Hz → V²/Hz | ×10⁻¹² |

Biochemical conversion factors were cross-checked against [Mayo's SI conversion catalog][S58]. Unit conversion does not transfer assay validity, turn photopic lux into melanopic EDI, or turn effective radiation dose into absorbed dose.

## 9. Original verification record and conflicts with the previous PDF

The current 10-page PDF comparison and NASA cadence verification are in [NASA_MONITORING_PLAN.md](NASA_MONITORING_PLAN.md). This original record explains earlier research and does not claim that old sample/formula inconsistencies remain unchanged in the new PDF.

| Check | Result |
| --- | --- |
| Scope coverage | All README rows have an entry above, including assessments, environment, sensor physics, trends, and backend decisions. Compound rows are split where their interpretations differ. |
| Glucose | NIDDK/CDC diagnostic categories agree; ADA classification confirms 54/70 boundaries and nonnumerical severe hypoglycemia. Crisis criteria checked separately. |
| Vital signs | Cross-checked general AHA/MedlinePlus ranges against RCP scoring. Differences are retained because population reference intervals and acute risk scores serve different purposes. |
| Cortisol | Read current saliva and serum lab references; confirmed orders-of-magnitude specimen differences. PDF's generic 22.4/30 nM warning/critical rules are not accepted as clinical truth. |
| Troponin | Checked named clinical assay and original sensor paper. Clinical assay thresholds and electrochemical analytical sensitivity are different; neither verifies the PDF's universal rule. |
| NTx and vitamin D | Verified assay-specific NTx units/sex categories and NIH vitamin-D classification. Neither supports invented critical percent-change limits. |
| Urine | Cross-checked general USG, AUA stone-prevention target and published KDIGO timed AKI criteria. PDF <2 L/day is a project risk flag, not an AKI emergency threshold. |
| EEG/PVT | Did not verify the exact CFE thresholds. PVT literature uses protocol-specific lapse boundaries; PDF duration and strict > boundary are not identical to a standard ≥ definition. |
| Questionnaires | Original validations support severity bands; two-week recall conflicts with treating each daily check-in as an independent new two-week assessment. |
| Radiation and CO2 | Checked NASA requirement identifiers and exposure windows. Career dose, GCR design rate, SPE protection and occupational IDLH must not be merged into one medical scale. |
| Sensor citations | Identified material/technique mismatches and inaccessible or incompletely identified evidence. Unverified constants remain explicitly labelled. |
| Unknown custom indices | No false numerical ranges assigned to mood, fluid index, asymmetry, form, compliance or sensor-derived ICP. |

Verification limitations: laboratory intervals are verified against their own performing-laboratory catalogs, not claimed to be universal or independently replicated. Some publisher pages were accessible only through indexed excerpts; those sources are limited below. Scientific validity for microgravity is not established merely by a terrestrial citation. Recheck dated standards and assay catalogs when changing the model.

## 10. Sources and trust assessment

Sources are linked next to the claims they support. Government agencies and guideline issuers are used for their own published requirements; performing laboratories for their own assay intervals; original studies for observations. A journal title, PubMed listing or NASA affiliation alone does not validate an unrelated project formula. No commercial wellness-range aggregator, social post or AI summary is used as evidence.

| IDs | Source quality and scope |
| --- | --- |
| S01–S05 | NIDDK/CDC and ADA/multi-society diagnostic guidance. High authority for stated diabetes classifications; not wearable calibration. |
| S06–S10, S12 | Mayo/UW performing-laboratory catalogs. Strong assay-specific provenance; intervals cannot be generalized across assays. |
| S11, S31–S33, S53–S54, S56–S57 | Original consensus/guideline documents from clinical societies. Strong authority within their clinical setting; not astronaut-specific validation. |
| S13 | NIH Office of Dietary Supplements synthesis of NASEM and other guidance; preserves stated uncertainty and toxicity context. |
| S14–S15, S19–S20, S29, S34, S39–S42, S55 | Original cohorts/experiments/instrument validation. Trustworthy for their methods and populations; weaker for extrapolated clinical cutoffs. |
| S16–S17, S28 | NASA investigations/clinical study and SANS expert consensus. Relevant spaceflight context; S28 indexed text available, full publisher page access failed. |
| S18, S21–S25, S43–S45 | Issuing professional bodies, NIH medical information, and NICE. Suitable for stated general guidance; do not replace assay/protocol detail. S44 is AAO-hosted educational material used for measurement conversion, not clinical triage. |
| S26–S27 | AUA current 2026 and earlier stone guidelines; independently matching volume target. |
| S30, S46–S48 | NASA standards/official requirements and CDC/NIOSH exposure limits. Authoritative operational limits with distinct scopes. |
| S35–S38, S49 | Sleep society guidelines/consensus and circadian expert consensus. Suitable for sleep/light recommendations, not universal disease thresholds. |
| S50–S52 | Sensor research. S51 full article read; S50 indexed content/bibliography checked with limited page access; S52 publisher record/title only, full text blocked. No unverified GFET coefficients adopted. |
| S60–S61 | Performing-laboratory IL-6 reference and NASA medical standard. Support serum assay interpretation and astronaut vitamin D policy respectively; neither validates continuous GFET sensing. |
| S59 | NIOSH official definitions of averaging periods; used to distinguish TWA and short-term limits. |
| S58 | Performing laboratory's conversion reference. Supports biochemical units, not disease thresholds. |

[S01]: https://www.niddk.nih.gov/health-information/diabetes/overview/tests-diagnosis "NIDDK — Diabetes Tests & Diagnosis"
[S02]: https://www.cdc.gov/diabetes/diabetes-testing/index.html "CDC — Diabetes Testing"
[S03]: https://professional.diabetes.org/sites/dpro/files/2025-04/hypoglycemia-patient-2025-4-22-25.pdf "ADA — Hypoglycemia classification, 2025"
[S04]: https://diabetesjournals.org/compendia/article/2026/1/7/172319/Chapter-2-Hypoglycemia-Classification-and "ADA — Hypoglycemia Classification and Epidemiology, 2026"
[S05]: https://diabetesjournals.org/care/article/47/8/1257/156750/Hyperglycemic-Crises-in-Adults-With-Diabetes-A "ADA and partner societies — Hyperglycemic Crises, 2024"
[S06]: https://www.mayocliniclabs.com/test-catalog/overview/623604 "Mayo — SALCC cortisol and cortisone, saliva"
[S07]: https://www.mayocliniclabs.com/test-catalog/Overview/8545 "Mayo — CORT cortisol, serum"
[S08]: https://www.mayocliniclabs.com/test-catalog/Overview/65484 "Mayo — CORTO free and total cortisol, serum"
[S09]: https://testguide.labmed.uw.edu/view/TROPBC?tabs=yes "UW Medicine — Beckman high-sensitivity troponin I"
[S10]: https://www.mayocliniclabs.com/test-catalog/Overview/601685 "Mayo — LACS1 lactate, plasma"
[S11]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4968574/ "Singer et al. — Sepsis-3, JAMA 2016"
[S12]: https://testguide.labmed.uw.edu/view/RUNTXP "UW Medicine — Urinary NTx sendout"
[S13]: https://ods.od.nih.gov/factsheets/VitaminD-HealthProfessional/ "NIH ODS — Vitamin D health professional fact sheet"
[S14]: https://pmc.ncbi.nlm.nih.gov/articles/PMC9942894/ "Baker et al. — Variation in sweat sodium, primary study"
[S15]: https://pmc.ncbi.nlm.nih.gov/articles/PMC7399373/ "Baker et al. — Regional/whole-body sweat sodium cross-validation, 2020"
[S16]: https://www.nasa.gov/humans-in-space/nasa-investigates-how-dormant-viruses-behave-during-spaceflight/ "NASA — Dormant viruses during spaceflight"
[S17]: https://ntrs.nasa.gov/citations/20220004358 "NASA NTRS — Dermatitis during spaceflight associated with HSV-1 reactivation"
[S18]: https://www.heart.org/en/healthy-living/exercise-and-physical-activity/fitness-basics/target-heart-rates/ "AHA — Target Heart Rates"
[S19]: https://pmc.ncbi.nlm.nih.gov/articles/PMC7734556/ "Lifelines cohort — 10-second ECG HRV reference values"
[S20]: https://pmc.ncbi.nlm.nih.gov/articles/PMC5010946/ "MESA — Short-term HRV reference ranges, 2016"
[S21]: https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings/ "AHA — Understanding Blood Pressure Readings"
[S22]: https://www.medlineplus.gov/lab-tests/pulse-oximetry/ "MedlinePlus — Pulse Oximetry"
[S23]: https://www.medlineplus.gov/ency/article/002341.htm "MedlinePlus — Vital Signs"
[S24]: https://pubmed.ncbi.nlm.nih.gov/17277604/ "ACSM — Exercise and Fluid Replacement, 2007"
[S25]: https://www.medlineplus.gov/ency/article/003587.htm "MedlinePlus — Urine Specific Gravity"
[S26]: https://www.auajournals.org/doi/full/10.1097/JU.0000000000005227 "AUA — Medical Management of Kidney Stones, 2026, Part I"
[S27]: https://www.auajournals.org/doi/10.1016/j.juro.2014.05.006 "AUA — Medical Management of Kidney Stones, 2014"
[S28]: https://www.nature.com/articles/s41433-026-04651-6 "SANS expert consensus on diagnosis and management, Eye, 2026"
[S29]: https://archive.cdc.gov/www_cdc_gov/ncbddd/jointrom/index.html "CDC — Normal Joint Range of Motion Study"
[S30]: https://www.nasa.gov/reference/4-0-human-performance/ "NASA — Human Performance, NASA-STD-3001 Volume 1 requirements"
[S31]: https://kdigo.org/wp-content/uploads/2016/10/KDIGO-2012-AKI-Guideline-English.pdf "KDIGO — Published 2012 AKI guideline, Table 2"
[S32]: https://www.rcp.ac.uk/media/eczf5mvm/news2-chart-3_news-observation-chart_2022_0_0.pdf "RCP — NEWS2 observation chart, 2022"
[S33]: https://www.rcp.ac.uk/media/a4ibkkbf/news2-final-report_0_0.pdf "RCP — NEWS2 full report, 2017"
[S34]: https://pmc.ncbi.nlm.nih.gov/articles/PMC3804027/ "Tanaka et al. — Mental fatigue EEG experiment"
[S35]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6040807/ "AASM — Actigraphy clinical practice guideline, 2018"
[S36]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4434546/ "AASM/SRS — Adult sleep duration consensus, 2015"
[S37]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4513271/ "AASM/SRS — Sleep duration consensus methodology"
[S38]: https://www.thensf.org/wp-content/uploads/2025/03/ANSI-CTA-NSF-2110-FINAL.pdf "CTA/NSF — Consumer technology sleep quality standard"
[S39]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10104405/ "Basner — Adaptive PVT protocol study"
[S40]: https://pmc.ncbi.nlm.nih.gov/articles/PMC8885985/ "Primary comparison of 3- and 10-minute PVT"
[S41]: https://pmc.ncbi.nlm.nih.gov/articles/PMC1495268/ "Kroenke et al. — Original PHQ-9 validation, 2001"
[S42]: https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/410326 "Spitzer et al. — Original GAD-7 validation, 2006"
[S43]: https://www.nice.org.uk/guidance/cg150/chapter/Recommendations "NICE CG150 — Headache assessment, updated 2025"
[S44]: https://eyewiki.aao.org/Visual_Acuity_Testing_in_Adults "AAO EyeWiki — Visual Acuity Testing"
[S45]: https://aao.org/eye-health/tips-prevention/facts-about-amsler-grid-daily-vision-test "AAO — Amsler Grid"
[S46]: https://www.nasa.gov/reference/6-0-natural-and-induced-environments-vol-2/ "NASA-STD-3001 Volume 2 Revision F — V2 6004 and V2 6020, checked 2026-11-14"
[S47]: https://www.cdc.gov/niosh/npg/npgd0103.html "NIOSH Pocket Guide — Carbon dioxide"
[S48]: https://www.cdc.gov/niosh/idlh/124389.html "NIOSH — Carbon dioxide IDLH rationale"
[S49]: https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3001571 "Brown et al. — Day/evening/night light consensus, 2022"
[S50]: https://pmc.ncbi.nlm.nih.gov/articles/PMC12349296/ "Bučinskas et al. — Carrageenan force sensor, 2025"
[S51]: https://www.nature.com/articles/s41598-019-53979-5 "Lakshmanakumar et al. — Electrochemical troponin sensor, 2019"
[S52]: https://pubs.acs.org/ascefj/article/doi/10.1021/acssensors.6c02418/5454834/Sandwich-SERS-Chip-with-Raman-Silent-Reporters-for "2026 serum-cortisol SERS paper — publisher record only verified"
[S53]: https://pmc.ncbi.nlm.nih.gov/articles/PMC8184725/ "EFAS/AAS/EAN — Tilt-testing consensus, 2021"
[S54]: https://pmc.ncbi.nlm.nih.gov/articles/PMC5267948/ "Heart Rhythm Society — POTS consensus, 2015"
[S55]: https://pubmed.ncbi.nlm.nih.gov/8092595/ "Rady et al. — Shock index and critical illness, 1994"
[S56]: https://pmc.ncbi.nlm.nih.gov/articles/PMC8486643/ "Surviving Sepsis Campaign guideline, 2021"
[S57]: https://doi.org/10.1227/neu.0000000000001432 "Brain Trauma Foundation — Severe TBI guideline, fourth edition"
[S58]: https://www.mayocliniclabs.com/order-tests/si-unit-conversion.html "Mayo — SI conversion catalog"

[S59]: https://www.cdc.gov/niosh/npg/pgintrod.html "NIOSH Pocket Guide — Definitions of exposure averaging times"
[S60]: https://www.mayocliniclabs.com/test-catalog/overview/618776 "Mayo IL6DX — Interleukin-6, Serum; performing laboratory interval"
[S61]: https://www.nasa.gov/wp-content/uploads/2024/09/ochmo-std-100-1a-rev-a-signed.pdf "NASA OCHMO-STD-100.1A Revision A, §6.7.1 vitamin D"
