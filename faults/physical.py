from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PhysicalFaultProfile:
    """Physical degradation applied to the simulated plant only."""

    sensor_bias_C: float = 0.0
    sensor_freeze: bool = False
    cooling_efficiency: float = 1.0
    rth_degradation: float = 1.0
    unbalance_severity: float = 0.0
    truth_severity: float = 0.0


SCENARIOS: dict[str, PhysicalFaultProfile] = {
    "healthy": PhysicalFaultProfile(),
    "sensor_bias": PhysicalFaultProfile(sensor_bias_C=10.0, truth_severity=1.0),
    "sensor_freeze": PhysicalFaultProfile(sensor_freeze=True, truth_severity=1.0),
    "cooling": PhysicalFaultProfile(cooling_efficiency=0.40, truth_severity=0.60),
    "rth_degradation": PhysicalFaultProfile(rth_degradation=2.0, truth_severity=0.50),
    "unbalance": PhysicalFaultProfile(unbalance_severity=0.75, truth_severity=0.75),
    "combined": PhysicalFaultProfile(
        sensor_bias_C=10.0,
        cooling_efficiency=0.40,
        unbalance_severity=0.75,
        truth_severity=1.0,
    ),
}


def fault_inputs_at(profile: PhysicalFaultProfile, active: bool) -> dict[str, Any]:
    """Translate a physical profile into plant-only FMU fault inputs."""
    if not active:
        return {
            "f_sensor_bias_C": 0.0,
            "f_sensor_freeze": False,
            "f_cooling_eff": 1.0,
            "f_rth_degradation": 1.0,
            "f_unbalance_severity": 0.0,
        }
    return {
        "f_sensor_bias_C": profile.sensor_bias_C,
        "f_sensor_freeze": profile.sensor_freeze,
        "f_cooling_eff": profile.cooling_efficiency,
        "f_rth_degradation": profile.rth_degradation,
        "f_unbalance_severity": profile.unbalance_severity,
    }