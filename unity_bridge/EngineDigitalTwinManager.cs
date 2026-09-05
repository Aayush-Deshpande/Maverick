using System;
using System.Collections.Generic;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace DigitalTwin.Core
{
    public class EngineDigitalTwinManager : MonoBehaviour
    {
        public static EngineDigitalTwinManager Instance { get; private set; }

        [Header("Core Subsystems")]
        public GameObject engineRoot;
        public OrbitCameraController cameraController;
        public XRayMaterialManager materialManager;
        public TelemetrySimulator telemetrySimulator;
        public DigitalTwinUIManager uiManager;
        public HolographicLeaderLine leaderLine;

        [Header("Active State")]
        public bool isFaultActive = false;
        public FaultDefinition currentFault = null;

        void Awake()
        {
            if (Instance == null) Instance = this;
            else Destroy(gameObject);
        }

        void Start()
        {
            if (cameraController == null) cameraController = FindObjectOfType<OrbitCameraController>();
            if (materialManager == null) materialManager = FindObjectOfType<XRayMaterialManager>();
            if (telemetrySimulator == null) telemetrySimulator = FindObjectOfType<TelemetrySimulator>();
            if (uiManager == null) uiManager = FindObjectOfType<DigitalTwinUIManager>();
            if (leaderLine == null) leaderLine = FindObjectOfType<HolographicLeaderLine>();

            if (materialManager != null && engineRoot != null)
            {
                materialManager.Initialize(engineRoot);
            }

            if (telemetrySimulator != null)
            {
                telemetrySimulator.OnFaultTriggered += HandleFaultTriggered;
                telemetrySimulator.OnFaultCleared += HandleFaultCleared;
            }
        }

        void Update()
        {
            HandleInput();
        }

        void HandleInput()
        {
#if ENABLE_INPUT_SYSTEM
            if (Keyboard.current == null) return;

            // Number Keys 1-8
            if (Keyboard.current.digit1Key.wasPressedThisFrame || Keyboard.current.numpad1Key.wasPressedThisFrame) telemetrySimulator?.TriggerFaultByIndex(0);
            if (Keyboard.current.digit2Key.wasPressedThisFrame || Keyboard.current.numpad2Key.wasPressedThisFrame) telemetrySimulator?.TriggerFaultByIndex(1);
            if (Keyboard.current.digit3Key.wasPressedThisFrame || Keyboard.current.numpad3Key.wasPressedThisFrame) telemetrySimulator?.TriggerFaultByIndex(2);
            if (Keyboard.current.digit4Key.wasPressedThisFrame || Keyboard.current.numpad4Key.wasPressedThisFrame) telemetrySimulator?.TriggerFaultByIndex(3);
            if (Keyboard.current.digit5Key.wasPressedThisFrame || Keyboard.current.numpad5Key.wasPressedThisFrame) telemetrySimulator?.TriggerFaultByIndex(4);
            if (Keyboard.current.digit6Key.wasPressedThisFrame || Keyboard.current.numpad6Key.wasPressedThisFrame) telemetrySimulator?.TriggerFaultByIndex(5);
            if (Keyboard.current.digit7Key.wasPressedThisFrame || Keyboard.current.numpad7Key.wasPressedThisFrame) telemetrySimulator?.TriggerFaultByIndex(6);
            if (Keyboard.current.digit8Key.wasPressedThisFrame || Keyboard.current.numpad8Key.wasPressedThisFrame) telemetrySimulator?.TriggerFaultByIndex(7);

            // Spacebar toggles auto-orbit
            if (Keyboard.current.spaceKey.wasPressedThisFrame && cameraController != null)
            {
                cameraController.isAutoRevolving = !cameraController.isAutoRevolving;
            }

            // Escape returns to normal state
            if (Keyboard.current.escapeKey.wasPressedThisFrame && isFaultActive)
            {
                ResetToNormalState();
            }
#else
            for (int i = 1; i <= 8; i++)
            {
                if (Input.GetKeyDown(KeyCode.Alpha0 + i) || Input.GetKeyDown(KeyCode.Keypad0 + i))
                {
                    telemetrySimulator?.TriggerFaultByIndex(i - 1);
                }
            }

            if (Input.GetKeyDown(KeyCode.Space) && cameraController != null)
            {
                cameraController.isAutoRevolving = !cameraController.isAutoRevolving;
            }

            if (Input.GetKeyDown(KeyCode.Escape) && isFaultActive)
            {
                ResetToNormalState();
            }
#endif
        }

        public void HandleFaultTriggered(FaultDefinition fault)
        {
            isFaultActive = true;
            currentFault = fault;

            // 1. Find Target Component in 3D Engine Hierarchy
            Transform targetTransform = null;
            if (engineRoot != null)
            {
                foreach (Transform child in engineRoot.GetComponentsInChildren<Transform>(true))
                {
                    if (child.name.IndexOf(fault.targetMeshKeyword, StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        targetTransform = child;
                        break;
                    }
                }
            }

            // 2. Camera Tween directly to Component Focus Position
            if (cameraController != null)
            {
                Vector3 targetWorldPos = targetTransform != null ? targetTransform.position : (engineRoot != null ? engineRoot.transform.position + fault.focusOffset : fault.focusOffset);
                cameraController.FocusOnComponent(targetWorldPos, fault.cameraDistance);
            }

            // 3. Apply X-Ray Ghosting and Glow Highlight
            if (materialManager != null)
            {
                materialManager.ApplyFaultHighlight(fault.targetMeshKeyword, fault.alertColor);
            }

            // 4. Attach 3D Holographic Leader Line
            if (leaderLine != null && targetTransform != null && uiManager != null && uiManager.diagnosticCardRect != null)
            {
                leaderLine.SetTarget(targetTransform, uiManager.diagnosticCardRect);
            }
        }

        public void HandleFaultCleared()
        {
            isFaultActive = false;
            currentFault = null;

            if (materialManager != null) materialManager.ResetMaterials();
            if (leaderLine != null) leaderLine.ClearTarget();
            if (cameraController != null) cameraController.ResetView();
        }

        public void ResetToNormalState()
        {
            if (telemetrySimulator != null)
            {
                telemetrySimulator.ClearFault();
            }
            else
            {
                HandleFaultCleared();
            }
        }
    }
}
