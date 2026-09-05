using System;
using System.Collections.Generic;
using UnityEngine;

namespace DigitalTwin.Core
{
    [Serializable]
    public class EngineTelemetry
    {
        public float rpm = 4380f;
        public float chtAvg = 86.7f;
        public float[] chtCylinders = new float[4] { 85.2f, 86.7f, 84.9f, 87.1f };
        public float egtAvg = 742f;
        public float[] egtRunners = new float[4] { 740f, 745f, 738f, 742f };
        public float oilPress = 52.3f; // psi
        public float oilTemp = 78.2f;  // °C
        public float fuelFlow = 16.8f; // L/hr
        public float manifoldPress = 24.6f; // inHg
        public float vibration = 1.2f; // mm/s
        public float busVoltage = 14.1f; // V
        public float healthIndex = 98.4f; // %
        public float rulHours = 1420f;
    }

    public enum SubsystemType
    {
        EngineBlock,
        FuelSystem,
        IgnitionSystem,
        CoolingSystem,
        ExhaustSystem,
        LubricationSystem,
        ECU
    }

    public enum SystemHealthStatus
    {
        Nominal,
        Warning,
        Critical
    }

    [Serializable]
    public class FaultDefinition
    {
        public string faultId;
        public string title;
        public string targetComponentName;
        public string targetMeshKeyword;
        public SubsystemType subsystem;
        public SystemHealthStatus severity;
        public string sensorReadingText;
        public string aiDiagnosis;
        public string rulImpactText;
        public string recommendedAction;
        public Vector3 focusOffset = new Vector3(-0.35f, 0.15f, 0f);
        public float cameraDistance = 2.2f;
        public Color alertColor = new Color(1f, 0.15f, 0.2f, 1f);
    }
}
