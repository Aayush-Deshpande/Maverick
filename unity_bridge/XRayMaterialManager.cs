using System;
using System.Collections.Generic;
using UnityEngine;

namespace DigitalTwin.Core
{
    public class XRayMaterialManager : MonoBehaviour
    {
        [Header("Engine Root")]
        public GameObject engineRoot;

        [Header("Ghost Shader Settings")]
        [Range(0.05f, 0.5f)] public float ghostOpacity = 0.14f;
        public Color ghostColor = new Color(0.6f, 0.8f, 1.0f, 0.14f);

        // Cached original materials
        private Dictionary<Renderer, Material[]> originalMaterials = new Dictionary<Renderer, Material[]>();
        private Dictionary<Renderer, Material[]> runtimeInstanceMaterials = new Dictionary<Renderer, Material[]>();
        private List<Renderer> activeTargetRenderers = new List<Renderer>();
        private bool isGhostActive = false;
        private float pulseTimer = 0f;
        private Color currentAlertColor = Color.red;

        public void Initialize(GameObject root)
        {
            engineRoot = root;
            CacheOriginalMaterials();
        }

        void CacheOriginalMaterials()
        {
            if (engineRoot == null) return;

            originalMaterials.Clear();
            runtimeInstanceMaterials.Clear();

            Renderer[] renderers = engineRoot.GetComponentsInChildren<Renderer>(true);
            foreach (Renderer r in renderers)
            {
                originalMaterials[r] = r.sharedMaterials;
                // Create instance copies for runtime modification
                Material[] instances = new Material[r.sharedMaterials.Length];
                for (int i = 0; i < instances.Length; i++)
                {
                    if (r.sharedMaterials[i] != null)
                    {
                        instances[i] = new Material(r.sharedMaterials[i]);
                    }
                }
                runtimeInstanceMaterials[r] = instances;
            }
        }

        void Update()
        {
            // Pulsing emission on highlighted faulty component
            if (isGhostActive && activeTargetRenderers.Count > 0)
            {
                pulseTimer += Time.deltaTime * 4.0f;
                float intensity = 1.5f + Mathf.Sin(pulseTimer) * 1.5f; // Oscillates between 0.0 and 3.0
                Color emissiveColor = currentAlertColor * Mathf.LinearToGammaSpace(intensity);

                foreach (Renderer r in activeTargetRenderers)
                {
                    if (r == null || !runtimeInstanceMaterials.ContainsKey(r)) continue;
                    Material[] mats = runtimeInstanceMaterials[r];
                    foreach (Material m in mats)
                    {
                        if (m != null)
                        {
                            m.EnableKeyword("_EMISSION");
                            m.SetColor("_EmissionColor", emissiveColor);
                            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", currentAlertColor);
                            if (m.HasProperty("_Color")) m.SetColor("_Color", currentAlertColor);
                        }
                    }
                }
            }
        }

        public void ApplyFaultHighlight(string targetMeshKeyword, Color alertColor)
        {
            if (engineRoot == null) return;
            if (originalMaterials.Count == 0) CacheOriginalMaterials();

            isGhostActive = true;
            currentAlertColor = alertColor;
            activeTargetRenderers.Clear();

            Renderer[] renderers = engineRoot.GetComponentsInChildren<Renderer>(true);
            foreach (Renderer r in renderers)
            {
                bool isTarget = r.name.IndexOf(targetMeshKeyword, StringComparison.OrdinalIgnoreCase) >= 0;

                if (isTarget)
                {
                    activeTargetRenderers.Add(r);
                    Material[] mats = runtimeInstanceMaterials[r];
                    r.materials = mats;
                }
                else
                {
                    // Apply Ghosting to non-target meshes
                    Material[] ghostMats = runtimeInstanceMaterials[r];
                    foreach (Material m in ghostMats)
                    {
                        if (m != null)
                        {
                            // URP / Standard Transparency setup
                            m.SetFloat("_Surface", 1); // 1 = Transparent
                            m.SetFloat("_Blend", 0); // Alpha blend
                            m.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
                            m.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                            m.SetInt("_ZWrite", 0);
                            m.DisableKeyword("_EMISSION");
                            m.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;

                            Color c = ghostColor;
                            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", c);
                            if (m.HasProperty("_Color")) m.SetColor("_Color", c);
                        }
                    }
                    r.materials = ghostMats;
                }
            }
        }

        public void ResetMaterials()
        {
            isGhostActive = false;
            activeTargetRenderers.Clear();

            foreach (var kvp in originalMaterials)
            {
                if (kvp.Key != null && kvp.Value != null)
                {
                    kvp.Key.sharedMaterials = kvp.Value;
                }
            }
        }
    }
}
