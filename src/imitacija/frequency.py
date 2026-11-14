"""Executable interpretation of docs/frequency_table.md for implemented channels.

Raw acquisition, publication and backend clinical evaluation are different clocks.
The simulator evaluates latent raw samples on demand for completed windows; it
never publishes 100 scalar heart rates per second as a substitute for a PPG waveform.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Frequency:
    """Project timing policy; missing interval means a calendar/event acquisition."""

    description: str
    raw_hz: float | None = None
    interval_s: float | None = None
    window_s: float = 0
    rows: tuple[int, ...] = ()


FREQUENCIES: dict[str, Frequency] = {
    "heart": Frequency("60s HR estimate; first complete window at 60s", 100, 60, 60, (1,)),
    "hrv": Frequency("60s RMSSD window every 60s; first at 61s", 100, 60, 60, (1,)),
    "bp": Frequency(
        "hourly in configured session; optional 10Hz / 180s stand-test burst", rows=(1,)
    ),
    "spo2": Frequency(
        "1Hz scalar pulse-oximetry; backend acute checks every 5s", 1, 1, rows=(3, 4)
    ),
    "temperature": Frequency("1Hz core-equivalent temperature", 1, 1, rows=(3,)),
    "respiration": Frequency(
        "60s respiratory estimate every 60s; first at 77s", interval_s=60, window_s=60, rows=(3, 4)
    ),
    "glucose": Frequency(
        "5-minute CGM result from 5s raw samples; first at 343s", 0.2, 300, 300, (7,)
    ),
    "sweat": Frequency(
        "1Hz local flow/concentration while active and wet; no resting acquisition", 1, 1, 1, (2,)
    ),
    "sweat_summary": Frequency(
        "60s integrated local sodium loss rate while active and wet", 1, 60, 60, (2,)
    ),
    "cortisol": Frequency("every 4 waking hours: 07:00/11:00/15:00/19:00/23:00 daily", rows=(6,)),
    "troponin": Frequency("configured assay events only; default synthetic baseline", rows=(1,)),
    "lactate": Frequency("baseline and configured exercise-test sessions; not specified by matrix"),
    "vitamin": Frequency("baseline then every 30 days (monthly simulator convention)", rows=(7,)),
    "il6": Frequency("explicitly configured gated assay events; default baseline only", rows=(3,)),
    "ntx": Frequency(
        "weekly completed 24h urine specimen; first result at FD7", window_s=86400, rows=(8,)
    ),
    "urine": Frequency(
        "completed 24h urine volume daily; first result at FD1", window_s=86400, rows=(8,)
    ),
    "usg": Frequency("spot urine twice daily pre/post activity: 07:00 and 18:30", rows=(2,)),
    "mass": Frequency("daily pre/post activity mass: 07:00 and 18:30", rows=(2, 7)),
    "saliva_pcr": Frequency("saliva PCR every 48h at 09:00 (daily/48h matrix choice)", rows=(3,)),
    "urine_pcr": Frequency(
        "CMV urine PCR every 48h at 10:00; adaptation of viral session cadence", rows=(3,)
    ),
    "co2": Frequency("1Hz cabin CO2; backend acute checks every 5s", 1, 1, rows=(4,)),
    "light": Frequency("1Hz ambient photopic light; no sleep inference", 1, 1, rows=(5,)),
    "radiation": Frequency("1Hz monitor dose-equivalent rate", 1, 1, rows=(10,)),
    "radiation_dose": Frequency("60s integrated monitor dose publication", 1, 60, rows=(10,)),
    "spe": Frequency("1Hz SPE heartbeat, independent of crew state", 1, 1, rows=(10,)),
}
