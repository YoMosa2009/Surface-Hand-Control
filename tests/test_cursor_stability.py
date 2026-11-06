import sys,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hand_control as h
class Fake:
 def __init__(self): self.xy=[]; self.events=[]
 def SetCursorPos(self,x,y): self.xy.append((x,y));return 1
 def GetSystemMetrics(self,n):return 1001
 def mouse_event(self,*args):self.events.append(args[0])
f=Fake();h.u=f;g=h.Gesture();g.bounds=h.centered_bounds((.5,.5),.3)
w=[(0.,0.,0.)]*21;w[17]=(.2,0.,0.);w[9]=(.2,0.,0.);w[4]=(.2,0.,0.)
def points(x,y):return [(x,y)]*21
r=random.Random(9)
for i in range(120):g.update(points(.5+r.uniform(-.001,.001),.5+r.uniform(-.001,.001)),'Pointer / drag',i*.067,w)
xs=[p[0] for p in f.xy[20:]];ys=[p[1] for p in f.xy[20:]]
assert max(xs)-min(xs)<8 and max(ys)-min(ys)<8,(min(xs),max(xs),min(ys),max(ys))
for i in range(120,180):g.update(points(.35,.5),'Pointer / drag',i*.067,w)
assert f.xy[-1][0]==1000,f.xy[-1]
for i in range(180,240):g.update(points(.65,.5),'Pointer / drag',i*.067,w)
assert f.xy[-1][0]==0,f.xy[-1]
print('Stationary synthetic jitter bounded; both horizontal edges reachable.')
