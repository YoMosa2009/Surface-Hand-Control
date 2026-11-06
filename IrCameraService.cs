using Windows.Graphics.Imaging;
using Windows.Media.Capture;
using Windows.Media.Capture.Frames;
using Windows.Media.MediaProperties;
using Windows.Storage.Streams;

namespace SurfaceIrViewer;

public sealed class IrCameraService : IAsyncDisposable
{
    private readonly SemaphoreSlim _lifecycleGate = new(1, 1);
    private readonly object _sessionSync = new();
    private MediaCapture? _capture;
    private MediaFrameReader? _reader;
    private bool _readerStarted;
    private bool _isStreaming;
    private bool _disposed;
    private int _sessionVersion;
    private long _lastProcessedTick;

    public event EventHandler<IrFrameData>? FrameArrived;
    public event EventHandler<Exception>? StreamingFailed;

    public async Task<IReadOnlyList<IrCameraInfo>> GetCamerasAsync(CancellationToken cancellationToken = default)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        var groups = await MediaFrameSourceGroup.FindAllAsync().AsTask(cancellationToken);
        return SelectInfraredCameras(groups);
    }

    public async Task<IrCameraInfo> StartAsync(
        string groupId,
        string sourceId,
        CancellationToken cancellationToken = default)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        await _lifecycleGate.WaitAsync(cancellationToken);
        try
        {
            await StopCoreAsync();
            cancellationToken.ThrowIfCancellationRequested();

            var groups = await MediaFrameSourceGroup.FindAllAsync().AsTask(cancellationToken);
            var camera = SelectInfraredCameras(groups)
                .FirstOrDefault(item => item.GroupId == groupId && item.SourceId == sourceId)
                ?? throw new InvalidOperationException("The selected infrared camera is no longer available.");
            var group = groups.Single(item => item.Id == groupId);
            var capture = new MediaCapture();
            _capture = capture;

            try
            {
                var settings = new MediaCaptureInitializationSettings
                {
                    SourceGroup = group,
                    StreamingCaptureMode = StreamingCaptureMode.Video,
                    SharingMode = MediaCaptureSharingMode.SharedReadOnly,
                    MemoryPreference = MediaCaptureMemoryPreference.Cpu
                };
                await capture.InitializeAsync(settings).AsTask(cancellationToken);

                var source = capture.FrameSources.Values.Single(
                    item => item.Info.Id == sourceId && item.Info.SourceKind == MediaFrameSourceKind.Infrared);
                var reader = await capture.CreateFrameReaderAsync(
                    source,
                    MediaEncodingSubtypes.Bgra8).AsTask(cancellationToken);
                reader.AcquisitionMode = MediaFrameReaderAcquisitionMode.Realtime;

                lock (_sessionSync)
                {
                    _reader = reader;
                    _sessionVersion++;
                    _isStreaming = true;
                }
                reader.FrameArrived += OnFrameArrived;

                var status = await reader.StartAsync().AsTask(cancellationToken);
                ThrowForStartFailure(status);
                _readerStarted = true;
                return camera;
            }
            catch
            {
                await StopCoreAsync();
                throw;
            }
        }
        finally
        {
            _lifecycleGate.Release();
        }
    }

    public async Task StopAsync()
    {
        if (_disposed)
        {
            return;
        }

        await _lifecycleGate.WaitAsync();
        try
        {
            await StopCoreAsync();
        }
        finally
        {
            _lifecycleGate.Release();
        }
    }

    public async ValueTask DisposeAsync()
    {
        if (_disposed)
        {
            return;
        }

        await _lifecycleGate.WaitAsync();
        try
        {
            await StopCoreAsync();
            _disposed = true;
        }
        finally
        {
            _lifecycleGate.Release();
        }

        _lifecycleGate.Dispose();
    }

    private static IReadOnlyList<IrCameraInfo> SelectInfraredCameras(IReadOnlyList<MediaFrameSourceGroup> groups)
    {
        return groups
            .SelectMany(group => group.SourceInfos
                .Where(source => source.SourceKind == MediaFrameSourceKind.Infrared)
                .Select(source => new IrCameraInfo(group.Id, source.Id, group.DisplayName)))
            .OrderByDescending(camera => camera.DisplayName.Contains("Surface IR", StringComparison.OrdinalIgnoreCase))
            .ThenBy(camera => camera.DisplayName, StringComparer.CurrentCultureIgnoreCase)
            .ToArray();
    }

    private static void ThrowForStartFailure(MediaFrameReaderStartStatus status)
    {
        if (status == MediaFrameReaderStartStatus.Success)
        {
            return;
        }

        throw status switch
        {
            MediaFrameReaderStartStatus.OutputFormatNotSupported =>
                new NotSupportedException("The infrared camera cannot provide a readable BGRA8 stream."),
            MediaFrameReaderStartStatus.DeviceNotAvailable or MediaFrameReaderStartStatus.ExclusiveControlNotAvailable =>
                new InvalidOperationException("The infrared camera is unavailable or busy in another app."),
            _ => new InvalidOperationException($"The infrared camera could not start: {status}.")
        };
    }

    private void OnFrameArrived(MediaFrameReader sender, MediaFrameArrivedEventArgs args)
    {
        int version;
        lock (_sessionSync)
        {
            if (!_isStreaming || !ReferenceEquals(sender, _reader))
            {
                return;
            }
            version = _sessionVersion;
        }

        var now = Environment.TickCount64;
        var last = Interlocked.Read(ref _lastProcessedTick);
        if (now - last < 66 || Interlocked.CompareExchange(ref _lastProcessedTick, now, last) != last) return;

        MediaFrameReference? frame = null;
        SoftwareBitmap? converted = null;

        try
        {
            frame = sender.TryAcquireLatestFrame();
            var bitmap = frame?.VideoMediaFrame.SoftwareBitmap;
            if (bitmap is null)
            {
                return;
            }

            var readable = bitmap;
            if (bitmap.BitmapPixelFormat != BitmapPixelFormat.Bgra8 || bitmap.BitmapAlphaMode != BitmapAlphaMode.Ignore)
            {
                converted = SoftwareBitmap.Convert(bitmap, BitmapPixelFormat.Bgra8, BitmapAlphaMode.Ignore);
                readable = converted;
            }

            var width = readable.PixelWidth;
            var height = readable.PixelHeight;
            var stride = checked(width * 4);
            var pixels = new byte[checked(stride * height)];
            var buffer = new Windows.Storage.Streams.Buffer((uint)pixels.Length);
            readable.CopyToBuffer(buffer);
            using var dataReader = DataReader.FromBuffer(buffer);
            dataReader.ReadBytes(pixels);

            lock (_sessionSync)
            {
                if (_isStreaming && version == _sessionVersion && ReferenceEquals(sender, _reader))
                {
                    FrameArrived?.Invoke(this, new IrFrameData(pixels, width, height, stride));
                }
            }
        }
        catch (Exception exception)
        {
            lock (_sessionSync)
            {
                if (_isStreaming && version == _sessionVersion && ReferenceEquals(sender, _reader))
                {
                    _isStreaming = false;
                    StreamingFailed?.Invoke(this, exception);
                }
            }
        }
        finally
        {
            converted?.Dispose();
            frame?.Dispose();
        }
    }

    private async Task StopCoreAsync()
    {
        MediaFrameReader? reader;
        lock (_sessionSync)
        {
            _isStreaming = false;
            _sessionVersion++;
            reader = _reader;
            _reader = null;
        }
        if (reader is not null)
        {
            reader.FrameArrived -= OnFrameArrived;
            try
            {
                if (_readerStarted)
                {
                    await reader.StopAsync();
                }
            }
            finally
            {
                reader.Dispose();
                _readerStarted = false;
                _capture?.Dispose();
                _capture = null;
            }
        }
        else
        {
            _capture?.Dispose();
            _capture = null;
        }
    }
}


