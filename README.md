# Surface Hand Control

An experimental, local Windows hand-gesture controller. It uses a webcam and MediaPipe hand landmarks to move the pointer, pinch to click or drag, switch tabs, and snap or minimize windows. A Surface infrared camera can be selected experimentally. The goal is touch-free desktop interaction; it is **not yet a reliable replacement for a mouse**.

## Requirements

- Windows x64 and a working webcam; Python 3.12 x64 with the `py` launcher and Tkinter.
- Internet access for initial setup: Python packages and Google's hand-landmark model are downloaded. During use, the application processes video locally.
- Optional infrared input: an IR camera exposed to Windows as an infrared MediaFrameSource, plus .NET SDK 10 to build the bridge. The IR path has only been exercised on a Surface Laptop 3; other devices may not work.

## Install and run

1. Clone this repository or download and extract it.
2. Double-click **Setup.cmd**. It creates a project-local Python environment, installs the dependencies, verifies the downloaded model's SHA-256, and builds the IR bridge if the .NET SDK is installed. If the IR build fails, the color webcam can still be used.
3. Double-click **Start Hand Control.cmd**. Select **Color webcam** and click **Start**.
4. Hold your hand in view, select **Pointer / drag**, and press **F8** or click **Enable controls**. Auto center maps the palm position at activation to the center of the primary screen. Move the palm to point; pinch thumb and index finger briefly to press, and open them to release. Hold the pinch and move deliberately to drag.

The app starts paused. F8 pauses and releases a held press, as do Stop, closing, or lost tracking. Try it in a disposable window before relying on it. Camera access must be enabled in Windows; close other apps using the camera if necessary. If F8 is already registered, close the conflicting program. The Surface keyboard may require Fn+F8 depending on its function-key setting.

## Modes and settings

- **Pointer / drag:** palm movement controls the cursor; pinch to click or drag. The preview displays the estimated skeleton; the adjacent 3D pose is a model estimate, not measured depth.
- **Tabs:** a left or right hand swipe sends previous or next tab shortcuts to the focused application.
- **Window swipes:** left/right sends Windows snap shortcuts; up maximizes and down minimizes the focused window.

Swipe modes detect hand movement, not intent; unintended movement can trigger commands. They have a cooldown, and switching modes pauses control. Focus the intended application before enabling. Controls may not reach elevated apps when this app runs without elevation.

**Hand movement** adjusts how far your palm must travel; click **Recenter** after changing it. **Smoothing** trades response speed for stability; **Click sensitivity** adjusts the pinch threshold. For a personalized pinch, click **Calibrate pinch gesture**, keep thumb and index apart for four seconds, then follow the prompt to capture the pinched pose for four seconds. Keep the hand in view. **Calibrate comfortable hand area** provides an alternative to auto center. Settings and calibration files stay local and are excluded from Git.

## IR and privacy

Infrared is an alternative image stream, not simultaneous RGB/IR fusion. On the tested Surface Laptop 3, Windows exposed IR and color sources but no depth stream. The model's 3D coordinates are inferred; IR brightness is not a depth map. The model has not been validated for IR images and tracking may be poor. See [IR research](IR_RESEARCH.md) and [gesture research](GESTURE_RESEARCH.md).

Frames are processed in memory on the device; the application does not intentionally save or transmit camera frames. Setup downloads dependencies and a model. No tracking accuracy, performance, or battery-life guarantee is made; hand occlusion, lighting, camera position, and Windows permissions matter.

## Development

Run tests after setup from PowerShell:

```powershell
Get-ChildItem tests/test_*.py | ForEach-Object { .\.venv\Scripts\python.exe $_.FullName }
```

To build the IR bridge separately: `dotnet build irbridge/irbridge.csproj -c Release`. Run `irbridge/bin/Release/net10.0-windows10.0.19041.0/irbridge.exe --list` to list accessible camera source types. Hardware tests are still needed: synthetic tests do not establish gesture accuracy, usability, CPU load, or reliability on another laptop. Contributions and reproducible issue reports are welcome; do not include camera images or personal calibration files unless you intend to share them.

The project code is MIT licensed; third-party packages and Google's model have their own terms. The model is downloaded from Google's official hosting at setup and is not committed to the repository.
