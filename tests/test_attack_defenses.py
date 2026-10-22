import pytest

from communication.interface import PlantCommunication
from communication.security import (
    CommandSecurityError,
    CommandSecurityPolicy,
    StateSecurityPolicy,
    sign_command,
)
from cybersecurity.attack_simulator import AttackSimulator
from plant.interface import ControlCommand, PlantInterface, PlantState


class FakePlant(PlantInterface):
    def __init__(self):
        self.state = PlantState(1.0, 1460.0, 50.0, 10.0, 400.0, 6000.0, 35.0)
        self.command = None

    def start(self): return self.state
    def stop(self): pass
    def reset(self): pass
    def read_state(self): return self.state
    def send_command(self, command): self.command = command
    def step(self, step_s): return self.state


def test_command_injection_and_replay_are_blocked_at_transport():
    transport = PlantCommunication(FakePlant())
    command = ControlCommand(timestamp_s=1.0, command_id="cmd-1")

    with pytest.raises(CommandSecurityError, match="untrusted"):
        transport.send_command(AttackSimulator.command_injection(command))

    transport.send_command(command)
    with pytest.raises(CommandSecurityError, match="replayed"):
        transport.send_command(AttackSimulator.replay(command))

        with pytest.raises(CommandSecurityError, match="duplicate timestamp"):
            transport.send_command(ControlCommand(timestamp_s=1.0))


def test_signed_commands_detect_mitm_tampering():
    key = b"test-only-motor-key"
    policy = CommandSecurityPolicy(signing_key=key, require_signature=True)
    original = ControlCommand(timestamp_s=1.0, command_id="cmd-1")
    signed = ControlCommand(**{**original.__dict__, "signature": sign_command(original, key)})
    policy.validate(signed)

    tampered = AttackSimulator.mitm_tamper(signed, 0.0)
    with pytest.raises(CommandSecurityError, match="signature"):
        CommandSecurityPolicy(signing_key=key, require_signature=True).validate(tampered)


def test_sensor_spoofing_and_stale_telemetry_are_blocked():
    state_policy = StateSecurityPolicy()
    state = PlantCommunication(FakePlant()).read_state()

    with pytest.raises(CommandSecurityError, match="temperature"):
        state_policy.validate(AttackSimulator.sensor_spoof(state, 500.0))

    state_policy.validate(state)
    with pytest.raises(CommandSecurityError, match="stale"):
        state_policy.validate(AttackSimulator.stale_telemetry(state, 0.5))