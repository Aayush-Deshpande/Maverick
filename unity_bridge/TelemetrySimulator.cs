using System;
using System.Collections.Generic;
using UnityEngine;

namespace DigitalTwin.Core
{
    public class TelemetrySimulator : MonoBehaviour
    {
        public static TelemetrySimulator Instance { get; private set; }

        public event Action<EngineTelemetry> OnTelemetryUpdated;
        public event Action<FaultDefinition> OnFaultTriggered;
        public event Action OnFaultCleared;

        [Header("Telemetry State")]
        public EngineTelemetry currentTelemetry = new EngineTelemetry();
        public FaultDefinition activeFault = null;

        [Header("Simulation Parameters")]
        public bool isSimulating = true;
        public float updateRate = 20.0f; // 20 Hz
        private float updateTimer = 0f;
        private float noiseTime = 0f;

        private List<FaultDefinition> faultCatalog = new List<FaultDefinition>();

        void Awake()
        {
            if (Instance == null) Instance = this;
            else Destroy(gameObject);

            InitializeFaultCatalog();
        }

        void InitializeFaultCatalog()
        {
            faultCatalog = new List<FaultDefinition>()
            {
                new FaultDefinition()
                {
                    faultId = "FAULT_1_CYLINDER_OVERHEAT",
                    title = "CRITICAL: CYLINDER #2 CHT OVERHEAT",
                    targetComponentName = "Cylinder #2 Head Assembly",
                    targetMeshKeyword = "Covers_Theme_M_PlasticGreen",
                    subsystem = SubsystemType.CoolingSystem,
                    severity = SystemHealthStatus.Critical,
                    sensorReadingText = "CHT: 148.6 °C (Max Limit: 135.0 °C)",
                    aiDiagnosis = "Baffle seal deterioration causing acute cooling restriction & thermal runaway.",
                    rulImpactText = "-38% Flight Hours if uncorrected",
                    recommendedAction = "Enrich fuel mixture +12% / Throttle back 15% / Immediate RTB vector.",
                    focusOffset = new Vector3(-0.35f, 0.15f, 0.05f),
                    cameraDistance = 1.8f,
                    alertColor = new Color(1.0f, 0.1f, 0.15f, 1.0f)
                },
                new FaultDefinition()
                {
                    faultId = "FAULT_2_FUEL_INJECTOR",
                    title = "WARNING: FUEL INJECTOR #1 ABNORMALITY",
                    targetComponentName = "Electronic Fuel Injector #1",
                    targetMeshKeyword = "Rotax_912i_Base_M_PlasticGreen",
                    subsystem = SubsystemType.FuelSystem,
                    severity = SystemHealthStatus.Warning,
                    sensorReadingText = "Fuel Flow: 14.2 L/hr (-23% below map) | EGT: 865 °C",
                    aiDiagnosis = "Electromagnetic injector solenoid lag & partial nozzle deposit restriction.",
                    rulImpactText = "-22% RUL Impact (Valve seat oxidation risk)",
                    recommendedAction = "Switch to Lane B ECU backup map / Increase boost pump pressure.",
                    focusOffset = new Vector3(0.0f, 0.30f, 0.10f),
                    cameraDistance = 1.6f,
                    alertColor = new Color(1.0f, 0.65f, 0.0f, 1.0f)
                },
                new FaultDefinition()
                {
                    faultId = "FAULT_3_IGNITION_MISFIRE",
                    title = "WARNING: SECONDARY SPARK IGNITION MISFIRE",
                    targetComponentName = "Spark Plug Lead & Ignition Harness",
                    targetMeshKeyword = "Wiring_Harness_M_Copper",
                    subsystem = SubsystemType.IgnitionSystem,
                    severity = SystemHealthStatus.Warning,
                    sensorReadingText = "RPM Jitter: ±180 RPM | Crank Acceleration Dip",
                    aiDiagnosis = "Secondary ignition lead insulation breakdown; intermittent spark discharge.",
                    rulImpactText = "-18% RUL Impact (Unburnt carbon deposits)",
                    recommendedAction = "Activate redundant Lane B ignition coil set / Limit high manifold power.",
                    focusOffset = new Vector3(-0.25f, 0.05f, 0.05f),
                    cameraDistance = 1.7f,
                    alertColor = new Color(1.0f, 0.35f, 0.0f, 1.0f)
                },
                new FaultDefinition()
                {
                    faultId = "FAULT_4_LUBRICATION_DECAY",
                    title = "CRITICAL: OIL SYSTEM PRESSURE LOSS",
                    targetComponentName = "Dry-Sump Oil Reservoir & Scavenge Line",
                    targetMeshKeyword = "Oil_Tank",
                    subsystem = SubsystemType.LubricationSystem,
                    severity = SystemHealthStatus.Critical,
                    sensorReadingText = "Oil Press: 26.1 psi (Min: 29.0 psi) | Oil Temp: 128.4 °C",
                    aiDiagnosis = "Scavenge line aerated cavitation or pressure relief bypass leak.",
                    rulImpactText = "-55% RUL Impact (Crankshaft journal bearing wear)",
                    recommendedAction = "Immediate throttle reduction to 4,200 RPM / Execute emergency descent.",
                    focusOffset = new Vector3(-0.45f, 0.35f, -0.15f),
                    cameraDistance = 1.9f,
                    alertColor = new Color(1.0f, 0.05f, 0.1f, 1.0f)
                },
                new FaultDefinition()
                {
                    faultId = "FAULT_5_GEARBOX_VIBRATION",
                    title = "WARNING: PROPELLER GEARBOX HARMONIC VIBRATION",
                    targetComponentName = "Propeller Reduction Gearbox (Type 2)",
                    targetMeshKeyword = "Gearbox_Type_2",
                    subsystem = SubsystemType.EngineBlock,
                    severity = SystemHealthStatus.Warning,
                    sensorReadingText = "Vibration RMS: 2.85 mm/s (Limit: 1.5 mm/s) | 3rd Order Peak",
                    aiDiagnosis = "Overload dog clutch tooth wear & propeller shaft micro-misalignment.",
                    rulImpactText = "-30% Gearbox Fatigue Life remaining",
                    recommendedAction = "Limit rapid RPM transitions / Schedule dog clutch backlash inspection.",
                    focusOffset = new Vector3(0.0f, -0.25f, -0.05f),
                    cameraDistance = 1.8f,
                    alertColor = new Color(1.0f, 0.75f, 0.0f, 1.0f)
                },
                new FaultDefinition()
                {
                    faultId = "FAULT_6_EGT_IMBALANCE",
                    title = "WARNING: EXHAUST RUNNER EGT IMBALANCE",
                    targetComponentName = "Exhaust Runner Manifold (Runner #3)",
                    targetMeshKeyword = "Exhaust_System",
                    subsystem = SubsystemType.ExhaustSystem,
                    severity = SystemHealthStatus.Warning,
                    sensorReadingText = "EGT Runner #3: 895 °C (Delta > 65°C across runners)",
                    aiDiagnosis = "Uneven air-fuel distribution or partial exhaust restriction.",
                    rulImpactText = "-25% Thermal Life Impact on Exhaust Collector",
                    recommendedAction = "Adjust fuel trim on Cylinder 3 / Monitor downstream exhaust runner.",
                    focusOffset = new Vector3(0.0f, -0.15f, -0.30f),
                    cameraDistance = 1.8f,
                    alertColor = new Color(1.0f, 0.45f, 0.0f, 1.0f)
                },
                new FaultDefinition()
                {
                    faultId = "FAULT_7_ALTERNATOR_DROP",
                    title = "WARNING: ALTERNATOR VOLTAGE SAG",
                    targetComponentName = "Heavy-Duty Alternator & Serpentine Belt",
                    targetMeshKeyword = "External_Alternator",
                    subsystem = SubsystemType.ECU,
                    severity = SystemHealthStatus.Warning,
                    sensorReadingText = "Bus Voltage: 12.4 V (Nominal: 14.1 V) | Stator Phase Sag",
                    aiDiagnosis = "Alternator regulator diode breakdown or drive belt slip under high load.",
                    rulImpactText = "Battery depletion in ~42 mins without load shedding",
                    recommendedAction = "Shed non-essential ISR payload sensors / Engage backup battery bus.",
                    focusOffset = new Vector3(0.25f, -0.20f, 0.05f),
                    cameraDistance = 1.7f,
                    alertColor = new Color(1.0f, 0.7f, 0.0f, 1.0f)
                },
                new FaultDefinition()
                {
                    faultId = "FAULT_8_ECU_SENSOR_DRIFT",
                    title = "WARNING: DUAL FADEC SENSOR DRIFT",
                    targetComponentName = "Lane A/B Engine Control Unit & Sensor Array",
                    targetMeshKeyword = "ECU",
                    subsystem = SubsystemType.ECU,
                    severity = SystemHealthStatus.Warning,
                    sensorReadingText = "MAP Sensor Differential: 8.4 kPa between Lane A & Lane B",
                    aiDiagnosis = "Manifold pressure transducer drift on Lane A ECU channel.",
                    rulImpactText = "Reduced engine efficiency & autonomous trim accuracy",
                    recommendedAction = "Force FADEC control arbitration to Lane B / Flag for recalibration.",
                    focusOffset = new Vector3(0.30f, 0.35f, -0.05f),
                    cameraDistance = 1.7f,
                    alertColor = new Color(0.0f, 0.85f, 1.0f, 1.0f)
                }
            };
        }

        void Update()
        {
            if (!isSimulating) return;

            updateTimer += Time.deltaTime;
            if (updateTimer >= (1f / updateRate))
            {
                updateTimer = 0f;
                SimulateStep();
            }
        }

        void SimulateStep()
        {
            noiseTime += 0.05f;

            if (activeFault == null)
            {
                // Nominal Telemetry Noise
                currentTelemetry.rpm = 4380f + Mathf.PerlinNoise(noiseTime, 0f) * 35f - 17.5f;
                currentTelemetry.chtAvg = 86.7f + Mathf.PerlinNoise(0f, noiseTime) * 1.5f - 0.75f;
                currentTelemetry.egtAvg = 742f + Mathf.PerlinNoise(noiseTime, noiseTime) * 6f - 3f;
                currentTelemetry.oilPress = 52.3f + Mathf.PerlinNoise(noiseTime * 0.5f, 0f) * 1.2f - 0.6f;
                currentTelemetry.oilTemp = 78.2f + Mathf.PerlinNoise(0f, noiseTime * 0.5f) * 0.8f - 0.4f;
                currentTelemetry.fuelFlow = 16.8f + Mathf.PerlinNoise(noiseTime * 0.8f, noiseTime * 0.8f) * 0.4f - 0.2f;
                currentTelemetry.manifoldPress = 24.6f + Mathf.PerlinNoise(noiseTime * 0.3f, 0f) * 0.3f - 0.15f;
                currentTelemetry.vibration = 1.2f + Mathf.PerlinNoise(noiseTime * 2f, noiseTime * 2f) * 0.25f - 0.12f;
                currentTelemetry.busVoltage = 14.1f + Mathf.PerlinNoise(0f, noiseTime * 0.2f) * 0.1f - 0.05f;
                currentTelemetry.healthIndex = 98.4f;
                currentTelemetry.rulHours = 1420f;
            }
            else
            {
                // Fault-Specific Telemetry Spikes
                if (activeFault.faultId == "FAULT_1_CYLINDER_OVERHEAT")
                {
                    currentTelemetry.chtAvg = Mathf.Lerp(currentTelemetry.chtAvg, 148.6f, Time.deltaTime * 3f);
                    currentTelemetry.healthIndex = 62.0f;
                    currentTelemetry.rulHours = 820f;
                }
                else if (activeFault.faultId == "FAULT_4_LUBRICATION_DECAY")
                {
                    currentTelemetry.oilPress = Mathf.Lerp(currentTelemetry.oilPress, 26.1f, Time.deltaTime * 3f);
                    currentTelemetry.oilTemp = Mathf.Lerp(currentTelemetry.oilTemp, 128.4f, Time.deltaTime * 2f);
                    currentTelemetry.healthIndex = 45.0f;
                    currentTelemetry.rulHours = 640f;
                }
                else if (activeFault.faultId == "FAULT_5_GEARBOX_VIBRATION")
                {
                    currentTelemetry.vibration = Mathf.Lerp(currentTelemetry.vibration, 2.85f, Time.deltaTime * 3f);
                    currentTelemetry.healthIndex = 70.0f;
                }
            }

            OnTelemetryUpdated?.Invoke(currentTelemetry);
        }

        public void TriggerFault(string faultId)
        {
            FaultDefinition fault = faultCatalog.Find(f => f.faultId == faultId);
            if (fault != null)
            {
                activeFault = fault;
                OnFaultTriggered?.Invoke(fault);
            }
        }

        public void TriggerFaultByIndex(int index)
        {
            if (index >= 0 && index < faultCatalog.Count)
            {
                TriggerFault(faultCatalog[index].faultId);
            }
        }

        public void ClearFault()
        {
            activeFault = null;
            OnFaultCleared?.Invoke();
        }

        public List<FaultDefinition> GetFaultCatalog() => faultCatalog;
    }
}
