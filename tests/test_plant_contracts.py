from communication.simulated import SimulatedCommunication
from plant.interface import ControlCommand, PlantInterface, PlantState


class FakePlant(PlantInterface):
    def __init__(self):
        self.state = PlantState(
            timestamp_s=0.0,
            speed_rpm=1460.0,
            temperature_C=45.0,
            current_A=10.0,
            voltage_V=400.0,
            electrical_power_W=6000.0,
            load_torque_Nm=35.0,
        )
        self.last_command = None

    def start(self):
        return self.state

    def stop(self):
        return None

    def reset(self):
        return None

    def read_state(self):
        return self.state

    def send_command(self, command):
        self.last_command = command

    def step(self, step_s):
        return self.state


def test_state_model_contains_observations_only():
    state = PlantState(
        timestamp_s=1.0,
        speed_rpm=1460.0,
        temperature_C=50.0,
        current_A=10.0,
        voltage_V=400.0,
        electrical_power_W=6000.0,
        load_torque_Nm=35.0,
    )

    measurement = state.as_measurement()

    assert measurement["T_sensor_C"] == 50.0
    assert "f_sensor_bias_C" not in measurement
    assert "T_winding_C" not in measurement


def test_simulated_transport_delegates_to_any_plant():
    plant = FakePlant()
    transport = SimulatedCommunication(plant)
    command = ControlCommand(load_torque_pu=0.8, command_id="test-1")

    transport.send_command(command)

    assert plant.last_command is command
    assert transport.read_state().speed_rpm == 1460.0