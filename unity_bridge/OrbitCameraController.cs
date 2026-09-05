using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace DigitalTwin.Core
{
    public class OrbitCameraController : MonoBehaviour
    {
        [Header("Orbit Targets")]
        public Transform pivotTransform;
        public Camera targetCamera;

        [Header("Orbit Parameters")]
        public float defaultDistance = 3.2f;
        public float minDistance = 0.8f;
        public float maxDistance = 8.0f;
        public float orbitSpeed = 12.0f; // degrees/sec in idle mode
        public float mouseSensitivityX = 12.0f;
        public float mouseSensitivityY = 10.0f;
        public float zoomSensitivity = 0.5f;

        [Header("Limits & Damping")]
        public float minPitch = -10.0f;
        public float maxPitch = 80.0f;
        public float damping = 8.0f;

        // Current State
        public bool isAutoRevolving = true;
        private float currentYaw = 35.0f;
        private float currentPitch = 22.0f;
        private float targetYaw = 35.0f;
        private float targetPitch = 22.0f;
        private float currentDistance = 3.2f;
        private float targetDistance = 3.2f;
        private Vector3 currentPivotPos = Vector3.zero;
        private Vector3 targetPivotPos = Vector3.zero;

        // Focus Transition State
        private bool isTransitioning = false;
        private float transitionProgress = 0f;
        private float transitionDuration = 1.0f;
        private Vector3 startPivotPos;
        private float startYaw, startPitch, startDist;
        private float focusYaw, focusPitch, focusDist;

        void Awake()
        {
            if (targetCamera == null) targetCamera = Camera.main;
            if (pivotTransform == null)
            {
                GameObject p = new GameObject("CameraPivot");
                pivotTransform = p.transform;
            }

            currentDistance = defaultDistance;
            targetDistance = defaultDistance;
            targetPivotPos = pivotTransform.position;
            currentPivotPos = pivotTransform.position;
        }

        void Update()
        {
            HandleInput();
            UpdateCameraTransform();
        }

        void HandleInput()
        {
            bool isLeftMouseDown = false;
            Vector2 mouseDelta = Vector2.zero;
            float scrollDelta = 0f;
            bool resetPressed = false;

#if ENABLE_INPUT_SYSTEM
            if (Mouse.current != null)
            {
                isLeftMouseDown = Mouse.current.leftButton.isPressed;
                mouseDelta = Mouse.current.delta.ReadValue() * 0.1f;
                scrollDelta = Mouse.current.scroll.ReadValue().y * 0.005f;
            }
            if (Keyboard.current != null)
            {
                resetPressed = Keyboard.current.rKey.wasPressedThisFrame || Keyboard.current.escapeKey.wasPressedThisFrame;
            }
#else
            isLeftMouseDown = Input.GetMouseButton(0);
            mouseDelta = new Vector2(Input.GetAxis("Mouse X"), Input.GetAxis("Mouse Y"));
            scrollDelta = Input.GetAxis("Mouse ScrollWheel");
            resetPressed = Input.GetKeyDown(KeyCode.R) || Input.GetKeyDown(KeyCode.Escape);
#endif

            if (resetPressed)
            {
                ResetView();
            }

            if (isLeftMouseDown)
            {
                isAutoRevolving = false;
                targetYaw += mouseDelta.x * mouseSensitivityX;
                targetPitch -= mouseDelta.y * mouseSensitivityY;
                targetPitch = Mathf.Clamp(targetPitch, minPitch, maxPitch);
            }
            else if (isAutoRevolving && !isTransitioning)
            {
                targetYaw += orbitSpeed * Time.deltaTime;
            }

            if (Mathf.Abs(scrollDelta) > 0.001f)
            {
                targetDistance -= scrollDelta * zoomSensitivity;
                targetDistance = Mathf.Clamp(targetDistance, minDistance, maxDistance);
            }
        }

        void UpdateCameraTransform()
        {
            if (isTransitioning)
            {
                transitionProgress += Time.deltaTime / transitionDuration;
                float t = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(transitionProgress));

                currentPivotPos = Vector3.Lerp(startPivotPos, targetPivotPos, t);
                currentYaw = Mathf.LerpAngle(startYaw, focusYaw, t);
                currentPitch = Mathf.Lerp(startPitch, focusPitch, t);
                currentDistance = Mathf.Lerp(startDist, focusDist, t);

                if (transitionProgress >= 1f)
                {
                    isTransitioning = false;
                    targetYaw = focusYaw;
                    targetPitch = focusPitch;
                    targetDistance = focusDist;
                }
            }
            else
            {
                currentYaw = Mathf.LerpAngle(currentYaw, targetYaw, Time.deltaTime * damping);
                currentPitch = Mathf.Lerp(currentPitch, targetPitch, Time.deltaTime * damping);
                currentDistance = Mathf.Lerp(currentDistance, targetDistance, Time.deltaTime * damping);
                currentPivotPos = Vector3.Lerp(currentPivotPos, targetPivotPos, Time.deltaTime * damping);
            }

            pivotTransform.position = currentPivotPos;

            Quaternion rotation = Quaternion.Euler(currentPitch, currentYaw, 0f);
            Vector3 offset = rotation * new Vector3(0f, 0f, -currentDistance);

            targetCamera.transform.position = currentPivotPos + offset;
            targetCamera.transform.LookAt(currentPivotPos);
        }

        public void FocusOnComponent(Vector3 targetWorldPos, float distance = 2.0f, float desiredYaw = 40f, float desiredPitch = 25f)
        {
            isAutoRevolving = false;
            isTransitioning = true;
            transitionProgress = 0f;
            transitionDuration = 1.1f;

            startPivotPos = currentPivotPos;
            startYaw = currentYaw;
            startPitch = currentPitch;
            startDist = currentDistance;

            targetPivotPos = targetWorldPos;
            focusYaw = desiredYaw;
            focusPitch = desiredPitch;
            focusDist = distance;
        }

        public void ResetView()
        {
            isTransitioning = true;
            transitionProgress = 0f;
            transitionDuration = 1.0f;

            startPivotPos = currentPivotPos;
            startYaw = currentYaw;
            startPitch = currentPitch;
            startDist = currentDistance;

            targetPivotPos = Vector3.zero;
            focusYaw = currentYaw;
            focusPitch = 22.0f;
            focusDist = defaultDistance;

            isAutoRevolving = true;
        }
    }
}
