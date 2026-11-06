import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hand_control import WorldHandFilter
f=WorldHandFilter();a=[(0.,0.,0.)]*21;b=[(1.,1.,1.)]*21
assert f.update(a,1)==a
out=f.update(b,1.07); assert 0<out[0][0]<1
assert f.update(None,1.1) is None
assert f.update(b,1.2)==b
assert f.update([(float('nan'),0,0)]*21,1.3) is None
assert f.update(a,2)==a
print('Temporal joint filter, loss, invalid input and reacquisition passed.')
