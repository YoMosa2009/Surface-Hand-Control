import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hand_control as app
class Fake:
    def __init__(self): self.events=[]; self.xy=[]
    def mouse_event(self,*args): self.events.append(args[0])
    def SetCursorPos(self,x,y): self.xy.append((x,y)); return 1
    def GetSystemMetrics(self,n): return 1000
fake=Fake(); app.u=fake; g=app.Gesture()
def hand(ratio,x=.5):
 p=[(x,.5)]*21; p[5]=(x-.1,.5); p[17]=(x+.1,.5); p[8]=(x,.4); p[4]=(x+ratio*.2,.4); return p
now=0
def samples(ratio,n,x=.5):
 global now
 for _ in range(n):
  now+=.067
  world=[(0.,0.,0.)]*21; world[5]=(0.,0.,0.); world[17]=(.2,0.,0.); world[0]=(0.,0.,0.); world[9]=(.2,0.,0.); world[8]=(0.,0.,0.); world[4]=(ratio*.2,0.,0.)
  g.update(hand(ratio,x),'Pointer / drag',now,world)
samples(.1,8); assert fake.events==[], 'closed hand must not start a press'
samples(1.1,8); assert g.ready
# Single noisy frame must not trigger a click.
samples(.1,1); samples(1.1,8); assert fake.events==[],fake.events
samples(.2,4); assert fake.events==[2],fake.events
start=fake.xy[-1]; samples(.2,1,x=.4); assert fake.xy[-1]==start, 'click aim should stay frozen briefly'
samples(.2,8,x=.25); assert fake.xy[-1]!=start, 'held pinch should be able to drag'
samples(1.2,8,x=.25); assert fake.events==[2,4],fake.events
samples(.2,8); assert fake.events==[2,4,2],fake.events
g.release(); assert fake.events==[2,4,2,4],fake.events
print('Open-to-arm, noisy-frame rejection, pinch, stable aim, drag and forced release passed.')

