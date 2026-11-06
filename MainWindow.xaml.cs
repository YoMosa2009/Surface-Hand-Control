using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace SurfaceIrViewer;
public partial class MainWindow : Window
{
    private readonly IrCameraService camera = new();
    private readonly MotionTracker tracker = new();
    private WriteableBitmap? image;
    private HwndSource? source;
    private bool running, enabled, closing, uiPending;
    private long lastAction;
    private const int HotkeyId = 7231;
    public MainWindow() { InitializeComponent(); camera.FrameArrived += Frame; camera.StreamingFailed += Failed; Loaded += SetupHotkey; }
    private void SetupHotkey(object sender, RoutedEventArgs e) {
        source = HwndSource.FromHwnd(new WindowInteropHelper(this).Handle); source.AddHook(Hook);
        if (!RegisterHotKey(source.Handle, HotkeyId, 0x4000, 0x77)) { Status.Text = "F8 unavailable; close the conflicting app and reopen this app."; StartButton.IsEnabled = false; }
    }
    private IntPtr Hook(IntPtr hwnd, int msg, IntPtr w, IntPtr l, ref bool handled) {
        if (msg == 0x0312 && w.ToInt32() == HotkeyId) { enabled = running && !enabled; tracker.Reset(); Status.Text = enabled ? "Controls ENABLED — press F8 to pause." : "Controls paused."; handled = true; } return IntPtr.Zero;
    }
    private async void StartClick(object sender, RoutedEventArgs e) {
        StartButton.IsEnabled = false;
        try { var devices = await camera.GetCamerasAsync(); if (devices.Count == 0) throw new InvalidOperationException("No infrared camera found."); await camera.StartAsync(devices[0].GroupId, devices[0].SourceId); running = true; Status.Text = "IR camera running. Controls paused; press F8 to enable."; }
        catch (Exception ex) { Status.Text = "Camera error: " + ex.Message; StartButton.IsEnabled = true; }
    }
    private async void StopClick(object sender, RoutedEventArgs e) { enabled = false; running = false; tracker.Reset(); await camera.StopAsync(); Status.Text = "Camera stopped. Controls paused."; StartButton.IsEnabled = true; }
    private void Failed(object? sender, Exception ex) { Dispatcher.BeginInvoke(() => { enabled = false; running = false; Status.Text = "Camera stopped: " + ex.Message; }); }
    private void Frame(object? sender, IrFrameData f) {
        var direction = tracker.Process(f);
        if (uiPending) return;
        uiPending = true;
        Dispatcher.BeginInvoke(() => { try {
            if (!running || closing) return;
            if (image == null || image.PixelWidth != f.Width || image.PixelHeight != f.Height) { image = new WriteableBitmap(f.Width, f.Height, 96, 96, PixelFormats.Bgra32, null); Preview.Source = image; }
            image.WritePixels(new Int32Rect(0,0,f.Width,f.Height), f.BgraPixels, f.Stride, 0);
            if (direction != null) { Gesture.Text = "Motion: " + direction + (enabled ? " (controls enabled)" : " (preview only)"); if (enabled && Environment.TickCount64 - lastAction > 1800) { lastAction = Environment.TickCount64; Execute(direction); } }
        } finally { uiPending = false; } });
    }
    private void Execute(string direction) {
        var foreground = GetForegroundWindow(); if (foreground == IntPtr.Zero || foreground == new WindowInteropHelper(this).Handle) return;
        if (Mode.SelectedIndex == 1) { if (direction == "left") Keys(0x11, 0x10, 0x09); else if (direction == "right") Keys(0x11, 0x09); }
        else { if (direction == "left") Keys(0x5B, 0x25); else if (direction == "right") Keys(0x5B, 0x27); else if (direction == "up") ShowWindow(foreground, 3); else if (direction == "down") ShowWindow(foreground, 6); }
    }
    private static void Keys(params byte[] keys) { foreach(var k in keys) keybd_event(k,0,0,UIntPtr.Zero); for(int i=keys.Length-1;i>=0;i--) keybd_event(keys[i],0,2,UIntPtr.Zero); }
    private async void OnClosing(object? sender, System.ComponentModel.CancelEventArgs e) { if (closing) return; e.Cancel = true; closing = true; enabled = false; if (source != null) { UnregisterHotKey(source.Handle, HotkeyId); source.RemoveHook(Hook); } await camera.DisposeAsync(); Close(); }
    [DllImport("user32.dll")] static extern bool RegisterHotKey(IntPtr h, int id, uint modifiers, uint key);
    [DllImport("user32.dll")] static extern bool UnregisterHotKey(IntPtr h, int id);
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int command);
    [DllImport("user32.dll")] static extern void keybd_event(byte key, byte scan, uint flags, UIntPtr extra);
}
