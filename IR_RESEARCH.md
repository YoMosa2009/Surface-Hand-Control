# Surface Laptop 3 infrared research

Research date: 2026-11-05. Sources below distinguish Microsoft's published information from local observations and unverified hypotheses.

## Confirmed by documentation

- Microsoft lists a front-facing Windows Hello face-authentication camera and a separate 720p front-facing camera for Surface Laptop 3: https://support.microsoft.com/en-us/surface/models/surface-laptop-3-specs-and-features
- Windows Hello facial authentication uses a camera configured for near-infrared imaging. Microsoft's general Windows Hello documentation describes near-IR images as less dependent on ambient lighting in its examples; this is not a guarantee of hand tracking in every lighting condition: https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/windows-hello-face-authentication
- Windows exposes IR and depth as different non-color stream types. An IR stream alone does not establish that a depth stream is available: https://learn.microsoft.com/en-us/windows-hardware/drivers/stream/uvc-camera-implementation-guide
- MediaPipe Hand Landmarker accepts RGB or RGBA input and reports 21 hand landmarks. Its documentation does not establish accuracy on this laptop's near-IR images: https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/HandLandmarker and https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/drawing_styles/hand_landmarker/HandLandmark

## Observations on this computer

The prior Surface IR Viewer README reported Surface IR Camera Front and Surface Camera Sensor Group sources at 480 × 480 and about 60 FPS. On 2026-11-05, the new bridge received a 480 × 480 infrared frame through the existing WinRT MediaFrameReader implementation. This frame is an intensity image; its dimensions and frame receipt do not prove depth capability or hand-detection accuracy. The color camera produced a 640 × 480 frame. Neither camera was tested with a hand for this hand controller.

## Design implications and unknowns

The IR stream can be selected as an experimental low-light input. Its grayscale pixels are replicated into RGB channels for the existing landmark model. This may work poorly because the model's suitability for IR images here is unverified. Its illumination strength, wavelength, field of view, useful range, camera/IR synchronization, stream availability during Windows Hello, and any accessible depth stream have not been established. Microsoft does not specify these details on the cited model page. Do not interpret brightness or MediaPipe's inferred landmark z as measured metric depth. Test recognition at normal seated distances in daylight and dim light before considering IR for default operation; compare with color under the same conditions. Concurrent RGB/IR fusion is not implemented.

## 2026-11-05 camera source enumeration

The WinRT MediaFrameSourceGroup enumeration exposed Surface IR Camera Front (Infrared), Surface Camera Sensor Group (Color and Infrared), and Surface Camera Front (Color); no Depth source was reported. This describes accessible sources at the time of the test, not a claim about every possible firmware or driver configuration. The hand landmark model's 3D coordinates are estimates from the selected image stream. RGB and IR fusion, registration, synchronization, and a measured metric depth map have not been implemented or verified.
