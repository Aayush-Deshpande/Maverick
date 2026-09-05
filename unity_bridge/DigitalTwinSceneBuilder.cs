#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;
using DigitalTwin.Core;

namespace DigitalTwin.Editor
{
    public class DigitalTwinSceneBuilder : MonoBehaviour
    {
        [MenuItem("DRDO Digital Twin/Build Full Digital Twin Scene", false, 1)]
        public static void BuildScene()
        {
            Debug.Log("=== DRDO Digital Twin: Starting Scene Build ===");

            // --- STOP PLAY MODE FIRST ---
            if (Application.isPlaying)
            {
                Debug.LogError("Please STOP Play Mode first before building the scene.");
                return;
            }

            // 1. Clean up 2D stuff
            DestroyIfExists("Global Light 2D");

            // 2. Camera Setup
            Camera mainCam = SetupCamera();

            // 3. Pivot for camera to orbit around
            GameObject pivotObj = FindOrCreate("CameraPivot");
            pivotObj.transform.position = Vector3.zero;

            OrbitCameraController camCtrl = GetOrAdd<OrbitCameraController>(mainCam.gameObject);
            camCtrl.pivotTransform = pivotObj.transform;
            camCtrl.targetCamera = mainCam;
            camCtrl.defaultDistance = 2.0f;
            camCtrl.minDistance = 0.5f;
            camCtrl.maxDistance = 6.0f;
            camCtrl.orbitSpeed = 15f;

            // 4. Lights
            SetupLights();

            // 5. Engine Model (FBX, scale in cm → set to 0.01 for meters)
            GameObject engineObj = SetupEngineModel();

            // 6. Auto-frame camera to engine bounds
            if (engineObj != null)
            {
                Bounds bounds = GetBounds(engineObj);
                float engineSize = bounds.size.magnitude;
                float idealDist = engineSize * 1.4f;
                camCtrl.defaultDistance = idealDist;

                // Aim pivot at center of engine
                pivotObj.transform.position = bounds.center;

                // Move camera to good starting position
                mainCam.transform.position = bounds.center + new Vector3(idealDist * 0.6f, idealDist * 0.35f, -idealDist);
                mainCam.transform.LookAt(bounds.center);

                Debug.Log($"Engine bounds: {bounds.size} | Camera distance set to {idealDist:F2}m");
            }

            // 7. Managers
            GameObject sysManager = FindOrCreate("DigitalTwin_System_Manager");
            EngineDigitalTwinManager twinMgr = GetOrAdd<EngineDigitalTwinManager>(sysManager);
            TelemetrySimulator telemSim = GetOrAdd<TelemetrySimulator>(sysManager);
            XRayMaterialManager matMgr = GetOrAdd<XRayMaterialManager>(sysManager);
            DigitalTwinUIManager uiMgr = GetOrAdd<DigitalTwinUIManager>(sysManager);

            twinMgr.engineRoot = engineObj;
            twinMgr.cameraController = camCtrl;
            twinMgr.materialManager = matMgr;
            twinMgr.telemetrySimulator = telemSim;
            twinMgr.uiManager = uiMgr;

            // 8. Canvas + HUD
            Canvas canvas = SetupCanvas();
            BuildHUD(canvas, uiMgr);

            HolographicLeaderLine leaderLine = SetupLeaderLine(canvas, mainCam);
            twinMgr.leaderLine = leaderLine;
            uiMgr.leaderLine = leaderLine;

            EditorUtility.SetDirty(sysManager);
            UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(
                UnityEditor.SceneManagement.EditorSceneManager.GetActiveScene());

            Debug.Log("=== DRDO Digital Twin: Scene Build COMPLETE! Press Play now. ===");
        }

        // ─── Helpers ─────────────────────────────────────────────────────────────

        static Camera SetupCamera()
        {
            Camera cam = Camera.main;
            if (cam == null)
            {
                GameObject obj = new GameObject("Main Camera");
                cam = obj.AddComponent<Camera>();
                obj.tag = "MainCamera";
            }
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.035f, 0.05f, 0.07f, 1f);
            cam.fieldOfView = 42f;
            cam.nearClipPlane = 0.01f;
            cam.farClipPlane = 500f;
            cam.allowHDR = true;
            return cam;
        }

        static void SetupLights()
        {
            // Key light
            Light key = FindOrCreate<Light>("Key Light", LightType.Directional);
            key.transform.rotation = Quaternion.Euler(48f, -30f, 0f);
            key.color = new Color(1.0f, 0.97f, 0.92f);
            key.intensity = 1.8f;
            key.shadows = LightShadows.Soft;

            // Fill light
            Light fill = FindOrCreate<Light>("Fill Light", LightType.Directional);
            fill.transform.rotation = Quaternion.Euler(25f, 150f, 0f);
            fill.color = new Color(0.82f, 0.90f, 1.0f);
            fill.intensity = 0.9f;
            fill.shadows = LightShadows.None;

            // Rim (back) light
            Light rim = FindOrCreate<Light>("Rim Light", LightType.Directional);
            rim.transform.rotation = Quaternion.Euler(-15f, 50f, 0f);
            rim.color = new Color(0.6f, 0.75f, 1.0f);
            rim.intensity = 0.5f;
            rim.shadows = LightShadows.None;
        }

        static GameObject SetupEngineModel()
        {
            GameObject existing = GameObject.Find("Rotax_912_iS_Sport_Engine");
            if (existing != null)
            {
                // Just re-center and fix scale
                FixEngineTransform(existing);
                return existing;
            }

            // Load from Assets
            GameObject fbxAsset = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/3D_Models/rotax_912_is_sport.fbx");
            if (fbxAsset == null)
            {
                Debug.LogError("FBX NOT FOUND at Assets/3D_Models/rotax_912_is_sport.fbx");
                return null;
            }

            GameObject engineObj = (GameObject)PrefabUtility.InstantiatePrefab(fbxAsset);
            engineObj.name = "Rotax_912_iS_Sport_Engine";
            FixEngineTransform(engineObj);
            Debug.Log("Engine model instantiated successfully!");
            return engineObj;
        }

        static void FixEngineTransform(GameObject engineObj)
        {
            engineObj.transform.position = Vector3.zero;
            engineObj.transform.rotation = Quaternion.Euler(0f, 200f, 0f); // Nice angle
            // Model units are cm → scale 0.01 to get meters. Rotax 912 is ~88cm long.
            engineObj.transform.localScale = Vector3.one * 0.01f;
        }

        static Canvas SetupCanvas()
        {
            Canvas existing = Object.FindObjectOfType<Canvas>();
            if (existing != null) return existing;

            GameObject obj = new GameObject("DigitalTwin_HUD_Canvas");
            Canvas canvas = obj.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 10;

            CanvasScaler scaler = obj.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            scaler.matchWidthOrHeight = 0.5f;

            obj.AddComponent<GraphicRaycaster>();
            return canvas;
        }

        static HolographicLeaderLine SetupLeaderLine(Canvas canvas, Camera cam)
        {
            HolographicLeaderLine existing = canvas.GetComponentInChildren<HolographicLeaderLine>();
            if (existing != null) return existing;

            GameObject obj = new GameObject("LeaderLineLayer");
            obj.transform.SetParent(canvas.transform, false);
            RectTransform rt = obj.AddComponent<RectTransform>();
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.offsetMin = rt.offsetMax = Vector2.zero;
            HolographicLeaderLine ll = obj.AddComponent<HolographicLeaderLine>();
            ll.targetCamera = cam;
            ll.rootCanvas = canvas;
            return ll;
        }

        static void BuildHUD(Canvas canvas, DigitalTwinUIManager uiMgr)
        {
            BuildTopHeader(canvas, uiMgr);
            BuildBottomBar(canvas, uiMgr);
            BuildDiagCard(canvas, uiMgr);
        }

        static void BuildTopHeader(Canvas canvas, DigitalTwinUIManager uiMgr)
        {
            if (canvas.transform.Find("TopHeader") != null) return;

            Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

            GameObject hdr = new GameObject("TopHeader");
            hdr.transform.SetParent(canvas.transform, false);
            RectTransform rt = hdr.AddComponent<RectTransform>();
            rt.anchorMin = new Vector2(0, 1); rt.anchorMax = new Vector2(1, 1);
            rt.pivot = new Vector2(0.5f, 1f);
            rt.sizeDelta = new Vector2(0, 64);
            rt.anchoredPosition = Vector2.zero;

            Image bg = hdr.AddComponent<Image>();
            bg.color = new Color(0.04f, 0.055f, 0.08f, 0.92f);

            // Title
            uiMgr.titleText = MakeText(hdr.transform, "TitleText",
                new Vector2(0, 0.5f), new Vector2(0, 0.5f),
                new Vector2(22, 10), new Vector2(420, 28),
                "MALE UAV ENGINE DIGITAL TWIN", font, 17, FontStyle.Bold, Color.white, TextAnchor.MiddleLeft);

            // Subtitle
            uiMgr.subtitleText = MakeText(hdr.transform, "SubtitleText",
                new Vector2(0, 0.5f), new Vector2(0, 0.5f),
                new Vector2(22, -14), new Vector2(480, 18),
                "Real-time Health Monitoring | Fault Prediction | Mission Reliability",
                font, 10, FontStyle.Normal, new Color(0.55f, 0.68f, 0.78f), TextAnchor.MiddleLeft);

            // Status badge (center)
            GameObject badge = MakePanel(hdr.transform, "StatusBadge",
                new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
                Vector2.zero, new Vector2(260, 34));
            badge.GetComponent<Image>().color = new Color(0f, 0.75f, 0.35f, 0.18f);
            uiMgr.systemStatusBadge = badge.GetComponent<Image>();

            uiMgr.systemStatusText = MakeText(badge.transform, "StatusText",
                Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero,
                "● SYSTEM STATUS: NOMINAL", font, 12, FontStyle.Bold,
                new Color(0.1f, 1f, 0.5f), TextAnchor.MiddleCenter);

            // Clock
            uiMgr.utcClockText = MakeText(hdr.transform, "ClockText",
                new Vector2(1, 0.5f), new Vector2(1, 0.5f),
                new Vector2(-20, 0), new Vector2(280, 24),
                "28 AUG 2026 | 00:00 UTC", font, 11, FontStyle.Normal,
                Color.white, TextAnchor.MiddleRight);
        }

        static void BuildBottomBar(Canvas canvas, DigitalTwinUIManager uiMgr)
        {
            if (canvas.transform.Find("BottomTelemetryBar") != null) return;

            Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

            GameObject bar = new GameObject("BottomTelemetryBar");
            bar.transform.SetParent(canvas.transform, false);
            RectTransform rt = bar.AddComponent<RectTransform>();
            rt.anchorMin = new Vector2(0, 0); rt.anchorMax = new Vector2(1, 0);
            rt.pivot = new Vector2(0.5f, 0);
            rt.sizeDelta = new Vector2(0, 88);
            rt.anchoredPosition = Vector2.zero;

            Image bg = bar.AddComponent<Image>();
            bg.color = new Color(0.04f, 0.055f, 0.08f, 0.92f);

            HorizontalLayoutGroup hlg = bar.AddComponent<HorizontalLayoutGroup>();
            hlg.padding = new RectOffset(16, 16, 8, 8);
            hlg.spacing = 8;
            hlg.childControlWidth = true;
            hlg.childControlHeight = true;
            hlg.childForceExpandWidth = true;
            hlg.childForceExpandHeight = true;

            MakeMetricCard(bar.transform, font, "RPM",            "4380",  "rpm",  3000, 6200, out uiMgr.rpmValueText,           out uiMgr.rpmSparkline);
            MakeMetricCard(bar.transform, font, "CHT AVG",        "86.7",  "°C",   50,   165,  out uiMgr.chtValueText,           out uiMgr.chtSparkline);
            MakeMetricCard(bar.transform, font, "EGT AVG",        "742",   "°C",   600,  950,  out uiMgr.egtValueText,           out uiMgr.egtSparkline);
            MakeMetricCard(bar.transform, font, "OIL PRESS",      "52.3",  "psi",  20,   80,   out uiMgr.oilPressValueText,      out uiMgr.oilPressSparkline);
            MakeMetricCard(bar.transform, font, "OIL TEMP",       "78.2",  "°C",   40,   140,  out uiMgr.oilTempValueText,       out uiMgr.oilTempSparkline);
            MakeMetricCard(bar.transform, font, "FUEL FLOW",      "16.8",  "L/hr", 5,    30,   out uiMgr.fuelFlowValueText,      out uiMgr.fuelFlowSparkline);
            MakeMetricCard(bar.transform, font, "MANIFOLD PRESS", "24.6",  "inHg", 15,   35,   out uiMgr.manifoldPressValueText, out uiMgr.manifoldPressSparkline);
            MakeMetricCard(bar.transform, font, "VIBRATION",      "1.2",   "mm/s", 0,    5,    out uiMgr.vibrationValueText,     out uiMgr.vibrationSparkline);
        }

        static void MakeMetricCard(Transform parent, Font font, string label, string initVal, string unit,
            float min, float max, out Text valText, out ProceduralSparkline sparkline)
        {
            GameObject card = new GameObject(label.Replace(" ", "_") + "_Card");
            card.transform.SetParent(parent, false);

            Image bg = card.AddComponent<Image>();
            bg.color = new Color(0.07f, 0.10f, 0.15f, 1f);

            VerticalLayoutGroup vlg = card.AddComponent<VerticalLayoutGroup>();
            vlg.childControlWidth = true;
            vlg.childControlHeight = false;
            vlg.childForceExpandWidth = true;
            vlg.padding = new RectOffset(4, 4, 6, 4);
            vlg.spacing = 2;

            // Label
            GameObject lObj = new GameObject("Label");
            lObj.transform.SetParent(card.transform, false);
            LayoutElement le = lObj.AddComponent<LayoutElement>();
            le.preferredHeight = 14;
            Text lt = lObj.AddComponent<Text>();
            lt.font = font;
            lt.fontSize = 9;
            lt.alignment = TextAnchor.MiddleCenter;
            lt.color = new Color(0.55f, 0.68f, 0.78f);
            lt.text = label;

            // Value
            GameObject vObj = new GameObject("Value");
            vObj.transform.SetParent(card.transform, false);
            LayoutElement vle = vObj.AddComponent<LayoutElement>();
            vle.preferredHeight = 22;
            valText = vObj.AddComponent<Text>();
            valText.font = font;
            valText.fontSize = 17;
            valText.fontStyle = FontStyle.Bold;
            valText.alignment = TextAnchor.MiddleCenter;
            valText.color = Color.white;
            valText.text = initVal;

            // Unit label
            GameObject uObj = new GameObject("Unit");
            uObj.transform.SetParent(card.transform, false);
            LayoutElement ule = uObj.AddComponent<LayoutElement>();
            ule.preferredHeight = 12;
            Text ut = uObj.AddComponent<Text>();
            ut.font = font;
            ut.fontSize = 8;
            ut.alignment = TextAnchor.MiddleCenter;
            ut.color = new Color(0.5f, 0.55f, 0.6f);
            ut.text = unit;

            // Sparkline
            GameObject sObj = new GameObject("Sparkline");
            sObj.transform.SetParent(card.transform, false);
            LayoutElement sle = sObj.AddComponent<LayoutElement>();
            sle.preferredHeight = 14;
            sparkline = sObj.AddComponent<ProceduralSparkline>();
            sparkline.SetRange(min, max);
        }

        static void BuildDiagCard(Canvas canvas, DigitalTwinUIManager uiMgr)
        {
            if (canvas.transform.Find("DiagnosticHUDCard") != null) return;

            Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

            GameObject card = new GameObject("DiagnosticHUDCard");
            card.transform.SetParent(canvas.transform, false);
            RectTransform rt = card.AddComponent<RectTransform>();
            rt.anchorMin = new Vector2(0, 0.5f); rt.anchorMax = new Vector2(0, 0.5f);
            rt.pivot = new Vector2(0, 0.5f);
            rt.sizeDelta = new Vector2(370, 250);
            rt.anchoredPosition = new Vector2(32, 0);
            uiMgr.diagnosticCardRect = rt;

            Image bg = card.AddComponent<Image>();
            bg.color = new Color(0.07f, 0.09f, 0.13f, 0.97f);

            // Top colored border
            GameObject border = new GameObject("TopBorder");
            border.transform.SetParent(card.transform, false);
            RectTransform brt = border.AddComponent<RectTransform>();
            brt.anchorMin = new Vector2(0, 1); brt.anchorMax = new Vector2(1, 1);
            brt.pivot = new Vector2(0.5f, 1f);
            brt.sizeDelta = new Vector2(0, 3);
            Image bImg = border.AddComponent<Image>();
            bImg.color = new Color(1f, 0.1f, 0.2f);

            uiMgr.diagTitleText = MakeText(card.transform, "DiagTitle",
                new Vector2(0, 1), new Vector2(1, 1), new Vector2(16, -16), new Vector2(-32, 20),
                "⚠ CRITICAL ANOMALY DETECTED", font, 12, FontStyle.Bold, new Color(1f, 0.2f, 0.3f), TextAnchor.MiddleLeft);

            uiMgr.diagComponentText = MakeText(card.transform, "DiagComponent",
                new Vector2(0, 1), new Vector2(1, 1), new Vector2(16, -42), new Vector2(-32, 22),
                "Cylinder #2 Head Assembly", font, 15, FontStyle.Bold, new Color(0f, 0.9f, 1f), TextAnchor.MiddleLeft);

            uiMgr.diagSensorReadingText = MakeText(card.transform, "DiagSensor",
                new Vector2(0, 1), new Vector2(1, 1), new Vector2(16, -68), new Vector2(-32, 20),
                "CHT: 148.6 °C  (Limit: 135.0 °C)", font, 12, FontStyle.Bold, new Color(1f, 0.3f, 0.3f), TextAnchor.MiddleLeft);

            uiMgr.diagAiDiagnosisText = MakeText(card.transform, "DiagAI",
                new Vector2(0, 1), new Vector2(1, 1), new Vector2(16, -100), new Vector2(-32, 60),
                "AI Diagnosis: Baffle seal restriction causing\nthermal runaway in cylinder #2.\nCheck cooling fin blockage.", font, 10, FontStyle.Normal, Color.white, TextAnchor.UpperLeft);

            // Ack button
            GameObject btnObj = new GameObject("AcknowledgeButton");
            btnObj.transform.SetParent(card.transform, false);
            RectTransform bRt = btnObj.AddComponent<RectTransform>();
            bRt.anchorMin = new Vector2(0, 0); bRt.anchorMax = new Vector2(1, 0);
            bRt.pivot = new Vector2(0.5f, 0);
            bRt.sizeDelta = new Vector2(-32, 32);
            bRt.anchoredPosition = new Vector2(0, 14);
            Image btnBg = btnObj.AddComponent<Image>();
            btnBg.color = new Color(0.7f, 0.05f, 0.12f, 1f);
            Button btn = btnObj.AddComponent<Button>();
            uiMgr.diagAcknowledgeButton = btn;

            MakeText(btnObj.transform, "BtnLabel",
                Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero,
                "ACKNOWLEDGE & RESUME ORBIT  [ESC]", font, 10, FontStyle.Bold, Color.white, TextAnchor.MiddleCenter);

            card.SetActive(false); // Hidden until fault fires
        }

        // ─── UI Primitives ────────────────────────────────────────────────────────

        static Text MakeText(Transform parent, string name,
            Vector2 anchorMin, Vector2 anchorMax,
            Vector2 anchoredPos, Vector2 sizeDelta,
            string content, Font font, int fontSize, FontStyle style, Color color, TextAnchor align)
        {
            GameObject obj = new GameObject(name);
            obj.transform.SetParent(parent, false);
            RectTransform rt = obj.AddComponent<RectTransform>();
            rt.anchorMin = anchorMin;
            rt.anchorMax = anchorMax;
            rt.anchoredPosition = anchoredPos;
            rt.sizeDelta = sizeDelta;
            Text t = obj.AddComponent<Text>();
            t.font = font;
            t.fontSize = fontSize;
            t.fontStyle = style;
            t.color = color;
            t.text = content;
            t.alignment = align;
            t.supportRichText = true;
            return t;
        }

        static GameObject MakePanel(Transform parent, string name,
            Vector2 anchorMin, Vector2 anchorMax,
            Vector2 anchoredPos, Vector2 sizeDelta)
        {
            GameObject obj = new GameObject(name);
            obj.transform.SetParent(parent, false);
            RectTransform rt = obj.AddComponent<RectTransform>();
            rt.anchorMin = anchorMin;
            rt.anchorMax = anchorMax;
            rt.anchoredPosition = anchoredPos;
            rt.sizeDelta = sizeDelta;
            obj.AddComponent<Image>();
            return obj;
        }

        // ─── GameObject Helpers ───────────────────────────────────────────────────

        static GameObject FindOrCreate(string name)
        {
            return GameObject.Find(name) ?? new GameObject(name);
        }

        static Light FindOrCreate<T>(string name, LightType type) where T : Light
        {
            GameObject obj = GameObject.Find(name) ?? new GameObject(name);
            Light l = obj.GetComponent<Light>() ?? obj.AddComponent<Light>();
            l.type = type;
            return l;
        }

        static T GetOrAdd<T>(GameObject obj) where T : Component
        {
            return obj.GetComponent<T>() ?? obj.AddComponent<T>();
        }

        static void DestroyIfExists(string name)
        {
            GameObject obj = GameObject.Find(name);
            if (obj != null) Object.DestroyImmediate(obj);
        }

        static Bounds GetBounds(GameObject root)
        {
            Renderer[] renderers = root.GetComponentsInChildren<Renderer>();
            if (renderers.Length == 0) return new Bounds(root.transform.position, Vector3.one);

            Bounds b = renderers[0].bounds;
            foreach (Renderer r in renderers) b.Encapsulate(r.bounds);
            return b;
        }
    }
}
#endif
