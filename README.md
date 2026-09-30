# Cyber-Resilient Industrial Motor Control Foundation

This repository is the simulation foundation for the future project
"Cyber-Resilient Industrial Motor Control Using a Physics-Informed Digital
Twin".

The current scope is deliberately limited to the industrial motor digital
twin and its simulation infrastructure. Cyberattacks, Modbus attack code,
anomaly detection, risk scoring, prevention decisions, and ML models are not
implemented yet.

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
