# Cyber-Resilient Industrial Motor Control Foundation

This repository is the simulation foundation for the future project
"Cyber-Resilient Industrial Motor Control Using a Physics-Informed Digital
Twin".

The project focuses on the industrial motor digital twin and its simulation
infrastructure. It includes repeatable cyberattack profiles, command and
telemetry defenses, and physics-informed cyber-physical detection. A concrete
Modbus/PLC transport and a trained ML detector remain future integration work.

The runtime now includes a defensive control boundary: commands are rejected
when they contain non-finite or out-of-range actuator values, come from an
untrusted source, move backward in time, or reuse a command ID. BaSyx
synchronization also validates HTTP(S) endpoints, supports bearer
authentication and host allowlisting, rejects non-finite telemetry, and
rejects properties outside the checked AAS schema. These controls prevent
common command injection, replay, endpoint redirection, and telemetry
poisoning attempts; production deployments still need TLS, network
segmentation, secret management, and authenticated PLC/VFD protocols.

## Motor cyberattack matrix

The attack catalog is implemented in `cybersecurity/attack_simulator.py` and
the protections are enforced at the shared communication boundary. The same
boundary can wrap `SimulatedCommunication` for FMU testing or a concrete
`HardwarePlant` adapter for a physical motor.

| Attack | Target | Implemented prevention/detection |
|---|---|---|
| Command injection | Speed, load, cooling command | Source allowlist, finite values, actuator bounds |
| Replay | Commands or telemetry | Unique command IDs and monotonic timestamps |
| MITM command tampering | Command frame | Optional HMAC-SHA256 signatures |
| Sensor spoofing | Temperature, speed, current, voltage | State plausibility limits plus estimator residuals |
| Stale telemetry | Sensor stream | Timestamp freshness validation |
| DoS/control flooding | Command transport | Duplicate-cycle rejection and deadline metrics |
| Unsafe AAS write | Digital-twin properties | Schema allowlist and finite-value validation |
| Physical-fault masquerade | Thermal/mechanical condition | Independent state estimation, persistence, and derating |
| Endpoint redirection | BaSyx connection | HTTP(S) validation, credentials rejection, host allowlist |
| Non-finite payload | Commands/telemetry/AAS | Rejects `NaN` and infinity |

Attack-defense tests are in `tests/test_attack_defenses.py`. HMAC protection
is enabled for a deployment by constructing the policy with a secret key and
`require_signature=True`; the key must come from a deployment secret store,
not source code. For a physical motor, use the same policy when constructing
`PlantCommunication(hardware_plant, security_policy=..., state_security_policy=...)`
before sending any PLC/VFD command.

## Cyber-physical research experiment layer

`cybersecurity/cyber_attacks.py` provides repeatable profiles for:

- unauthorized command manipulation;
- temperature/sensor spoofing;
- replayed observations;
- false-data injection; and
- gradual stealth manipulation.

`cybersecurity/digital_twin_detector.py` keeps the comparison baselines
separate:

1. `network_command_score()` represents network/rule-only detection.
2. `CyberPhysicalDetector` scores speed-command, temperature-observer, and
	frame-model residuals from the digital twin.
3. `combined_score` combines network and physics evidence for the final alert.

This separation supports the proposed comparison of normal operation,
physical faults, sensor spoofing, command manipulation, replay, and gradual
attacks using detection latency, false alarms, physical deviation, and attack
impact. The attack profiles modify observation copies or controller command
copies; FMU truth remains private and is never used by the detector.

The current physical adapter is intentionally still a boundary: the same
detector and `PlantCommunication` security wrapper can be connected to a PLC
or VFD implementation, but no real hardware transport is assumed or opened
by this repository.

## What the project does

The project simulates a WEG W22 IE3 5.5 kW motor using a reduced-order
electro-thermal-mechanical Modelica model exported as an FMI 2.0
Co-Simulation FMU. Python runs the closed loop around the FMU and provides:

- baseline, adaptive, and constrained adaptive controllers;
- model-based thermal state estimation;
- 30-second and 60-second thermal prediction;
- physical-fault diagnostics and severity estimation;
- optional BaSyx Asset Administration Shell synchronization;
- experiment metrics, CSV result files, plots, and a Streamlit UI.

The motor model is a calibrated research model, not a full electromagnetic
induction-motor or rotor-dynamics model. Manufacturer values are used for
reference operating points; thermal RC parameters, friction, and partial-load
loss scaling are model assumptions.

## Environment setup

Use the project virtual environment on Windows. Prefer its Python executable
explicitly so commands do not accidentally use another Python installation.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
\.venv\Scripts\python.exe -m pip install --upgrade pip
\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Required software:

- Python 3.12 or a compatible version;
- OpenModelica for checking/exporting the FMU;
- Docker Desktop only if BaSyx integration is needed.

## Project architecture

The important runtime boundary is:

```text
Controller / digital twin
					|
					v
CommunicationInterface
					|
SimulatedCommunication       future PLC/Modbus/VFD transport
					|                   
					v
			PlantInterface
					|
			FMUPlant                future HardwarePlant
					|
					v
OpenModelica FMI 2.0 FMU
```

The application-facing contracts are in `plant/interface.py`:

- `PlantState` contains observable channels such as speed, temperature,
	current, voltage, power, load, vibration, status, and thermal margin.
- `ControlCommand` contains timestamp, speed/load/cooling requests, command ID,
	source, and metadata.
- `PlantInterface` defines `start()`, `stop()`, `reset()`, `read_state()`,
	`send_command()`, and `step()`.

Simulation-specific details are isolated as follows:

- `plant/simulated/fmu_plant.py` adapts the FMU to `PlantInterface`.
- `simulation/fmu_runtime.py` owns low-level FMI lifecycle and typed I/O.
- `communication/simulated.py` provides the current in-process transport.
- `plant/hardware/interface.py` is the future hardware implementation boundary.
- `faults/physical.py` owns physical fault profiles and FMU fault injection.
- `estimation/thermal_state.py` exposes the thermal observer.
- `prediction/thermal.py` exposes the thermal predictor.
- `faults/diagnostics.py` exposes physical fault detection and severity logic.
- `control/` contains the existing controllers.
- `experiments/experiment_runner.py` coordinates the closed-loop run.

The simulation-only FMU truth used for offline evaluation is not part of
`PlantState` and is not sent to controllers, estimators, diagnostics, or
future cybersecurity code.

See `docs/architecture.md` for the detailed architecture and hardware
replacement plan.

## Validate the source model

Check the reference motor quantities:

```powershell
\.venv\Scripts\python.exe scripts\validate_reference_motor.py
```

Open `models/MotorElectroThermalMechanicalFaultable.mo` in OpenModelica/OMEdit
and run `Check -> Check Model` before changing the Modelica model.

## Export or refresh the FMU

The current repository contains `MotorElectroThermalMechanicalFaultable.fmu`
at the project root. Re-export it only when the Modelica model changes.

```powershell
\.venv\Scripts\python.exe scripts\export_fmu.py `
	--omhome "C:/Program Files/OpenModelica1.27.1-64bit"
```

The export script enables CVODE itself. It does not have a separate
`--cvode` command-line option.

## Run the FMU smoke test

This validates FMI initialization, typed inputs/outputs, stepping, and solver
timing without running the full digital-twin controller loop.

```powershell
\.venv\Scripts\python.exe simulation\fmu_runtime.py `
	--fmu .\MotorElectroThermalMechanicalFaultable.fmu `
	--stop 180 `
	--step 0.5 `
	--fault-time 60 `
	--output results\smoke_test.csv
```

## Run a closed-loop experiment

The authoritative runner is `experiments/experiment_runner.py`. It executes:

```text
state observation
	-> estimator
	-> fault diagnostics
	-> thermal prediction
	-> controller
	-> communication adapter
	-> FMU plant step
	-> CSV and metrics
```

Example:

```powershell
\.venv\Scripts\python.exe -m experiments.experiment_runner `
	--fmu .\MotorElectroThermalMechanicalFaultable.fmu `
	--scenario combined `
	--controller constrained `
	--stop 1800 `
	--step 0.5 `
	--fault-time 600 `
	--output results\combined_constrained_1800s.csv
```

Available physical scenarios:

- `healthy`
- `sensor_bias`
- `sensor_freeze`
- `cooling`
- `rth_degradation`
- `unbalance`
- `combined`

Available controllers:

- `baseline`
- `adaptive`
- `constrained`

Enable wall-clock pacing and deadline measurements with `--realtime`:

```powershell
\.venv\Scripts\python.exe -m experiments.experiment_runner `
	--fmu .\MotorElectroThermalMechanicalFaultable.fmu `
	--scenario combined `
	--controller constrained `
	--stop 800 `
	--step 0.5 `
	--fault-time 350 `
	--realtime `
	--output results\combined_constrained_800s_realtime.csv
```

## Run tests and analysis

```powershell
\.venv\Scripts\python.exe -m pytest -q
\.venv\Scripts\python.exe analysis\compare_evaluation.py `
	--input-dir results `
	--output results\compare.csv
\.venv\Scripts\python.exe analysis\generate_publication_figures.py
\.venv\Scripts\python.exe analysis\generate_publication_tables.py
```

The tests cover the constrained controller and the plant/communication
contracts. Result CSV files are time-series logs; comparison CSV files are
derived analysis products.

## Optional BaSyx integration

Start the local BaSyx services:

```powershell
docker compose -f docker\docker-compose.yml up -d
\.venv\Scripts\python.exe scripts\seed_basyx.py
\.venv\Scripts\python.exe experiments\basyx_smoke_test.py
```

Run an experiment with AAS synchronization:

```powershell
\.venv\Scripts\python.exe -m experiments.experiment_runner `
	--fmu .\MotorElectroThermalMechanicalFaultable.fmu `
	--scenario combined `
	--controller constrained `
	--basyx `
	--basyx-host http://localhost:8081 `
	--basyx-period 2
```

BaSyx is currently an integration/observability path. It does not change
controller decisions.

## Start the Streamlit UI

```powershell
\.venv\Scripts\python.exe -m streamlit run ui\app.py
```

The UI launches the existing experiment and comparison commands, visualizes
CSV results, and provides downloads. It does not contain controller or FMU
logic.

## How to start the cybersecurity project

Do not begin by modifying the Modelica model or adding attack code to the
controllers. The intended future security layer belongs around
`communication.CommunicationInterface`:

1. Define security-neutral observations and command-validation events around
	 `PlantState` and `ControlCommand`.
2. Add a security-aware communication adapter that can observe, validate, and
	 eventually allow, modify, block, or replace commands.
3. Add simulated communication faults and attack scenarios at that boundary,
	 not inside `FMUPlant` or the physical-fault profiles.
4. Add physics-informed residuals using the existing estimator and predictor.
5. Add cyber-versus-physical diagnosis only after the normal and physical-fault
	 baselines are stable.
6. Add risk and safe-state decisions as a separate layer, with explicit tests.
7. Later replace `FMUPlant` with `HardwarePlant` and replace
	 `SimulatedCommunication` with PLC/Modbus TCP/VFD adapters.

The future hardware should therefore replace adapters, not controllers,
estimators, metrics, or the cybersecurity decision layer.

## Current status and limitations

- The simulation FMU is the current plant implementation.
- Hardware is not connected or assumed.
- Cybersecurity algorithms are not implemented.
- Physical sensor, cooling, thermal-resistance, and unbalance phenomena are
	available for baseline experiments.
- The digital twin is a reduced-order research model and should not be treated
	as a certified motor protection system.
