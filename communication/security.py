from __future__ import annotations

import math
import hashlib
import hmac
import json
from dataclasses import dataclass, field

from plant.interface import ControlCommand, PlantState


class CommandSecurityError(ValueError):
    """Raised when a command violates the plant command security policy."""


@dataclass
class CommandSecurityPolicy:
    """Validate commands before they cross the controller/device boundary."""

    allowed_sources: frozenset[str] = frozenset(
        {"controller", "operator", "safety_controller"}
    )
    max_speed_pu: float = 1.0
    max_load_pu: float = 1.0
    max_cooling_pu: float = 1.0
    timestamp_tolerance_s: float = 1e-9
    signing_key: bytes | None = None
    require_signature: bool = False
    _last_timestamp_s: float | None = field(default=None, init=False)
    _seen_command_ids: set[str] = field(default_factory=set, init=False)

    def validate(self, command: ControlCommand) -> None:
        if not isinstance(command, ControlCommand):
            raise CommandSecurityError("command must be a ControlCommand")

        numeric_values = {
            "timestamp_s": command.timestamp_s,
            "requested_speed_pu": command.requested_speed_pu,
            "load_torque_pu": command.load_torque_pu,
            "cooling_flow_pu": command.cooling_flow_pu,
        }
        if any(
            not isinstance(value, (int, float)) or not math.isfinite(float(value))
            for value in numeric_values.values()
        ):
            raise CommandSecurityError("command contains a non-finite value")

        if command.timestamp_s < 0.0:
            raise CommandSecurityError("command timestamp cannot be negative")
        if (
            self._last_timestamp_s is not None
            and command.timestamp_s + self.timestamp_tolerance_s
            < self._last_timestamp_s
        ):
            raise CommandSecurityError("stale command timestamp rejected")

        if command.source not in self.allowed_sources:
            raise CommandSecurityError(f"untrusted command source: {command.source!r}")

        if self.require_signature and self.signing_key is None:
            raise CommandSecurityError("signature verification is not configured")
        if self.signing_key is not None and not verify_command_signature(
            command, self.signing_key
        ):
            raise CommandSecurityError("invalid command signature")

        ranges = {
            "requested_speed_pu": (0.0, self.max_speed_pu),
            "load_torque_pu": (0.0, self.max_load_pu),
            "cooling_flow_pu": (0.0, self.max_cooling_pu),
        }
        for name, (lower, upper) in ranges.items():
            value = float(getattr(command, name))
            if not lower <= value <= upper:
                raise CommandSecurityError(
                    f"{name}={value} outside [{lower}, {upper}]"
                )

        if len(command.metadata) > 16:
            raise CommandSecurityError("command metadata contains too many fields")
        for key, value in command.metadata.items():
            if (
                not isinstance(key, str)
                or len(key) > 64
                or not isinstance(value, (str, int, float, bool, type(None)))
                or isinstance(value, float) and not math.isfinite(value)
            ):
                raise CommandSecurityError("command metadata contains an unsafe value")

        command_id = command.command_id.strip()
        if len(command_id) > 128:
            raise CommandSecurityError("command ID is too long")
        if command_id and command_id in self._seen_command_ids:
            raise CommandSecurityError("replayed command rejected")
            if (
                self._last_timestamp_s is not None
                and abs(command.timestamp_s - self._last_timestamp_s)
                <= self.timestamp_tolerance_s
            ):
                raise CommandSecurityError("duplicate command timestamp rejected")

        self._last_timestamp_s = max(
            command.timestamp_s,
            self._last_timestamp_s if self._last_timestamp_s is not None else command.timestamp_s,
        )
        if command_id:
            self._seen_command_ids.add(command_id)


def safe_stop_command(timestamp_s: float) -> ControlCommand:
    """Return a bounded command for fail-safe handling by callers."""
    return ControlCommand(
        timestamp_s=max(0.0, float(timestamp_s)),
        requested_speed_pu=0.0,
        load_torque_pu=0.0,
        cooling_flow_pu=1.0,
        command_id="safety-stop",
        source="safety_controller",
    )


def _command_payload(command: ControlCommand) -> bytes:
    return json.dumps(
        {
            "timestamp_s": float(command.timestamp_s),
            "requested_speed_pu": float(command.requested_speed_pu),
            "load_torque_pu": float(command.load_torque_pu),
            "cooling_flow_pu": float(command.cooling_flow_pu),
            "command_id": command.command_id,
            "source": command.source,
            "metadata": command.metadata,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sign_command(command: ControlCommand, signing_key: bytes) -> str:
    """Create an HMAC-SHA256 signature for a command's immutable fields."""
    return hmac.new(signing_key, _command_payload(command), hashlib.sha256).hexdigest()


def verify_command_signature(command: ControlCommand, signing_key: bytes) -> bool:
    expected = sign_command(command, signing_key)
    return hmac.compare_digest(expected, command.signature)


@dataclass
class StateSecurityPolicy:
    """Reject implausible, non-finite, or replayed motor telemetry."""

    maximum_temperature_C: float = 250.0
    maximum_speed_rpm: float = 5000.0
    maximum_current_A: float = 1000.0
    maximum_voltage_V: float = 1000.0
    _last_timestamp_s: float | None = field(default=None, init=False)

    def validate(self, state: PlantState) -> None:
        values = {
            "timestamp_s": state.timestamp_s,
            "speed_rpm": state.speed_rpm,
            "temperature_C": state.temperature_C,
            "current_A": state.current_A,
            "voltage_V": state.voltage_V,
            "electrical_power_W": state.electrical_power_W,
            "load_torque_Nm": state.load_torque_Nm,
        }
        optional_values = {
            "vibration_mm_s": state.vibration_mm_s,
            "frame_temperature_C": state.frame_temperature_C,
            "shaft_power_W": state.shaft_power_W,
            "motor_torque_Nm": state.motor_torque_Nm,
            "thermal_margin_C": state.thermal_margin_C,
        }
        for name, value in {**values, **optional_values}.items():
            if value is not None and not math.isfinite(float(value)):
                raise CommandSecurityError(f"non-finite telemetry: {name}")
        if state.timestamp_s < 0.0 or (
            self._last_timestamp_s is not None
            and state.timestamp_s < self._last_timestamp_s
        ):
            raise CommandSecurityError("stale telemetry rejected")
        if not 0.0 <= state.speed_rpm <= self.maximum_speed_rpm:
            raise CommandSecurityError("implausible speed telemetry")
        if not -40.0 <= state.temperature_C <= self.maximum_temperature_C:
            raise CommandSecurityError("implausible temperature telemetry")
        if not 0.0 <= state.current_A <= self.maximum_current_A:
            raise CommandSecurityError("implausible current telemetry")
        if not 0.0 <= state.voltage_V <= self.maximum_voltage_V:
            raise CommandSecurityError("implausible voltage telemetry")
        self._last_timestamp_s = state.timestamp_s