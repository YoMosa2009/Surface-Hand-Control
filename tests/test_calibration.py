import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hand_control as app
class Fake:
    def __init__(self): self.xy=[]
    def mouse_event(self,*args): pass
    def SetCursorPos(self,x,y): self.xy.append((x,y)); return 1
    def GetSystemMetrics(self,n): return 1001
fake=Fake(); app.u=fake
g=app.Gesture(); g.bounds=(.3,.7,.2,.5)
def hand(x,y):
 p=[(1-x,y)]*21; p[8]=(1-x,y); p[4]=(.2,.2); return p
world=[(0.,0.,0.)]*21; world[17]=(.2,0.,0.); world[9]=(.2,0.,0.); world[4]=(.2,0.,0.)
g.update(hand(.3,.2),'Pointer / drag',1,world)
assert fake.xy[-1]==(0,0),fake.xy
g.reset();g.update(hand(.7,.5),'Pointer / drag',2,world)
assert fake.xy[-1]==(1000,1000),fake.xy
samples=[(.3+.4*(i%10)/9,.2+.3*(i%10)/9) for i in range(100)]
assert app.calculate_bounds(samples) is not None
assert app.calculate_bounds([(.5,.5)]*100) is None
assert app.calculate_bounds([]) is None
g.release();assert g.bounds==(.3,.7,.2,.5)
print('Calibration bounds, corner mapping, invalid samples, and persistence across release passed.')
