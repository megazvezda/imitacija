"""Elapsed-time healthy trajectories independent of collection frequency or delivery.

These are deliberately modest phenomenological waveforms, not validated disease or
space-adaptation models. Deterministic Fourier noise provides temporal correlation
without keeping telemetry history or consuming RNG draws when a channel is sampled.
"""

from __future__ import annotations

import hashlib
import math
import random
from functools import lru_cache

from .models import AstronautProfile, Environment

DAY = 86400.0


@lru_cache(maxsize=4096)
def phase(seed: int, owner: str, channel: str) -> float:
    """Stable per-channel random stream identity; Python's randomized hash is unsuitable."""
    digest = hashlib.sha256(f"{seed}:{owner}:{channel}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big")).uniform(0, 2 * math.pi)


def noise(t: float, seed: int, owner: str, channel: str, period: float = 600) -> float:
    """Smooth bounded noise evaluated at time, so polling changes do not change physiology."""
    p = phase(seed, owner, channel)
    return 0.65 * math.sin(t / period + p) + 0.35 * math.sin(t / (period * 2.37) + 2 * p)


def activity(t: float) -> float:
    """Daily moderate exercise peaks at 17:30, followed by a smooth slower recovery."""
    hour = t % DAY / 3600
    width = 0.40 if hour <= 17.5 else 0.65
    return math.exp(-(((hour - 17.5) / width) ** 2))


def hydration(t: float) -> float:
    """Small fluid deficit during exercise with routine replacement; never clinical illness."""
    return 0.18 * activity(t) + 0.04 * math.sin(2 * math.pi * t / DAY)


def heart_rate(t: float, profile: AstronautProfile, seed: int) -> float:
    """Activity, circadian phase and low-amplitude pulse noise share a continuous context."""
    return (
        profile.resting_hr_bpm
        + 48 * activity(t)
        + 3 * math.sin(2 * math.pi * (t / DAY - 0.32))
        + 0.8 * noise(t, seed, profile.id, "heart_rate", 30)
    )


def rmssd(t: float, profile: AstronautProfile, seed: int, window_s: float = 60) -> float:
    """Compute RMSSD from a complete 60-second simulated NN-interval window.

    Respiratory sinus arrhythmia modulates beat intervals around instantaneous pulse.
    The beat sequence is local temporary computation, discarded after the window.
    This is never estimated from the sparse published heart-rate stream.
    """
    if t < window_s or window_s <= 0:
        raise ValueError("HRV needs a completed positive-duration window")
    beat = t - window_s
    previous_peak: float | None = None
    previous: float | None = None
    squared = 0.0
    differences = 0
    while beat < t:
        base = 60 / heart_rate(beat, profile, seed)
        target = profile.rmssd_ms / 1000 * (1 - 0.5 * activity(beat))
        # Consecutive samples of a sine differ by 2*sin(pi*f*NN); normalize so
        # varying mean heart rate does not itself dictate the intended RMSSD.
        amplitude = target / (math.sqrt(2) * max(0.2, abs(math.sin(math.pi * 0.23 * base))))
        nn = base + amplitude * math.sin(2 * math.pi * 0.23 * beat)
        if beat + nn > t:
            break
        beat += nn
        # Model pulse-peak localization on the matrix's 100Hz raw time grid.
        # This is a synthetic beat extractor, not a validated raw PPG morphology.
        peak = round(beat * 100) / 100
        if previous_peak is not None:
            measured_nn = peak - previous_peak
            if previous is not None:
                squared += (measured_nn - previous) ** 2
                differences += 1
            previous = measured_nn
        previous_peak = peak
    if not differences:
        raise ValueError("HRV window contains too few complete beats")
    return 1000 * math.sqrt(squared / differences)


def crew_values(
    group: str,
    t: float,
    profile: AstronautProfile,
    seed: int,
) -> dict[str, float | bool]:
    """Produce one physical acquisition group in conventional source units."""
    a = activity(t)
    h = hydration(t)
    hour = t % DAY / 3600
    n = noise(t, seed, profile.id, group)
    match group:
        case "heart":
            if t < 60:
                raise ValueError("HR needs a completed 60-second window")
            return {
                "heart_rate": sum(
                    heart_rate(t - 60 + (i + 0.5) * 5, profile, seed) for i in range(12)
                )
                / 12
            }
        case "hrv":
            return {"hrv_rmssd": rmssd(t, profile, seed)}
        case "bp":
            return {
                "bp_systolic": profile.sbp_mmhg + 18 * a + 1.2 * n,
                "bp_diastolic": profile.dbp_mmhg + 3 * a + 0.8 * n,
            }
        case "spo2":
            return {"spo2": 98.1 - 0.25 * a + 0.25 * n}
        case "temperature":
            # Thermal response trails the work bout; the method estimates core,
            # not the much more variable patch skin temperature.
            lagged = activity(t - 600)
            return {
                "body_temperature": 36.85
                + 0.18 * math.sin(2 * math.pi * (t / DAY - 0.35))
                + 0.25 * lagged
                + 0.025 * n
            }
        case "respiration":
            if t < 60:
                raise ValueError("Respiratory rate needs a completed 60-second window")
            return {
                "respiratory_rate": sum(
                    14
                    + 9 * activity(t - 60 + (i + 0.5) * 5)
                    + 0.35 * noise(t - 60 + (i + 0.5) * 5, seed, profile.id, group)
                    for i in range(12)
                )
                / 12
            }
        case "glucose":
            if t < 300:
                raise ValueError("CGM estimate needs its completed 5-minute sensor window")
            raw = []
            for i in range(60):
                sample = t - 300 + (i + 1) * 5
                sample_hour = sample % DAY / 3600
                meals = sum(
                    1.45 * math.exp(-(((sample_hour - meal - 0.65) / 0.65) ** 2))
                    for meal in (8, 13, 19)
                )
                raw.append(
                    5.1
                    + meals
                    - 0.12 * activity(sample)
                    + 0.06 * noise(sample, seed, profile.id, group)
                )
            return {"glucose": sum(raw) / len(raw)}
        case "cortisol":
            since_waking = (hour - 7) % 24
            return {
                "cortisol_saliva": 1.2
                + 9 * math.exp(-since_waking / 5)
                + 3 * math.exp(-(((since_waking - 0.5) / 0.4) ** 2))
                + 0.05 * n
            }
        case "troponin":
            return {"troponin_i": 3.5 + 0.3 * n}
        case "lactate":
            return {"lactate": 1.0 + 1.7 * a + 0.04 * n}
        case "vitamin":
            return {
                "vitamin_d_25oh": profile.vitamin_d_ng_ml
                + 0.7 * math.sin(2 * math.pi * t / (DAY * 90))
            }
        case "il6":
            return {"il6_serum": 1.4 + 0.7 * activity(t - 1200) + 0.1 * n}
        case "mass":
            return {"body_mass": profile.mass_kg * (1 - h / 100)}
        case "usg":
            return {"urine_specific_gravity": 1.015 + 0.002 * h}
        case "urine" | "ntx":
            if t < DAY:
                raise ValueError("urine results need a complete collection")
            # Integrate the modeled urine flow, including the same hydration driver
            # used by mass and USG. Fixed quadrature is temporary calculation, not
            # saved telemetry. Five-minute resolution is ample for these slow curves.
            steps = 288
            width = DAY / steps
            volume = sum(
                (
                    2.7
                    + 0.1 * math.sin(2 * math.pi * (t - DAY + (i + 0.5) * width) / (7 * DAY))
                    - 0.5 * hydration(t - DAY + (i + 0.5) * width)
                )
                / steps
                for i in range(steps)
            )
            ntx = profile.ntx_baseline * (1 + 0.03 * math.sin(2 * math.pi * t / (60 * DAY)))
            return {
                "urinary_ntx": ntx,
                "bone_ntx_pct_baseline": 100 * (ntx / profile.ntx_baseline - 1),
                "urine_volume_24h": volume,
                "urine_specific_gravity": 1.015 + 0.002 * h,
            }
        case "sweat":
            # Raw local flow and concentration at 1Hz only while active and wet.
            if t < 1 or min(activity(t), activity(t - 1)) < 0.05:
                return {}
            flow = (0.02 + 0.8 * a) / 1800
            concentration = 42 + 4 * a + noise(t, seed, profile.id, "sweat")
            return {"sweat_rate": flow, "sweat_sodium_concentration": concentration}
        case "sweat_summary":
            if t < 60 or min(activity(t), activity(t - 60)) < 0.05:
                return {}
            # Replay the latent 1Hz sensor window without retaining raw telemetry.
            # Mean mmol/h is integrated sodium amount over the window / elapsed hours.
            losses = []
            for i in range(60):
                sample = t - 60 + i + 1
                flow = (0.02 + 0.8 * activity(sample)) / 1800
                sodium = 42 + 4 * activity(sample) + noise(sample, seed, profile.id, "sweat")
                losses.append(flow * sodium)
            return {"sweat_sodium_flux": sum(losses) / 60}
        case "saliva_pcr":
            return {"viral_ebv_detected": False, "viral_vzv_detected": False}
        case "urine_pcr":
            return {"viral_cmv_detected": False}
        case _:
            raise ValueError(f"unknown crew acquisition group: {group}")


def environment_values(
    group: str, t: float, environment: Environment, seed: int
) -> dict[str, float | bool]:
    """Compartment telemetry depends on compartment time and configuration, never crew count."""
    match group:
        case "co2":
            return {
                "ambient_ppco2": 250
                + 25 * math.sin(2 * math.pi * t / DAY)
                + 4 * noise(t, seed, environment.id, "co2")
            }
        case "light":
            # Smooth lighting transitions are configured routine inputs, not sleep inference.
            hour = t % DAY / 3600
            daylight = 0.5 * (math.tanh((hour - 7) * 3) - math.tanh((hour - 22) * 3))
            return {"ambient_light_lux": 0.5 + 349.5 * daylight}
        case "radiation" | "radiation_dose":
            # Exact analytic integration avoids history and avoids summing noisy
            # measurements. It remains correct when intermediate polls are skipped.
            omega = 2 * math.pi / 5400
            base = environment.dose_rate_usv_h
            rate = base * (1 + 0.12 * math.sin(omega * t))
            dose = (
                environment.initial_monitor_dose_msv
                + base * (t + 0.12 * (1 - math.cos(omega * t)) / omega) / 3_600_000
            )
            return {"ambient_dose_rate": rate, "ambient_integrated_dose": dose}
        case "spe":
            return {"spe_flag": False}
        case _:
            raise ValueError(f"unknown environment acquisition group: {group}")
