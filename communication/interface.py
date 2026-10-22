from __future__ import annotations

from abc import ABC, abstractmethod

from communication.security import CommandSecurityPolicy, StateSecurityPolicy
from plant.interface import ControlCommand, PlantInterface, PlantState


class CommunicationInterface(ABC):
    """Replaceable controller-to-device transport boundary."""

    @abstractmethod
    def read_state(self) -> PlantState:
        raise NotImplementedError

    @abstractmethod
    def send_command(self, command: ControlCommand) -> None:
        raise NotImplementedError

    @abstractmethod
    def step(self, step_s: float) -> PlantState:
        raise NotImplementedError


class PlantCommunication(CommunicationInterface):
    """Internal transport used by the current simulation."""

    def __init__(
        self,
        plant: PlantInterface,
        security_policy: CommandSecurityPolicy | None = None,
        state_security_policy: StateSecurityPolicy | None = None,
    ) -> None:
        self.plant = plant
        self.security_policy = security_policy or CommandSecurityPolicy()
        self.state_security_policy = state_security_policy or StateSecurityPolicy()

    def read_state(self) -> PlantState:
        state = self.plant.read_state()
        self.state_security_policy.validate(state)
        return state

    def send_command(self, command: ControlCommand) -> None:
        self.security_policy.validate(command)
        self.plant.send_command(command)

    def step(self, step_s: float) -> PlantState:
        state = self.plant.step(step_s)
        self.state_security_policy.validate(state)
        return state