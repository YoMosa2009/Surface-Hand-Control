import sys,time,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hand_control import App, Gesture, valid_pinch_thresholds
class Widget:
 def __init__(self): self.value=''; self.options={}
 def set(self,v): self.value=v
 def get(self): return 'Color webcam'
 def config(self,**kw): self.options.update(kw)
class Root:
 def after(self,ms,cb): return 'job'
 def after_cancel(self,job): pass
a=App.__new__(App);a.calibrating=False;a.started=True;a.last_frame=time.monotonic();a.pinch_calibrating=False;a.pinch_phase=None;a.armed=False;a.gesture=Gesture();a.togglebutton=Widget();a.pinchbutton=Widget();a.state=Widget();a.root=Root();a.calibration_jobs=[];a.camera=Widget();a.click_sensitivity=Widget();a.update_tuning=lambda: None
temp_dir=tempfile.TemporaryDirectory(); a.pinch_path=Path(temp_dir.name)/'pinch.json'
a.begin_pinch_calibration(); assert a.pinch_phase=='open'; a.pinch_samples['open']=[1.0]*15
a.finish_pinch_open(); assert a.pinch_phase=='waiting' and a.pinchbutton.options['state']=='normal'
a.begin_pinch_calibration(); assert a.pinch_phase=='closed'; a.pinch_samples['closed']=[.2]*15
a.finish_pinch_calibration(); assert not a.pinch_calibrating and valid_pinch_thresholds(a.gesture.pinch_bounds)
a.pinch_calibrating=True;a.pinch_phase='open';a.pinch_samples={'open':[],'closed':[]};a.finish_pinch_open();assert 'only 0 samples' in a.state.value
print('Two-step calibration, save, and missing-sample reporting passed.')
