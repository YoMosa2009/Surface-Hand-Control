using SurfaceIrViewer;
using Windows.Media.Capture.Frames;
using System.Threading.Channels;
if (args.Contains("--list")) {
 foreach (var group in await MediaFrameSourceGroup.FindAllAsync()) {
  foreach (var item in group.SourceInfos) Console.WriteLine($"{group.DisplayName} | {item.SourceKind} | {item.MediaStreamType}");
 }
 return;
}
var channel = Channel.CreateBounded<IrFrameData>(new BoundedChannelOptions(1) { FullMode = BoundedChannelFullMode.DropOldest, SingleReader = true });
await using var camera = new IrCameraService();
camera.FrameArrived += (_, f) => channel.Writer.TryWrite(f);
camera.StreamingFailed += (_, e) => channel.Writer.TryComplete(e);
try {
 var devices = await camera.GetCamerasAsync();
 if (devices.Count == 0) throw new Exception("No infrared camera found.");
 await camera.StartAsync(devices[0].GroupId, devices[0].SourceId);
 using var stream = Console.OpenStandardOutput();
 await foreach (var frame in channel.Reader.ReadAllAsync()) {
  var header = new byte[12]; BitConverter.GetBytes(frame.Width).CopyTo(header,0); BitConverter.GetBytes(frame.Height).CopyTo(header,4); BitConverter.GetBytes(frame.Stride).CopyTo(header,8);
  await stream.WriteAsync(header); await stream.WriteAsync(frame.BgraPixels); await stream.FlushAsync();
 }
} catch (Exception e) { Console.Error.WriteLine(e.Message); Environment.ExitCode=1; }
