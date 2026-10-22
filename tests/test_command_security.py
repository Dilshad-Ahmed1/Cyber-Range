import pytest
from pathlib import Path

from communication.security import CommandSecurityError, CommandSecurityPolicy
from integration.basyx_bridge import BaSyxBridge
from plant.interface import ControlCommand


def test_policy_rejects_out_of_range_motor_command():
    policy = CommandSecurityPolicy()

    with pytest.raises(CommandSecurityError, match="load_torque_pu"):
        policy.validate(ControlCommand(load_torque_pu=4.0))


def test_policy_rejects_replayed_command_id():
    policy = CommandSecurityPolicy()
    command = ControlCommand(timestamp_s=1.0, command_id="cmd-1")

    policy.validate(command)
    with pytest.raises(CommandSecurityError, match="replayed"):
        policy.validate(command)


def test_policy_rejects_untrusted_source_and_stale_timestamp():
    policy = CommandSecurityPolicy()

    with pytest.raises(CommandSecurityError, match="untrusted"):
        policy.validate(ControlCommand(source="attacker"))

    policy.validate(ControlCommand(timestamp_s=2.0))
    with pytest.raises(CommandSecurityError, match="stale"):
        policy.validate(ControlCommand(timestamp_s=1.0))


def test_policy_rejects_non_finite_metadata():
    policy = CommandSecurityPolicy()

    with pytest.raises(CommandSecurityError, match="unsafe"):
        policy.validate(ControlCommand(metadata={"operator_note": float("nan")}))


def test_basyx_rejects_unsafe_endpoint_and_unknown_property():
    config_path = Path(__file__).parents[1] / "config" / "motor_aas_definition.json"

    with pytest.raises(ValueError, match="absolute http"):
        BaSyxBridge(host="file:///tmp/aas", config_path=config_path)

    bridge = BaSyxBridge(
        host="http://localhost:8081",
        config_path=config_path,
        allowed_hosts={"localhost"},
    )
    try:
        with pytest.raises(KeyError, match="Unknown project properties"):
            bridge.update_submodel("OperationalState", {"InjectedProperty": 1.0})
    finally:
        bridge.close()