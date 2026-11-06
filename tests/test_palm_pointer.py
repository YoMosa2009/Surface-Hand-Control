import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hand_control as h
class Fake:
 def __init__(self):self.pos=[]
 def SetCursorPos(self,x,y):self.pos.append((x,y));return 1
 def GetSystemMetrics(self,n):return 1000
 def mouse_event(self,*args):pass
fake=Fake();h.u=fake;g=h.Gesture()
p=[(.5,.5)]*21; w=[(0.,0.,0.)]*21;w[17]=(.2,0,0);w[9]=(.2,0,0);w[4]=(.2,0,0)
g.update(p,'Pointer / drag',1,w);a=fake.pos[-1]
p[8]=(.5,.8);g.update(p,'Pointer / drag',1.1,w);assert fake.pos[-1]==a
print('Index finger bending does not move palm-based pointer.')
