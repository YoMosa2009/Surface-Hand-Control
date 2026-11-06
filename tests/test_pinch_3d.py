import sys, math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hand_control import pinch_measure,pinch_calibration,valid_pinch_thresholds,Gesture
world=[(0.,0.,0.)]*21
world[5]=(-.04,0.,0.);world[17]=(.04,0.,0.);world[0]=(0.,-.04,0.);world[9]=(0.,.04,0.);world[4]=(.02,.04,0.);world[8]=(.04,.04,0.)
original=pinch_measure(world)
for angle in (0,.5,1,1.5):
 rotated=[(x*math.cos(angle)+z*math.sin(angle),y,-x*math.sin(angle)+z*math.cos(angle)) for x,y,z in world]
 assert abs(pinch_measure(rotated)-original)<1e-8
bounds=pinch_calibration([1.0]*15,[.2]*15)
assert valid_pinch_thresholds(bounds) and .2<bounds[0]<bounds[1]<1
assert pinch_calibration([.5]*15,[.49]*15) is None
assert pinch_calibration([1]*2,[.2]*15) is None
assert pinch_measure(None) is None
class Fake:
 def __init__(self):self.events=[]
 def mouse_event(self,*args):self.events.append(args[0])
import hand_control as h
fake=Fake();h.u=fake;g=Gesture();g.down=True
g.update([(0.,0.)]*21,'Pointer / drag',1,None)
assert fake.events==[4] and not g.down
print('3D rotation invariance, calibration separation, invalid input, and loss release passed.')
