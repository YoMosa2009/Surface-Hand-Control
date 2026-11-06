# Gesture control research and decisions

Research date: 2026-11-05.

- Casiez, Roussel, and Vogel's One Euro filter uses a speed-adaptive cutoff to balance low-speed jitter and high-speed lag: https://direction.bordeaux.inria.fr/~roussel/publications/2012-CHI-one-euro-filter.pdf. The controller now uses a two-dimensional speed-adaptive filter, plus a short median filter. Its parameters are implementation choices and need user testing.
- Google MediaPipe's hand gesture recognizer offers predefined gestures, including Open Palm, Closed Fist, and Pointing Up; its published canned set does not include pinch: https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/GestureRecognizerOptions. Our app uses hand landmarks plus calibrated pinch distances, not that classifier. A classifier or more training data may help with ambiguous poses; no accuracy comparison was performed.
- Similar public projects describe One Euro filtering and state-machine gesture handling: https://github.com/VARSHITH707/gesture_os and https://github.com/edic-23/Air-Cursor. These are project descriptions, not independent proof of their claims. A project also describes selecting the cursor position shortly before a pinch: https://github.com/mahdidigitalx-oss/mausely. The controller uses a short lookback and briefly holds the pointer at pinch onset.
- Current swipe modes recognize palm translation while enabled, not intent or a semantic pose. They can fire on unintended motion. Color camera and experimental IR still need hands-on comparison; neither tracking accuracy nor power use is established by synthetic checks. A future user study with explicit success and false-trigger counts is needed to evaluate usability.

All processing remains local. 3D hand coordinates are model estimates, not measured IR depth.
