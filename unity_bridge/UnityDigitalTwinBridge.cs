using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

/// <summary>
/// DRDO Digital Twin Unity 3D Bridge (PS ID: 26054)
/// Communicates in real-time with Python AI Backend / MCP Server.
/// Handles 60 FPS Revolving Camera Orbit, X-Ray Ghosting, and Holographic HUD Callouts.
/// </summary>
public class UnityDigitalTwinBridge : MonoBehaviour
{
    [Header("Backend Connection")]
    public string backendUrl = "http://localhost:8080/mcp";
    public float telemetryPollInterval = 0.1f; // 10 Hz Telemetry Stream

    [Header("Camera & Orbit Rig")]
    public Transform cameraPivot;
    public Camera mainCamera;
    public float orbitSpeed = 15.0f; // Degrees per second (60 FPS smooth)
    public bool isRevolving = true;

    [Header("Engine Root")]
    public GameObject engineRoot;

    [Header("Holographic HUD & Leader Line")]
    public LineRenderer leaderLineRenderer;
    public RectTransform holographicDiagnosticCard;
    public Canvas worldSpaceCanvas;

    [Header("X-Ray & Alert Materials")]
    public Material xRayGhostMaterial;
    public Material alertGlowMaterial;

    private Dictionary<Renderer, Material[]> originalMaterials = new Dictionary<Renderer, Material[]>();
    private Transform activeTargetComponent = null;
    private bool isFaultActive = false;

    void Start()
    {
        // Cache original PBR materials of all engine parts
        if (engineRoot != null)
        {
            Renderer[] renderers = engineRoot.GetComponentsInChildren<Renderer>();
            foreach (Renderer r in renderers)
            {
                originalMaterials[r] = r.sharedMaterials;
            }
        }

        // Hide Holographic Card initially
        if (holographicDiagnosticCard != null)
        {
            holographicDiagnosticCard.gameObject.SetActive(false);
        }

        // Start Telemetry Ingestion Loop
        StartCoroutine(PollTelemetryStream());
    }

    void Update()
    {
        // 1. Continuous 60 FPS Camera Orbit during normal state
        if (isRevolving && !isFaultActive && cameraPivot != null)
        {
            cameraPivot.Rotate(Vector3.up, orbitSpeed * Time.deltaTime, Space.World);
        }

        // 2. Update 3D Leader Line position if fault is active
        if (isFaultActive && activeTargetComponent != null && leaderLineRenderer != null)
        {
            Update3DLeaderLine();
        }

        // 3. User Escape Key Reset
        if (Input.GetKeyDown(KeyCode.Escape) && isFaultActive)
        {
            ResetToNormalOrbit();
        }
    }

    /// <summary>
    /// Polls real-time telemetry from Python AI Backend
    /// </summary>
    IEnumerator PollTelemetryStream()
    {
        while (true)
        {
            using (UnityWebRequest req = UnityWebRequest.Get(backendUrl))
            {
                yield return req.SendWebRequest();

                if (req.result == UnityWebRequest.Result.Success)
                {
                    string json = req.downloadHandler.text;
                    ProcessTelemetryResponse(json);
                }
            }
            yield return new WaitForSeconds(telemetryPollInterval);
        }
    }

    void ProcessTelemetryResponse(string json)
    {
        // Parse Telemetry JSON packet
        // If active_fault is detected, trigger corresponding 3D focus
    }

    /// <summary>
    /// Triggers 3D Component Focus, X-Ray Ghosting, and Holographic HUD
    /// </summary>
    public void TriggerComponentFault(string componentName, string faultTitle, string reading, string aiDiagnosis, string action)
    {
        isFaultActive = true;
        isRevolving = false;

        // Find Target Mesh in 3D Hierarchy
        Transform targetTransform = null;
        if (engineRoot != null)
        {
            foreach (Transform child in engineRoot.GetComponentsInChildren<Transform>())
            {
                if (child.name.IndexOf(componentName, StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    targetTransform = child;
                    break;
                }
            }
        }

        activeTargetComponent = targetTransform;

        // 1. Apply X-Ray Ghosting to Non-Target Parts
        foreach (var kvp in originalMaterials)
        {
            Renderer r = kvp.Key;
            if (activeTargetComponent != null && (r.transform == activeTargetComponent || r.transform.IsChildOf(activeTargetComponent)))
            {
                // Apply Pulsing Alert Glow
                r.material = alertGlowMaterial != null ? alertGlowMaterial : r.material;
            }
            else
            {
                // Apply Semi-Transparent Ghost Shader
                if (xRayGhostMaterial != null)
                {
                    r.material = xRayGhostMaterial;
                }
            }
        }

        // 2. Smoothly Move Camera to Frame Target & Whole Engine
        if (activeTargetComponent != null)
        {
            Vector3 focusPoint = activeTargetComponent.position;
            StartCoroutine(SmoothCameraFocus(focusPoint));
        }

        // 3. Show Holographic UI Card
        if (holographicDiagnosticCard != null)
        {
            holographicDiagnosticCard.gameObject.SetActive(true);
            // Populate Text Elements here...
        }
    }

    /// <summary>
    /// Resets Engine and Resumes 60 FPS Orbit (<kbd>Esc</kbd>)
    /// </summary>
    public void ResetToNormalOrbit()
    {
        isFaultActive = false;
        activeTargetComponent = null;

        // Restore Original Solid PBR Materials
        foreach (var kvp in originalMaterials)
        {
            kvp.Key.materials = kvp.Value;
        }

        // Hide UI Card & Leader Line
        if (holographicDiagnosticCard != null)
        {
            holographicDiagnosticCard.gameObject.SetActive(false);
        }
        if (leaderLineRenderer != null)
        {
            leaderLineRenderer.positionCount = 0;
        }

        isRevolving = true;
    }

    IEnumerator SmoothCameraFocus(Vector3 targetPos)
    {
        float elapsed = 0f;
        float duration = 1.0f;
        Vector3 startPivotPos = cameraPivot.position;

        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            float t = Mathf.SmoothStep(0f, 1f, elapsed / duration);
            cameraPivot.position = Vector3.Lerp(startPivotPos, targetPos, t);
            yield return null;
        }
    }

    void Update3DLeaderLine()
    {
        if (leaderLineRenderer == null || activeTargetComponent == null || holographicDiagnosticCard == null) return;

        leaderLineRenderer.positionCount = 3;
        Vector3 startPos = activeTargetComponent.position;
        Vector3 endPos = holographicDiagnosticCard.position;
        Vector3 midPos = new Vector3((startPos.x + endPos.x) * 0.5f, startPos.y, (startPos.z + endPos.z) * 0.5f);

        leaderLineRenderer.SetPosition(0, startPos);
        leaderLineRenderer.SetPosition(1, midPos);
        leaderLineRenderer.SetPosition(2, endPos);
    }
}
