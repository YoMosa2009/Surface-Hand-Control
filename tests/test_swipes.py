import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hand_control as h
class Fake:
 def __init__(self): self.keys=[];self.commands=[];self.pos=[]
 def keybd_event(self,k,scan,flags,extra): self.keys.append((k,flags))
 def GetForegroundWindow(self): return 123
 def ShowWindow(self,handle,cmd): self.commands.append(cmd)
 def SetCursorPos(self,x,y): self.pos.append((x,y)); return 1
 def GetSystemMetrics(self,n): return 1000
 def mouse_event(self,*args): pass
fake=Fake();h.u=fake
def points(x,y): return [(x,y)]*21
g=h.Gesture();g.update(points(.7,.5),'Tabs',10);g.update(points(.57,.5),'Tabs',10.3)
assert (9,0) in fake.keys, fake.keys
n=len(fake.keys);g.update(points(.3,.5),'Tabs',10.5);assert len(fake.keys)==n
g.reset();g.update(points(.5,.6),'Window swipes',20);g.update(points(.5,.48),'Window swipes',20.3);assert fake.commands==[3]
g.reset();g.update(points(.5,.5),'Tabs',30);g.update(points(.5,.35),'Tabs',30.3);assert len(fake.keys)==n
print('Short swipes, cooldown, window action and ignored vertical tab movement passed.')
