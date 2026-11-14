# Implemented channel catalog

Active timing: [frequency_mapping.md](frequency_mapping.md), based on [frequency_table.md](frequency_table.md).

Static metadata from `src/imitacija/registry.py`; no generated measurements are stored here. Runtime `--dictionary` reflects enabled channels and configured timing overrides. See [model assumptions](model_assumptions.md) for exact schedules and waveform coefficients.

| Channel | Scope / specimen | Source → wire unit | Collection | Measurement source |
| --- | --- | --- | --- | --- |
| `heart_rate` | crew: wearable | bpm → s^-1 | 60s HR estimate; first complete window at 60s | Synthetic pulse. [Source](https://www.heart.org/en/healthy-living/exercise-and-physical-activity/fitness-basics/target-heart-rates/) |
| `hrv_rmssd` | crew: NN intervals | ms → s | 60s RMSSD window every 60s; first at 61s | RMSSD of generated beat intervals. [Source](https://pmc.ncbi.nlm.nih.gov/articles/PMC5010946/) |
| `bp_systolic` | crew: cuff | mmHg → Pa | hourly in configured session; optional 10Hz / 180s stand-test burst | Paired synthetic cuff. [Source](https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings/) |
| `bp_diastolic` | crew: cuff | mmHg → Pa | hourly in configured session; optional 10Hz / 180s stand-test burst | Paired synthetic cuff. [Source](https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings/) |
| `spo2` | crew: pulse oximeter | % → 1 | 1Hz scalar pulse-oximetry; backend acute checks every 5s | Synthetic pulse oximetry. [Source](https://www.medlineplus.gov/lab-tests/pulse-oximetry/) |
| `body_temperature` | crew: ZHF estimate | degC → K | 1Hz core-equivalent temperature | Synthetic lagged core-equivalent estimate. [Source](https://www.medlineplus.gov/ency/article/002341.htm) |
| `respiratory_rate` | crew: wearable | min^-1 → s^-1 | 60s respiratory estimate every 60s; first at 77s | 60-second respiratory estimate. [Source](https://www.medlineplus.gov/ency/article/002341.htm) |
| `glucose` | crew: interstitial fluid | mmol/L → mol/m^3 | 5-minute CGM result from 5s raw samples; first at 343s | Synthetic CGM with meal lag. [Source](https://www.niddk.nih.gov/health-information/diabetes/overview/managing-diabetes/continuous-glucose-monitoring) |
| `cortisol_saliva` | crew: saliva | nmol/L → mol/m^3 | every 4 waking hours: 07:00/11:00/15:00/19:00/23:00 daily | Synthetic Mayo SALCC-compatible fixture. [Source](https://www.mayocliniclabs.com/test-catalog/overview/623604) |
| `troponin_i` | crew: serum | ng/L → kg/m^3 | configured assay events only; default synthetic baseline | UW Beckman hs-cTnI synthetic fixture. [Source](https://testguide.labmed.uw.edu/view/TROPBC?tabs=yes) |
| `lactate` | crew: plasma | mmol/L → mol/m^3 | baseline and configured exercise-test sessions; not specified by matrix | Synthetic plasma lactate fixture. [Source](https://www.mayocliniclabs.com/test-catalog/Overview/601685) |
| `urinary_ntx` | crew: 24h urine | nmol BCE/mmol creatinine → mol BCE/mol creatinine | weekly completed 24h urine specimen; first result at FD7 | UW CLIA-compatible synthetic fixture. [Source](https://testguide.labmed.uw.edu/view/RUNTXP) |
| `bone_ntx_pct_baseline` | crew: 24h urine | % change → 1 | weekly completed 24h urine specimen; first result at FD7 | 100*(NTx/baseline-1), then percent-to-fraction. [Source](https://testguide.labmed.uw.edu/view/RUNTXP) |
| `vitamin_d_25oh` | crew: serum | ng/mL → mol/m^3 | baseline then every 30 days (monthly simulator convention) | Synthetic serum 25-OH D fixture; conventional 2.5 nmol/L per ng/mL. [Source](https://ods.od.nih.gov/factsheets/VitaminD-HealthProfessional/) |
| `il6_serum` | crew: serum | pg/mL → kg/m^3 | explicitly configured gated assay events; default baseline only | Mayo IL6DX-compatible fixture, not NASA plasma research assay. [Source](https://www.mayocliniclabs.com/test-catalog/overview/618776) |
| `sweat_sodium_concentration` | crew: local sweat | mmol/L → mol/m^3 | 1Hz local flow/concentration while active and wet; no resting acquisition | Filled local patch, 10 cm^2 modeled area. [Source](https://pmc.ncbi.nlm.nih.gov/articles/PMC9942894/) |
| `sweat_sodium_flux` | crew: local sweat | mmol/h → mol/s | 60s integrated local sodium loss rate while active and wet | Matching local concentration times local flow. [Source](https://pmc.ncbi.nlm.nih.gov/articles/PMC9942894/) |
| `sweat_rate` | crew: local sweat | L/h → m^3/s | 1Hz local flow/concentration while active and wet; no resting acquisition | Synthetic 10 cm^2 patch flow; not whole-body sweat rate. [Source](https://pmc.ncbi.nlm.nih.gov/articles/PMC9942894/) |
| `viral_ebv_detected` | crew: saliva | boolean → boolean | saliva PCR every 48h at 09:00 (daily/48h matrix choice) | Synthetic PCR fixture; illustrative detection limit 2 copies/reaction. [Source](https://www.nature.com/articles/s41526-017-0015-y) |
| `viral_vzv_detected` | crew: saliva | boolean → boolean | saliva PCR every 48h at 09:00 (daily/48h matrix choice) | Synthetic PCR fixture; illustrative detection limit 2 copies/reaction. [Source](https://www.nature.com/articles/s41526-017-0015-y) |
| `viral_cmv_detected` | crew: spot urine | boolean → boolean | CMV urine PCR every 48h at 10:00; adaptation of viral session cadence | Synthetic PCR fixture; illustrative detection limit 2 copies/reaction. [Source](https://www.nature.com/articles/s41526-017-0015-y) |
| `body_mass` | crew: mass device | kg → kg | daily pre/post activity mass: 07:00 and 18:30 | Synthetic inertial mass estimate. [Source](https://www.nasa.gov/wp-content/uploads/2024/09/ochmo-std-100-1a-rev-a-signed.pdf) |
| `urine_specific_gravity` | crew: spot urine | 1 → 1 | spot urine twice daily pre/post activity: 07:00 and 18:30 | Prompted synthetic spot-urine fixture. [Source](https://www.medlineplus.gov/ency/article/003587.htm) |
| `urine_volume_24h` | crew: 24h urine | L → m^3 | completed 24h urine volume daily; first result at FD1 | Integral of model urine flow over completed collection. [Source](https://www.auajournals.org/doi/10.1016/j.juro.2014.05.006) |
| `ambient_ppco2` | environment: cabin atmosphere | Pa → Pa | 1Hz cabin CO2; backend acute checks every 5s | Synthetic compartment monitor. [Source](https://www.nasa.gov/reference/6-0-natural-and-induced-environments-vol-2/) |
| `ambient_light_lux` | environment: cabin light | lux → lx | 1Hz ambient photopic light; no sleep inference | Synthetic compartment photometer; no spectral/at-eye inference. [Source](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3001571) |
| `ambient_dose_rate` | environment: radiation monitor | uSv/h → Sv/s | 1Hz monitor dose-equivalent rate | Modeled monitor equivalent dose, not absorbed Gy. [Source](https://ntrs.nasa.gov/api/citations/20240011436/downloads/BEAM-Report-NASA-TP-new.pdf) |
| `ambient_integrated_dose` | environment: radiation monitor | mSv → Sv | 60s integrated monitor dose publication | Exact integral of the same modeled monitor rate. [Source](https://ntrs.nasa.gov/api/citations/20240011436/downloads/BEAM-Report-NASA-TP-new.pdf) |
| `spe_flag` | environment: event feed | boolean → boolean | 1Hz SPE heartbeat, independent of crew state | Healthy fixture with heartbeat. [Source](https://ntrs.nasa.gov/api/citations/20240011436/downloads/BEAM-Report-NASA-TP-new.pdf) |

## Coverage decisions

The 29 channels above implement the current NASA plan. Paired outputs share their physical acquisition. Biochemical saliva, serum, plasma, interstitial and urine specimens remain distinct. Environmental integration is monitor dose equivalent, not personal effective/career dose.

The original README also includes the following excluded or backend-owned outputs:

- sleep/stages/debt.
- mood/PHQ9/GAD7.
- EEG/CFE/PVT.
- headache/visual/Amsler.
- kinematics/exercise compliance.
- cephalic impedance/jugular/ICP.
- hydrogel/GFET.
- NEWS2/qSOFA/diagnosis/recommendations (backend-owned).
- postural changes/shock index/weekly and endocrine slopes (backend-owned).

The remaining original inventory rows map to these channels: sweat sodium flux additionally exposes its underlying concentration; latent viral status splits into three specimen-specific PCR results; NTx exposes normalized measurement and baseline change. Ambient radiation identifiers were renamed to make monitor ownership explicit. No EEG, visual, questionnaire or sensor-electrical outputs are generated.

Schedule and waveform precision are simulation choices. Public NASA cadence is unknown for some channels; see the evidence tables in [NASA_MONITORING_PLAN.md](../NASA_MONITORING_PLAN.md).
