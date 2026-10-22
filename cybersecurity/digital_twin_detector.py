from __future__ import annotations

import math
from dataclasses import dataclass

from plant.interface import ControlCommand
from twin.state_estimator import StateEstimate


@dataclass(frozen=True)
class CyberPhysicalEvidence:
    network_score: float
    twin_score: float
    combined_score: float
    network_alert: bool
    twin_alert: bool
    combined_alert: bool
    speed_residual_pu: float
    temperature_residual_C: float
    reason: str


class CyberPhysicalDetector:
    """Compare reported behavior with command/network and twin expectations."""

    def __init__(self, alert_threshold: float = 0.70) -> None:
        self.alert_threshold = float(alert_threshold)

    @staticmethod
    def _clip(value: float) -> float:
        return min(1.0, max(0.0, float(value)))

    def evaluate(
        self,
        *,
        measurement: dict[str, float],
        estimate: StateEstimate,
        command: ControlCommand,
        rated_speed_rpm: float,
        network_anomaly_score: float = 0.0,
    ) -> CyberPhysicalEvidence:
        expected_speed_rpm = rated_speed_rpm * command.requested_speed_pu
        speed_residual_pu = abs(
            float(measurement["speed_rpm"]) - expected_speed_rpm
        ) / max(rated_speed_rpm, 1e-9)
        temperature_residual_C = abs(
            float(measurement["T_sensor_C"]) - estimate.estimated_winding_C
        )
        frame_residual_C = abs(float(estimate.frame_innovation_C))

        speed_score = self._clip(speed_residual_pu / 0.10)
        sensor_score = self._clip(temperature_residual_C / 10.0)
        frame_score = self._clip(frame_residual_C / 5.0)
        twin_score = max(speed_score, sensor_score, frame_score)
        network_score = self._clip(network_anomaly_score)
        combined_score = max(twin_score, network_score)

        reasons = []
        if speed_score >= self.alert_threshold:
            reasons.append("speed-command inconsistency")
        if sensor_score >= self.alert_threshold:
            reasons.append("temperature-observer inconsistency")
        if frame_score >= self.alert_threshold:
            reasons.append("frame-model inconsistency")
        if network_score >= self.alert_threshold:
            reasons.append("network anomaly")

        return CyberPhysicalEvidence(
            network_score=network_score,
            twin_score=twin_score,
            combined_score=combined_score,
            network_alert=network_score >= self.alert_threshold,
            twin_alert=twin_score >= self.alert_threshold,
            combined_alert=combined_score >= self.alert_threshold,
            speed_residual_pu=speed_residual_pu,
            temperature_residual_C=temperature_residual_C,
            reason="; ".join(reasons) if reasons else "consistent",
        )


def network_command_score(
    command: ControlCommand,
    *,
    trusted_sources: frozenset[str] = frozenset({"controller", "operator", "safety_controller"}),
) -> float:
    """Small rule-based baseline used to compare network-only detection."""
    if command.source not in trusted_sources:
        return 1.0
    if not all(
        math.isfinite(float(value))
        for value in (
            command.requested_speed_pu,
            command.load_torque_pu,
            command.cooling_flow_pu,
        )
    ):
        return 1.0
    if not 0.0 <= command.requested_speed_pu <= 1.0:
        return 1.0
    if not 0.0 <= command.load_torque_pu <= 1.0:
        return 1.0
    if not 0.0 <= command.cooling_flow_pu <= 1.0:
        return 1.0
    return 0.0