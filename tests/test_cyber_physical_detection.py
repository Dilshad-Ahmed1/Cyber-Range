from cybersecurity.cyber_attacks import (
    CyberAttackKind,
    CyberAttackProfile,
    attack_command,
    attack_measurement,
)
from cybersecurity.digital_twin_detector import (
    CyberPhysicalDetector,
    network_command_score,
)
from plant.interface import ControlCommand
from twin.state_estimator import StateEstimate


def _estimate() -> StateEstimate:
    return StateEstimate(50.0, 45.0, 0.1, 0.0, 0.0, 0.0)


def _measurement() -> dict[str, float]:
    return {
        "T_sensor_C": 50.0,
        "T_frame_C": 45.0,
        "speed_rpm": 1460.0,
        "omega_rad_s": 153.0,
    }


def test_gradual_attack_is_deterministic_and_increases():
    profile = CyberAttackProfile(
        CyberAttackKind.GRADUAL_MANIPULATION, start_time_s=10.0, magnitude=0.20, duration_s=10.0
    )
    command = ControlCommand(timestamp_s=10.0, load_torque_pu=0.5)

    early = attack_command(command, profile, 11.0)
    late = attack_command(command, profile, 19.0)

    assert early.load_torque_pu < late.load_torque_pu
    assert late.load_torque_pu == 0.68


def test_twin_detector_catches_false_speed_data_when_network_rules_do_not():
    command = ControlCommand(requested_speed_pu=1.0)
    measurement = attack_measurement(
        _measurement(),
        CyberAttackProfile(CyberAttackKind.FALSE_DATA_INJECTION, 0.0, magnitude=300.0),
        1.0,
    )
    evidence = CyberPhysicalDetector().evaluate(
        measurement=measurement,
        estimate=_estimate(),
        command=command,
        rated_speed_rpm=1460.0,
        network_anomaly_score=network_command_score(command),
    )

    assert evidence.network_alert is False
    assert evidence.twin_alert is True
    assert evidence.reason == "speed-command inconsistency"


def test_sensor_spoofing_creates_twin_residual():
    measurement = attack_measurement(
        _measurement(),
        CyberAttackProfile(CyberAttackKind.SENSOR_SPOOFING, 0.0, magnitude=10.0),
        1.0,
    )
    evidence = CyberPhysicalDetector().evaluate(
        measurement=measurement,
        estimate=_estimate(),
        command=ControlCommand(),
        rated_speed_rpm=1460.0,
    )

    assert evidence.twin_alert is True
    assert evidence.temperature_residual_C == 10.0