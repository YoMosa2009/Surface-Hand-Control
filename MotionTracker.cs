namespace SurfaceIrViewer;
// Sparse frame differencing. It detects moving image regions, not hands or pose.
public sealed class MotionTracker
{
    private readonly object gate = new();
    private byte[]? previous;
    private double startX, startY;
    private long startTime, lastMotion;
    private bool tracking;
    public void Reset() { lock(gate) { previous = null; tracking = false; } }
    public string? Process(IrFrameData f) { lock(gate) {
        const int step = 8;
        int cols = (f.Width + step - 1) / step, rows = (f.Height + step - 1) / step;
        var next = new byte[cols * rows]; int count=0; double xsum=0, ysum=0;
        for(int y=0; y<rows; y++) for(int x=0; x<cols; x++) {
            int i=y*cols+x; byte value=f.BgraPixels[(y*step)*f.Stride+x*step*4]; next[i]=value;
            if(previous != null && previous.Length == next.Length && Math.Abs(value-previous[i]) >= 30) { count++; xsum += x; ysum += y; }
        }
        previous=next; long now=Environment.TickCount64;
        if (count < 20 || count > cols*rows*0.4) { if(now-lastMotion > 350) tracking=false; return null; }
        double px=xsum/count/cols, py=ysum/count/rows;
        if(!tracking || now-startTime > 1200) { tracking=true; startX=px; startY=py; startTime=now; lastMotion=now; return null; }
        lastMotion=now; double dx=px-startX, dy=py-startY;
        if(Math.Max(Math.Abs(dx), Math.Abs(dy)) < 0.22 || now-startTime < 100) return null;
        tracking=false;
        // Preview is the raw camera image; horizontal direction may need adjustment per device.
        return Math.Abs(dx)>Math.Abs(dy) ? (dx<0 ? "left" : "right") : (dy<0 ? "up" : "down");
    } }
}
