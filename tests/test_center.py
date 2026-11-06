import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hand_control import centered_bounds
for px,py in [(.5,.5),(.65,.4),(.3,.7)]:
 l,r,t,b=centered_bounds((px,py),.3)
 assert abs(((1-px)-l)/(r-l)-.5)<1e-9
 assert abs((py-t)/(b-t)-.5)<1e-9
 assert abs(r-l-.3)<1e-9 and abs(b-t-.24)<1e-9
print('Auto center and small movement mapping passed for several starting positions.')
