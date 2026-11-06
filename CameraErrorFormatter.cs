namespace SurfaceIrViewer;

internal static class CameraErrorFormatter
{
    private const int AccessDenied = unchecked((int)0x80070005);
    private const int CameraReservedByAnotherApp = unchecked((int)0xA00F4243);
    private const int NoCamerasAttached = unchecked((int)0xA00F4244);

    public static string ForDisplay(Exception exception)
    {
        if (exception is UnauthorizedAccessException || exception.HResult == AccessDenied)
        {
            return $"Windows blocked camera access. In Settings > Privacy & security > Camera, enable Camera access and Let desktop apps access your camera, then retry. {exception.Message}";
        }

        if (exception.HResult == CameraReservedByAnotherApp || ContainsAny(exception.Message, "in use", "busy", "reserved"))
        {
            return $"The infrared camera appears to be busy. Close other camera or sign-in windows, then retry. {exception.Message}";
        }

        if (exception.HResult == NoCamerasAttached || ContainsAny(exception.Message, "no longer available", "not found"))
        {
            return $"The infrared camera was not found. Check Device Manager and the Surface drivers, then retry. {exception.Message}";
        }

        if (exception is NotSupportedException)
        {
            return $"The infrared camera's video format is not supported by this viewer. {exception.Message}";
        }

        return $"The infrared camera could not stream. Stop other camera apps and try again. {exception.Message}";
    }

    private static bool ContainsAny(string text, params string[] values)
    {
        return values.Any(value => text.Contains(value, StringComparison.OrdinalIgnoreCase));
    }
}
