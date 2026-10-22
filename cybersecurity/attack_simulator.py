from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from plant.interface import ControlCommand, PlantState


class AttackKind(StrEnum):
    COMMAND_INJECTION = "command_injection"
    REPLAY = "replay"
    MITM_COMMAND_TAMPERING = "mitm_command_tampering"
    SENSOR_SPOOFING = "sensor_spoofing"
    STALE_TELEMETRY = "stale_telemetry"
    DOS_FLOOD = "dos_flood"
    UNSAFE_AAS_WRITE = "unsafe_aas_write"
    PHYSICAL_FAULT_MASQUERADE = "physical_fault_masquerade"
    CREDENTIAL_ENDPOINT_REDIRECT = "credential_endpoint_redirect"
    NON_FINITE_PAYLOAD = "non_finite_payload"


@dataclass(frozen=True)
class AttackDefinition:
    kind: AttackKind
    target: str
    prevention: str
    detection: str


ATTACK_CATALOG = (
    AttackDefinition(AttackKind.COMMAND_INJECTION, "actuator command", "source allowlist and actuator bounds", "rejected command audit"),
    AttackDefinition(AttackKind.REPLAY, "command or telemetry frame", "monotonic timestamps and unique IDs", "freshness failure"),
    AttackDefinition(AttackKind.MITM_COMMAND_TAMPERING, "command frame", "HMAC-SHA256 command signature", "signature failure"),
    AttackDefinition(AttackKind.SENSOR_SPOOFING, "motor telemetry", "state plausibility validation and model residuals", "fault detector residual"),
    AttackDefinition(AttackKind.STALE_TELEMETRY, "sensor stream", "monotonic telemetry timestamps", "stale telemetry alarm"),
    AttackDefinition(AttackKind.DOS_FLOOD, "control transport", "duplicate-cycle rejection and deadline monitoring", "deadline/failure metrics"),
    AttackDefinition(AttackKind.UNSAFE_AAS_WRITE, "digital-twin properties", "AAS schema allowlist and finite values", "write rejection"),
    AttackDefinition(AttackKind.PHYSICAL_FAULT_MASQUERADE, "thermal/mechanical state", "independent state estimation and conservative derating", "persistent residual diagnosis"),
    AttackDefinition(AttackKind.CREDENTIAL_ENDPOINT_REDIRECT, "BaSyx endpoint", "HTTPS validation, host allowlist, bearer auth", "endpoint validation failure"),
    AttackDefinition(AttackKind.NON_FINITE_PAYLOAD, "commands/telemetry", "finite-number validation", "payload rejection"),
)


class AttackSimulator:
    """Create hostile test inputs without changing the plant implementation."""

    @staticmethod
    def command_injection(command: ControlCommand) -> ControlCommand:
        return ControlCommand(
            **{**command.__dict__, "source": "attacker", "command_id": "injected"}
        )

    @staticmethod
    def replay(command: ControlCommand) -> ControlCommand:
        return command

    @staticmethod
    def mitm_tamper(command: ControlCommand, load_torque_pu: float) -> ControlCommand:
        return ControlCommand(
            **{**command.__dict__, "load_torque_pu": load_torque_pu}
        )

    @staticmethod
    def sensor_spoof(state: PlantState, temperature_C: float) -> PlantState:
        return PlantState(**{**state.__dict__, "temperature_C": temperature_C})

    @staticmethod
    def stale_telemetry(state: PlantState, timestamp_s: float) -> PlantState:
        return PlantState(**{**state.__dict__, "timestamp_s": timestamp_s})