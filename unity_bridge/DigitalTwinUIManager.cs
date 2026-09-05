using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace DigitalTwin.Core
{
    public class DigitalTwinUIManager : MonoBehaviour
    {
        public static DigitalTwinUIManager Instance { get; private set; }

        [Header("Top Header Elements")]
        public Text titleText;
        public Text subtitleText;
        public Text systemStatusText;
        public Image systemStatusBadge;
        public Text utcClockText;

        [Header("Bottom Telemetry Cards")]
        public Text rpmValueText;
        public ProceduralSparkline rpmSparkline;
        public Text chtValueText;
        public ProceduralSparkline chtSparkline;
        public Text egtValueText;
        public ProceduralSparkline egtSparkline;
        public Text oilPressValueText;
        public ProceduralSparkline oilPressSparkline;
        public Text oilTempValueText;
        public ProceduralSparkline oilTempSparkline;
        public Text fuelFlowValueText;
        public ProceduralSparkline fuelFlowSparkline;
        public Text manifoldPressValueText;
        public ProceduralSparkline manifoldPressSparkline;
        public Text vibrationValueText;
        public ProceduralSparkline vibrationSparkline;

        [Header("Right Dynamic Intelligence Panel")]
        public GameObject rightPanelRoot;
        public Text missionReadinessText;
        public Image missionReadinessRing;
        public Transform subsystemListContainer;

        [Header("Floating Holographic Diagnostic HUD")]
        public RectTransform diagnosticCardRect;
        public Text diagTitleText;
        public Text diagComponentText;
        public Text diagSensorReadingText;
        public Text diagAiDiagnosisText;
        public Text diagRulImpactText;
        public Text diagActionText;
        public Button diagAcknowledgeButton;
        public HolographicLeaderLine leaderLine;

        [Header("Colors & Themes")]
        public Color nominalGreen = new Color(0.0f, 1.0f, 0.53f, 1.0f);
        public Color warningAmber = new Color(1.0f, 0.72f, 0.0f, 1.0f);
        public Color criticalRed = new Color(1.0f, 0.16f, 0.33f, 1.0f);

        void Awake()
        {
            if (Instance == null) Instance = this;
            else Destroy(gameObject);

            if (diagnosticCardRect != null) diagnosticCardRect.gameObject.SetActive(false);
            if (diagAcknowledgeButton != null)
            {
                diagAcknowledgeButton.onClick.AddListener(() =>
                {
                    EngineDigitalTwinManager.Instance?.ResetToNormalState();
                });
            }
        }

        void Start()
        {
            if (TelemetrySimulator.Instance != null)
            {
                TelemetrySimulator.Instance.OnTelemetryUpdated += UpdateTelemetryUI;
                TelemetrySimulator.Instance.OnFaultTriggered += DisplayFaultAlert;
                TelemetrySimulator.Instance.OnFaultCleared += ClearFaultAlert;
            }
        }

        void Update()
        {
            if (utcClockText != null)
            {
                utcClockText.text = DateTime.UtcNow.ToString("dd MMM yyyy | HH:mm:ss") + " UTC";
            }
        }

        public void UpdateTelemetryUI(EngineTelemetry telem)
        {
            if (rpmValueText != null) rpmValueText.text = telem.rpm.ToString("F0");
            if (rpmSparkline != null) rpmSparkline.AddDataPoint(telem.rpm);

            if (chtValueText != null) chtValueText.text = telem.chtAvg.ToString("F1");
            if (chtSparkline != null) chtSparkline.AddDataPoint(telem.chtAvg);

            if (egtValueText != null) egtValueText.text = telem.egtAvg.ToString("F0");
            if (egtSparkline != null) egtSparkline.AddDataPoint(telem.egtAvg);

            if (oilPressValueText != null) oilPressValueText.text = telem.oilPress.ToString("F1");
            if (oilPressSparkline != null) oilPressSparkline.AddDataPoint(telem.oilPress);

            if (oilTempValueText != null) oilTempValueText.text = telem.oilTemp.ToString("F1");
            if (oilTempSparkline != null) oilTempSparkline.AddDataPoint(telem.oilTemp);

            if (fuelFlowValueText != null) fuelFlowValueText.text = telem.fuelFlow.ToString("F1");
            if (fuelFlowSparkline != null) fuelFlowSparkline.AddDataPoint(telem.fuelFlow);

            if (manifoldPressValueText != null) manifoldPressValueText.text = telem.manifoldPress.ToString("F1");
            if (manifoldPressSparkline != null) manifoldPressSparkline.AddDataPoint(telem.manifoldPress);

            if (vibrationValueText != null) vibrationValueText.text = telem.vibration.ToString("F1");
            if (vibrationSparkline != null) vibrationSparkline.AddDataPoint(telem.vibration);
        }

        public void DisplayFaultAlert(FaultDefinition fault)
        {
            // Update Top Status Pill
            if (systemStatusText != null)
            {
                systemStatusText.text = fault.severity == SystemHealthStatus.Critical ? "SYSTEM STATUS: CRITICAL" : "SYSTEM STATUS: WARNING";
                systemStatusText.color = fault.severity == SystemHealthStatus.Critical ? criticalRed : warningAmber;
            }

            // Populate Diagnostic Card
            if (diagTitleText != null) diagTitleText.text = fault.title;
            if (diagComponentText != null) diagComponentText.text = fault.targetComponentName;
            if (diagSensorReadingText != null) diagSensorReadingText.text = fault.sensorReadingText;
            if (diagAiDiagnosisText != null) diagAiDiagnosisText.text = fault.aiDiagnosis;
            if (diagRulImpactText != null) diagRulImpactText.text = fault.rulImpactText;
            if (diagActionText != null) diagActionText.text = fault.recommendedAction;

            if (diagnosticCardRect != null)
            {
                diagnosticCardRect.gameObject.SetActive(true);
            }
        }

        public void ClearFaultAlert()
        {
            if (systemStatusText != null)
            {
                systemStatusText.text = "SYSTEM STATUS: NOMINAL";
                systemStatusText.color = nominalGreen;
            }

            if (diagnosticCardRect != null)
            {
                diagnosticCardRect.gameObject.SetActive(false);
            }

            if (leaderLine != null)
            {
                leaderLine.ClearTarget();
            }
        }
    }
}
