from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

from plant.interface import ControlCommand


class CyberAttackKind(StrEnum):
    UNAUTHORIZED_COMMAND = "unauthorized_command"
    SENSOR_SPOOFING = "sensor_spoofing"
    REPLAY = "replay"
    FALSE_DATA_INJECTION = "false_data_injection"
    GRADUAL_MANIPULATION = "gradual_manipulation"


@dataclass(frozen=True)
class CyberAttackProfile:
    """Deterministic cyberattack scenario for repeatable twin experiments."""

    kind: CyberAttackKind
    start_time_s: float
    magnitude: float = 0.0
    duration_s: float = 60.0

    def active(self, time_s: float) -> bool:
        return self.start_time_s <= time_s < self.start_time_s + self.duration_s

    def progress(self, time_s: float) -> float:
        if not self.active(time_s):
            return 0.0
        return min(1.0, max(0.0, (time_s - self.start_time_s) / self.duration_s))


def attack_command(
    command: ControlCommand,
    profile: CyberAttackProfile,
    time_s: float,
) -> ControlCommand:
    """Apply command-path attacks; the transport policy must still validate it."""
    if not profile.active(time_s):
        return command

    if profile.kind is CyberAttackKind.UNAUTHORIZED_COMMAND:
        return replace(
            command,
            requested_speed_pu=min(1.0, max(0.0, command.requested_speed_pu + profile.magnitude)),
            source="attacker",
            command_id=f"unauthorized-{command.command_id or time_s}",
        )

    if profile.kind in {
        CyberAttackKind.FALSE_DATA_INJECTION,
        CyberAttackKind.GRADUAL_MANIPULATION,
    }:
        factor = profile.magnitude * (
            profile.progress(time_s)
            if profile.kind is CyberAttackKind.GRADUAL_MANIPULATION
            else 1.0
        )
        return replace(
            command,
            load_torque_pu=min(1.0, max(0.0, command.load_torque_pu + factor)),
            metadata={**command.metadata, "cyber_attack": profile.kind.value},
        )

    return command


def attack_measurement(
    measurement: dict[str, float],
    profile: CyberAttackProfile,
    time_s: float,
    replay_measurement: dict[str, float] | None = None,
) -> dict[str, float]:
    """Apply telemetry-path attacks to an observation copy, never FMU truth."""
    if not profile.active(time_s):
        return dict(measurement)
    if profile.kind is CyberAttackKind.REPLAY and replay_measurement is not None:
        return dict(replay_measurement)

    result: dict[str, Any] = dict(measurement)
    if profile.kind is CyberAttackKind.SENSOR_SPOOFING:
        result["T_sensor_C"] = float(result["T_sensor_C"]) + profile.magnitude
    elif profile.kind in {
        CyberAttackKind.FALSE_DATA_INJECTION,
        CyberAttackKind.GRADUAL_MANIPULATION,
    }:
        factor = profile.magnitude * (
            profile.progress(time_s)
            if profile.kind is CyberAttackKind.GRADUAL_MANIPULATION
            else 1.0
        )
        result["speed_rpm"] = max(0.0, float(result["speed_rpm"]) + factor)
        result["omega_rad_s"] = float(result["speed_rpm"]) * 2.0 * 3.141592653589793 / 60.0
    return {key: float(value) for key, value in result.items()}