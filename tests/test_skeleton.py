import sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import hand_control as h
p=np.zeros((240,320,3),dtype=np.uint8); pts=[(.5,.5)]*21
p=h.draw_hand_preview(p,pts); assert p.sum()>0
w=[(0.,0.,0.)]*21
for b,j,t in ((5,6,8),(9,10,12),(13,14,16),(17,18,20)):
 w[b]=(0.,0.,0.);w[j]=(0.,1.,0.);w[t]=(0.,2.,0.)
assert h.finger_states(w)==('straight',)*4
w[8]=(1.,1.,0.)
assert h.finger_states(w)[0]=='bent'
image=h.draw_world_skeleton(w);assert image.shape==(240,180,3)
assert h.finger_states(None) is None
print('Skeleton rendering, straight/bent pose and missing-hand checks passed.')
