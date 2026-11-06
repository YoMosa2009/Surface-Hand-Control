import sys,math,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hand_control import OneEuro2D
r=random.Random(4); filt=OneEuro2D(); raw=[]; out=[]
for i in range(150):
 p=(.5+r.uniform(-.015,.015),.5+r.uniform(-.015,.015)); raw.append(p); out.append(filt.update(p,i/15,.65))
def rms(a):return math.sqrt(sum((x-.5)**2+(y-.5)**2 for x,y in a)/len(a))
assert rms(out[20:]) < rms(raw[20:])*.7,(rms(out[20:]),rms(raw[20:]))
for i in range(150,180): p=filt.update((.9,.9),i/15,.65)
assert p[0]>.85 and p[1]>.85,p
filt.reset(); assert filt.update((.2,.3),30,.65)==(.2,.3)
print('Stationary noise reduced on synthetic trace; movement reaches target; reset passed.')
