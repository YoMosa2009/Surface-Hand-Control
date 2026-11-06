namespace SurfaceIrViewer;

public sealed class IrFrameData
{
    public IrFrameData(byte[] bgraPixels, int width, int height, int stride)
    {
        BgraPixels = bgraPixels;
        Width = width;
        Height = height;
        Stride = stride;
    }

    public byte[] BgraPixels { get; }
    public int Width { get; }
    public int Height { get; }
    public int Stride { get; }
}
