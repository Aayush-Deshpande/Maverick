using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace DigitalTwin.Core
{
    [RequireComponent(typeof(CanvasRenderer))]
    public class ProceduralSparkline : MaskableGraphic
    {
        [Header("Sparkline Settings")]
        public Color lineColor = new Color(0.0f, 1.0f, 0.53f, 1.0f); // Bright Green
        public float lineWidth = 2.0f;
        public int maxDataPoints = 30;
        public float minValue = 0f;
        public float maxValue = 100f;

        private List<float> dataPoints = new List<float>();

        protected override void Awake()
        {
            base.Awake();
            // Initialize with default baseline points
            for (int i = 0; i < maxDataPoints; i++)
            {
                dataPoints.Add((minValue + maxValue) * 0.5f);
            }
        }

        public void AddDataPoint(float value)
        {
            dataPoints.Add(value);
            if (dataPoints.Count > maxDataPoints)
            {
                dataPoints.RemoveAt(0);
            }
            SetVerticesDirty();
        }

        public void SetRange(float min, float max)
        {
            minValue = min;
            maxValue = max;
        }

        public void SetColor(Color c)
        {
            lineColor = c;
            SetVerticesDirty();
        }

        protected override void OnPopulateMesh(VertexHelper vh)
        {
            vh.Clear();

            if (dataPoints.Count < 2) return;

            Rect rect = rectTransform.rect;
            float width = rect.width;
            float height = rect.height;
            float xStep = width / (dataPoints.Count - 1);

            List<Vector2> points = new List<Vector2>();
            for (int i = 0; i < dataPoints.Count; i++)
            {
                float normalizedY = Mathf.InverseLerp(minValue, maxValue, dataPoints[i]);
                float px = rect.xMin + i * xStep;
                float py = rect.yMin + normalizedY * height;
                points.Add(new Vector2(px, py));
            }

            // Draw line segments
            for (int i = 0; i < points.Count - 1; i++)
            {
                Vector2 p1 = points[i];
                Vector2 p2 = points[i + 1];

                Vector2 dir = (p2 - p1).normalized;
                Vector2 normal = new Vector2(-dir.y, dir.x) * (lineWidth * 0.5f);

                UIVertex v1 = UIVertex.simpleVert;
                v1.color = lineColor;
                v1.position = p1 + normal;

                UIVertex v2 = UIVertex.simpleVert;
                v2.color = lineColor;
                v2.position = p2 + normal;

                UIVertex v3 = UIVertex.simpleVert;
                v3.color = lineColor;
                v3.position = p2 - normal;

                UIVertex v4 = UIVertex.simpleVert;
                v4.color = lineColor;
                v4.position = p1 - normal;

                int vIndex = vh.currentVertCount;
                vh.AddVert(v1);
                vh.AddVert(v2);
                vh.AddVert(v3);
                vh.AddVert(v4);

                vh.AddTriangle(vIndex, vIndex + 1, vIndex + 2);
                vh.AddTriangle(vIndex + 2, vIndex + 3, vIndex);
            }
        }
    }
}
