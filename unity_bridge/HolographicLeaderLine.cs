using UnityEngine;
using UnityEngine.UI;

namespace DigitalTwin.Core
{
    [RequireComponent(typeof(CanvasRenderer))]
    public class HolographicLeaderLine : MaskableGraphic
    {
        public Camera targetCamera;
        public Canvas rootCanvas;
        public Transform targetWorldTransform;
        public RectTransform targetUIPanel;
        public Color lineColor = new Color(1.0f, 0.15f, 0.25f, 0.9f);
        public float lineWidth = 2.0f;
        public float reticleRadius = 14.0f;

        private float pulseTimer = 0f;
        private bool isTracking = false;

        protected override void Awake()
        {
            base.Awake();
            if (targetCamera == null) targetCamera = Camera.main;
            if (rootCanvas == null) rootCanvas = GetComponentInParent<Canvas>();
        }

        public void SetTarget(Transform worldTarget, RectTransform uiCard)
        {
            targetWorldTransform = worldTarget;
            targetUIPanel = uiCard;
            isTracking = (worldTarget != null && uiCard != null);
            SetVerticesDirty();
        }

        public void ClearTarget()
        {
            isTracking = false;
            targetWorldTransform = null;
            targetUIPanel = null;
            SetVerticesDirty();
        }

        void Update()
        {
            if (isTracking)
            {
                pulseTimer += Time.deltaTime * 3f;
                SetVerticesDirty();
            }
        }

        protected override void OnPopulateMesh(VertexHelper vh)
        {
            vh.Clear();

            if (!isTracking || targetWorldTransform == null || targetUIPanel == null || targetCamera == null || rootCanvas == null)
            {
                return;
            }

            // Convert World Target to Screen Space
            Vector3 screenPos = targetCamera.WorldToScreenPoint(targetWorldTransform.position);
            if (screenPos.z < 0) return; // Behind camera

            Vector2 localPointTarget;
            RectTransformUtility.ScreenPointToLocalPointInRectangle(rectTransform, screenPos, targetCamera, out localPointTarget);

            // Convert UI Card Anchor to Screen Space
            Vector3[] corners = new Vector3[4];
            targetUIPanel.GetWorldCorners(corners);
            Vector3 cardAnchorScreen = targetCamera.WorldToScreenPoint(corners[0]); // Bottom left or right
            Vector2 localPointCard;
            RectTransformUtility.ScreenPointToLocalPointInRectangle(rectTransform, cardAnchorScreen, targetCamera, out localPointCard);

            // Draw Pulsing Circle Reticle on 3D Target
            float currentRadius = reticleRadius + Mathf.Sin(pulseTimer) * 4f;
            DrawCircle(vh, localPointTarget, currentRadius, 2f, lineColor);
            DrawFilledDot(vh, localPointTarget, 5f, Color.white);

            // Draw Elbow Leader Line
            Vector2 midPoint = new Vector2((localPointTarget.x + localPointCard.x) * 0.5f, localPointTarget.y);
            DrawLineSegment(vh, localPointTarget, midPoint, lineWidth, lineColor);
            DrawLineSegment(vh, midPoint, localPointCard, lineWidth, lineColor);
        }

        void DrawLineSegment(VertexHelper vh, Vector2 p1, Vector2 p2, float width, Color c)
        {
            Vector2 dir = (p2 - p1).normalized;
            Vector2 normal = new Vector2(-dir.y, dir.x) * (width * 0.5f);

            UIVertex v1 = UIVertex.simpleVert; v1.color = c; v1.position = p1 + normal;
            UIVertex v2 = UIVertex.simpleVert; v2.color = c; v2.position = p2 + normal;
            UIVertex v3 = UIVertex.simpleVert; v3.color = c; v3.position = p2 - normal;
            UIVertex v4 = UIVertex.simpleVert; v4.color = c; v4.position = p1 - normal;

            int vIndex = vh.currentVertCount;
            vh.AddVert(v1); vh.AddVert(v2); vh.AddVert(v3); vh.AddVert(v4);
            vh.AddTriangle(vIndex, vIndex + 1, vIndex + 2);
            vh.AddTriangle(vIndex + 2, vIndex + 3, vIndex);
        }

        void DrawCircle(VertexHelper vh, Vector2 center, float radius, float width, Color c)
        {
            int segments = 24;
            float angleStep = 360f / segments;
            for (int i = 0; i < segments; i++)
            {
                float a1 = i * angleStep * Mathf.Deg2Rad;
                float a2 = (i + 1) * angleStep * Mathf.Deg2Rad;
                Vector2 p1 = center + new Vector2(Mathf.Cos(a1), Mathf.Sin(a1)) * radius;
                Vector2 p2 = center + new Vector2(Mathf.Cos(a2), Mathf.Sin(a2)) * radius;
                DrawLineSegment(vh, p1, p2, width, c);
            }
        }

        void DrawFilledDot(VertexHelper vh, Vector2 center, float radius, Color c)
        {
            int segments = 16;
            float angleStep = 360f / segments;
            int centerIdx = vh.currentVertCount;
            UIVertex cv = UIVertex.simpleVert; cv.color = c; cv.position = center;
            vh.AddVert(cv);

            for (int i = 0; i <= segments; i++)
            {
                float a = i * angleStep * Mathf.Deg2Rad;
                Vector2 p = center + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * radius;
                UIVertex pv = UIVertex.simpleVert; pv.color = c; pv.position = p;
                vh.AddVert(pv);
            }

            for (int i = 1; i <= segments; i++)
            {
                vh.AddTriangle(centerIdx, centerIdx + i, centerIdx + i + 1);
            }
        }
    }
}
