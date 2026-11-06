import sys, os, time, threading, queue, subprocess, struct, math, ctypes, json
from collections import deque
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'runtime'))
import numpy as np
import cv2
import mediapipe as mp
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk
from ctypes import wintypes

u = ctypes.WinDLL('user32', use_last_error=True)
u.GetForegroundWindow.restype = wintypes.HWND
u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
u.ShowWindow.restype = wintypes.BOOL
u.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
u.SetCursorPos.restype = wintypes.BOOL
u.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
u.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
u.SetProcessDPIAware()

HAND_BONES=((0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),(13,17),(17,18),(18,19),(19,20),(17,0))

def draw_hand_preview(rgb, points):
    height,width=rgb.shape[:2]
    if points is None or len(points)<21: return rgb
    pixels=[(round(x*width),round(y*height)) for x,y in points]
    for a,b in HAND_BONES: cv2.line(rgb,pixels[a],pixels[b],(30,200,255),2,cv2.LINE_AA)
    for i,p in enumerate(pixels): cv2.circle(rgb,p,4 if i in (4,8) else 2,(255,210,20) if i in (4,8) else (50,255,100),-1,cv2.LINE_AA)
    return rgb

def draw_world_skeleton(world):
    # A fixed oblique view of model-estimated relative 3D positions, not sensor depth.
    panel=np.full((240,180,3), 25, dtype=np.uint8)
    cv2.putText(panel,'3D estimate', (12,20),cv2.FONT_HERSHEY_SIMPLEX,.48,(210,220,230),1,cv2.LINE_AA)
    if world is None or len(world)<21: return panel
    try:
        points=np.asarray(world,dtype=np.float64)
        if points.shape!=(21,3) or not np.isfinite(points).all(): return panel
        points=points-points.mean(axis=0)
        xp=points[:,0]*.82+points[:,2]*.57
        yp=points[:,1]*.88-points[:,2]*.30
        scale=85/max(float(np.max(np.abs(xp))),float(np.max(np.abs(yp))),.02)
        projected=[(int(np.clip(90-x*scale,5,175)),int(np.clip(135+y*scale,30,235))) for x,y in zip(xp,yp)]
        for a,b in HAND_BONES: cv2.line(panel,projected[a],projected[b],(30,200,255),2,cv2.LINE_AA)
        for i,p in enumerate(projected): cv2.circle(panel,p,4 if i in (4,8) else 2,(255,210,20) if i in (4,8) else (50,255,100),-1,cv2.LINE_AA)
    except (ValueError,TypeError,OverflowError): pass
    return panel

def finger_states(world):
    # Approximate joint bend from the MCP/PIP/tip triangle in estimated 3D.
    if world is None or len(world)<21: return None
    states=[]
    try:
        for base,joint,tip in ((5,6,8),(9,10,12),(13,14,16),(17,18,20)):
            a=[world[base][i]-world[joint][i] for i in range(3)]
            b=[world[tip][i]-world[joint][i] for i in range(3)]
            denom=math.sqrt(sum(v*v for v in a)*sum(v*v for v in b))
            if denom<1e-8: return None
            cosine=sum(a[i]*b[i] for i in range(3))/denom
            if not math.isfinite(cosine): return None
            states.append('straight' if cosine<-.3 else 'bent')
        return tuple(states)
    except (ValueError,TypeError,IndexError): return None

def valid_bounds(value):
    return (isinstance(value,(list,tuple)) and len(value)==4 and
            all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=1 for v in value) and
            value[1]-value[0]>=.08 and value[3]-value[2]>=.08)

def calculate_bounds(samples):
    if len(samples)<10: return None
    x=sorted(p[0] for p in samples if 0<=p[0]<=1 and 0<=p[1]<=1)
    y=sorted(p[1] for p in samples if 0<=p[0]<=1 and 0<=p[1]<=1)
    if len(x)<10: return None
    low=int((len(x)-1)*.05); high=int((len(x)-1)*.95)
    bounds=(x[low],x[high],y[low],y[high])
    return bounds if valid_bounds(bounds) else None

def pinch_measure(world):
    if world is None or len(world)<21: return None
    try:
        def d(a,b): return math.dist(world[a],world[b])
        scale=(d(5,17)+d(0,9))*.5
        ratio=d(4,8)/scale if scale>1e-5 else None
        return ratio if ratio is not None and math.isfinite(ratio) and 0<=ratio<=5 else None
    except (ValueError,TypeError,IndexError): return None

def pinch_calibration(open_samples, closed_samples):
    if len(open_samples)<10 or len(closed_samples)<10: return None
    opened=sorted(open_samples); closed=sorted(closed_samples)
    open_mid=opened[len(opened)//2]
    close_mid=closed[len(closed)//2]
    gap=open_mid-close_mid
    if gap<.08: return None
    return (close_mid+.35*gap,close_mid+.65*gap)

def valid_pinch_thresholds(v):
    return (isinstance(v,(list,tuple)) and len(v)==2 and all(isinstance(x,(int,float)) and math.isfinite(x) for x in v)
            and 0<v[0]<v[1]<=5 and v[1]-v[0]>=.02)

def palm_center(points):
    ids=(0,5,9,13,17)
    return (sum(points[i][0] for i in ids)/len(ids), sum(points[i][1] for i in ids)/len(ids))

def centered_bounds(palm, reach):
    # Coordinates are mirrored for the preview. Bounds may extend outside the image:
    # they reflect the chosen center, and should not be silently shifted.
    x,y=1-palm[0],palm[1]
    return (x-reach/2,x+reach/2,y-reach*.4,y+reach*.4)

class WorldHandFilter:
    # Filter all estimated joints across time; never reuse a missing hand.
    def __init__(self): self.previous=None; self.timestamp=None
    def update(self,world,now):
        if world is None or len(world)!=21:
            self.previous=None; self.timestamp=None; return None
        try:
            if any(len(v)!=3 or not all(math.isfinite(n) for n in v) for v in world): raise ValueError()
            if self.previous is None or self.timestamp is None or now<=self.timestamp or now-self.timestamp>.4:
                filtered=[tuple(p) for p in world]
            else:
                alpha=1-math.exp(-(now-self.timestamp)/.07)
                filtered=[tuple(old[i]+alpha*(new[i]-old[i]) for i in range(3)) for old,new in zip(self.previous,world)]
            self.previous=filtered; self.timestamp=now
            return filtered
        except (ValueError,TypeError,OverflowError):
            self.previous=None; self.timestamp=None; return None

class OneEuro2D:
    # Speed-adaptive filter based on Casiez et al., CHI 2012.
    def __init__(self): self.reset()
    def reset(self): self.value=None; self.raw=None; self.derivative=(0.,0.); self.time=None
    @staticmethod
    def alpha(cutoff,dt):
        r=2*math.pi*cutoff*dt
        return r/(1+r)
    def update(self,point,now,smoothing):
        if self.time is None or now<=self.time or now-self.time>.5:
            self.value=point; self.raw=point; self.time=now; self.derivative=(0.,0.); return point
        dt=now-self.time
        da=self.alpha(1.,dt)
        speed=tuple((point[i]-self.raw[i])/dt for i in range(2))
        self.derivative=tuple(self.derivative[i]+da*(speed[i]-self.derivative[i]) for i in range(2))
        minimum=.45+(1-smoothing)*1.4
        cutoff=minimum+1.5*math.hypot(*self.derivative)
        a=self.alpha(cutoff,dt)
        self.value=tuple(self.value[i]+a*(point[i]-self.value[i]) for i in range(2))
        self.raw=point; self.time=now
        return self.value

class Gesture:
    def __init__(self):
        self.bounds = (.18, .82, .12, .65)
        self.pinch_threshold = .60
        self.pinch_bounds = (.60,.80)
        self.smoothing = .55
        self.aspect = .75
        self.pointer_filter=OneEuro2D(); self.samples=deque(maxlen=3); self.history=deque(maxlen=12)
        self.reset()
    def reset(self):
        self.down = False; self.ready = False; self.close_since = None; self.open_since = None
        self.ratio = None; self.xy = None; self.swipe = None; self.last_action = 0; self.down_since = 0
        self.pointer_filter.reset(); self.samples.clear(); self.history.clear(); self.aim_frozen=False; self.dragging=False; self.drag_origin=None
    def release(self):
        if self.down: u.mouse_event(4, 0, 0, 0, 0)
        self.reset()
    def update(self, points, mode, now, world=None):
        # Correct for image aspect ratio, then normalize fingertip distance by palm width.
        d=lambda a,b: math.hypot(points[a][0]-points[b][0], (points[a][1]-points[b][1])*self.aspect)
        palm=max(d(5,17), .02); measured=pinch_measure(world)
        if mode == 'Pointer / drag' and measured is None:
            self.release(); return '3D hand landmarks unavailable; drag released.'
        if mode != 'Pointer / drag': measured=d(4,8)/palm
        self.ratio=measured if self.ratio is None else self.ratio*.45+measured*.55
        ratio=self.ratio
        if mode == 'Pointer / drag':
            offset=(self.pinch_threshold-.60)*.50
            close=max(.05,self.pinch_bounds[0]+offset)
            opened=max(close+.04,self.pinch_bounds[1]+offset)
            left,right,top,bottom=self.bounds
            px,py=palm_center(points)
            x=max(0,min(1,(1-px-left)/(right-left))); y=max(0,min(1,(py-top)/(bottom-top)))
            self.samples.append((x,y))
            sample=(sorted(v[0] for v in self.samples)[len(self.samples)//2],sorted(v[1] for v in self.samples)[len(self.samples)//2])
            filtered=self.pointer_filter.update(sample,now,self.smoothing)
            if self.xy is None: self.xy=filtered
            # A pinch holds the cursor still until a deliberate palm movement starts a drag.
            candidate=self.ready and ratio<close
            if self.down and not self.dragging and self.drag_origin is not None:
                if now-self.down_since>=.20 and math.hypot(filtered[0]-self.drag_origin[0],filtered[1]-self.drag_origin[1])>.035:
                    self.dragging=True
            freeze=candidate or (self.down and not self.dragging)
            self.aim_frozen=freeze
            # Radius is in normalized screen space; subtract it instead of jumping
            # to the new point, making it a stable target with continuous movement.
            distance=math.hypot(filtered[0]-self.xy[0],filtered[1]-self.xy[1])
            radius=.010+.012*self.smoothing
            if not freeze and distance>radius:
                fraction=(distance-radius)/distance
                self.xy=(self.xy[0]+fraction*(filtered[0]-self.xy[0]),self.xy[1]+fraction*(filtered[1]-self.xy[1]))
                # Let a sustained reach at the ends access screen edges.
                self.xy=tuple(0.0 if filtered[i]<.003 else 1.0 if filtered[i]>.997 else self.xy[i] for i in range(2))
            if not freeze and not self.down: self.history.append((now,self.xy))
            cursor_x=round(self.xy[0]*(u.GetSystemMetrics(0)-1)); cursor_y=round(self.xy[1]*(u.GetSystemMetrics(1)-1))
            if not u.SetCursorPos(cursor_x,cursor_y):
                raise OSError(ctypes.get_last_error(), 'Windows rejected pointer movement')
            if ratio>opened:
                self.close_since=None
                if self.open_since is None: self.open_since=now
                if now-self.open_since>=.10:
                    self.ready=True
                    if self.down: u.mouse_event(4,0,0,0,0); self.down=False; self.dragging=False; self.drag_origin=None
            elif ratio<close:
                self.open_since=None
                if self.close_since is None: self.close_since=now
                if self.ready and not self.down and now-self.close_since>=.10:
                    u.mouse_event(2,0,0,0,0); self.down=True; self.down_since=now; self.ready=False; self.drag_origin=filtered; self.dragging=False
            else:
                self.close_since=None; self.open_since=None
            if self.down: return f'{"DRAGGING" if self.dragging else "CLICK HELD: move palm deliberately to drag"} | pinch {ratio:.2f}'
            if not self.ready: return f'Open thumb and index to get ready | pinch {ratio:.2f}, open above {opened:.2f}'
            if self.close_since is not None: return f'Pinch detected; hold briefly | pinch {ratio:.2f}'
            return f'Pointer ready | pinch {ratio:.2f}, close below {close:.2f}'
        # These modes are explicitly enabled by the user; a visible hand is enough.
        # Track palm translation instead of requiring an exact finger pose.
        px,py=palm_center(points); x,y=1-px,py
        if now-self.last_action<1.5:
            self.swipe=None
            return 'Gesture sent; pause briefly before the next swipe'
        if self.swipe is None: self.swipe=(x,y,now); return 'Hand ready: move left or right' if mode=='Tabs' else 'Hand ready: move left, right, up or down'
        sx,sy,start=self.swipe; dx=x-sx; dy=y-sy
        if now-start>1.3: self.swipe=(x,y,now); return 'Hand ready: make a short swipe'
        if max(abs(dx),abs(dy))>.11 and now-start>.10:
            direction=('right' if dx>0 else 'left') if abs(dx)>abs(dy) else ('down' if dy>0 else 'up')
            if mode=='Tabs' and direction in ('up','down'):
                self.swipe=(x,y,now); return 'Tabs: swipe left or right'
            self.last_action=now; self.swipe=None
            if mode=='Tabs':
                if direction=='left': keys(0x11,0x10,0x09)
                else: keys(0x11,0x09)
            else:
                h=u.GetForegroundWindow()
                if direction=='left': keys(0x5B,0x25)
                elif direction=='right': keys(0x5B,0x27)
                elif direction=='up': u.ShowWindow(h,3)
                else: u.ShowWindow(h,6)
            return 'Swipe '+direction
        return 'Hand ready: make a short swipe'

def keys(*ks):
    for k in ks: u.keybd_event(k,0,0,0)
    for k in reversed(ks): u.keybd_event(k,0,2,0)

def hotkeys(events):
    if not u.RegisterHotKey(None, 1, 0x4000, 0x77): events.put(('hotkey_error',None)); return
    events.put(('hotkey_ok',None))
    msg=wintypes.MSG()
    while u.GetMessageW(ctypes.byref(msg),None,0,0)>0:
        if msg.message==0x312: events.put(('toggle',None))
    u.UnregisterHotKey(None,1)

def read_exact(pipe, n):
    chunks=[]
    while n:
        s=pipe.read(n)
        if not s: raise RuntimeError('IR capture stopped or camera unavailable')
        chunks.append(s); n-=len(s)
    return b''.join(chunks)

def capture(stop, events, camera):
    cap=None; proc=None
    try:
        from mediapipe.tasks import python as mt
        from mediapipe.tasks.python import vision
        options=vision.HandLandmarkerOptions(base_options=mt.BaseOptions(model_asset_path=str(ROOT/'hand_landmarker.task')), running_mode=vision.RunningMode.VIDEO, num_hands=1, min_hand_detection_confidence=.6, min_hand_presence_confidence=.6, min_tracking_confidence=.6)
        with vision.HandLandmarker.create_from_options(options) as model:
            if camera=='Infrared (experimental)':
                exe=ROOT/'irbridge/bin/Release/net10.0-windows10.0.19041.0/irbridge.exe'
                proc=subprocess.Popen([str(exe)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
                def cancel_ir():
                    stop.wait()
                    if proc.poll() is None: proc.kill()
                threading.Thread(target=cancel_ir,daemon=True).start()
            else:
                cap=cv2.VideoCapture(0, cv2.CAP_DSHOW)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                if not cap.isOpened(): raise RuntimeError('Color camera unavailable or blocked')
            events.put(('started',None)); frame_no=0; last=0; world_filter=WorldHandFilter()
            while not stop.is_set():
                if proc:
                    w,h,stride=struct.unpack('<III',read_exact(proc.stdout,12))
                    if not (0<w<=4096 and 0<h<=4096 and stride==w*4): raise RuntimeError('Invalid IR frame')
                    bgra=np.frombuffer(read_exact(proc.stdout,stride*h),dtype=np.uint8).reshape((h,w,4))
                    rgb=cv2.cvtColor(bgra,cv2.COLOR_BGRA2RGB)
                else:
                    ok, frame=cap.read()
                    if not ok: raise RuntimeError('Camera stopped delivering frames')
                    rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                now=time.monotonic()
                if now-last<.067: continue
                last=now; rgb=cv2.resize(rgb, (320,320) if proc else (320,240), interpolation=cv2.INTER_AREA)
                frame_no=max(frame_no+1,int(now*1000))
                result=model.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,data=np.ascontiguousarray(rgb)),frame_no)
                pts=[(p.x,p.y) for p in result.hand_landmarks[0]] if result.hand_landmarks else None
                world=[(p.x,p.y,p.z) for p in result.hand_world_landmarks[0]] if result.hand_world_landmarks else None
                world=world_filter.update(world,now)
                rgb=draw_hand_preview(rgb,pts)
                rgb=cv2.flip(rgb,1)
                # Keep the UI queue bounded so stale frames cannot drive controls.
                try: events.put_nowait(('frame',(rgb,pts,world,time.monotonic())))
                except queue.Full: pass
    except Exception as e:
        if not stop.is_set(): events.put(('error',str(e)))
    finally:
        if cap: cap.release()
        if proc:
            if proc.poll() is None: proc.kill()
            proc.wait(timeout=3)
        events.put(('stopped',None))

class App:
    def __init__(self):
        self.root=tk.Tk(); self.root.title('Surface Hand Control'); self.root.geometry('760x850')
        self.events=queue.Queue(maxsize=6); self.gesture=Gesture(); self.armed=False; self.running=False; self.started=False; self.stop=None; self.last_frame=0; self.hotkey=False; self.calibrating=False; self.calibration=[]; self.config_path=ROOT/'palm_calibration.json'; self.prefs_path=ROOT/'gesture_preferences.json'; self.pinch_path=ROOT/'pinch_calibration.json'; self.pinch_calibrating=False; self.pinch_phase=None; self.pinch_samples={'open':[],'closed':[]}; self.calibration_jobs=[]; self.needs_center=False
        try:
            prefs=json.loads(self.prefs_path.read_text(encoding='utf-8'))
            sensitivity=float(prefs.get('click_sensitivity',.60)); smooth=float(prefs.get('smoothing',.55))
            if not math.isfinite(sensitivity) or not .40<=sensitivity<=.85: sensitivity=.60
            if not math.isfinite(smooth) or not .20<=smooth<=.90: smooth=.55
        except (OSError,ValueError,TypeError,AttributeError): sensitivity=.60; smooth=.55
        ttk.Label(self.root,text='Surface Hand Control',font=('Segoe UI',20,'bold')).pack(pady=8)
        ttk.Label(self.root,text='F8 enables or pauses control. Start paused; test with a harmless window.',wraplength=650).pack()
        bar=ttk.Frame(self.root); bar.pack(pady=10)
        self.camera=ttk.Combobox(bar,state='readonly',values=['Color webcam','Infrared (experimental)'],width=24); self.camera.current(0); self.camera.pack(side='left',padx=4)
        self.mode=ttk.Combobox(bar,state='readonly',values=['Pointer / drag','Tabs','Window swipes'],width=20); self.mode.current(0); self.mode.pack(side='left',padx=4); self.mode.bind('<<ComboboxSelected>>',self.mode_changed)
        self.start=ttk.Button(bar,text='Start',command=self.start_camera); self.start.pack(side='left',padx=4)
        self.stopbutton=ttk.Button(bar,text='Stop',command=self.stop_camera); self.stopbutton.pack(side='left',padx=4)
        self.togglebutton=ttk.Button(self.root,text='Enable controls (F8)',command=self.toggle); self.togglebutton.pack(pady=3)
        self.calbutton=ttk.Button(self.root,text='Calibrate comfortable hand area',command=self.begin_calibration); self.calbutton.pack(pady=3)
        self.pinchbutton=ttk.Button(self.root,text='Calibrate pinch gesture',command=self.begin_pinch_calibration); self.pinchbutton.pack(pady=3)
        tune=ttk.Frame(self.root); tune.pack(pady=2)
        ttk.Label(tune,text='Click sensitivity').grid(row=0,column=0,padx=4)
        self.click_sensitivity=tk.DoubleVar(value=sensitivity)
        ttk.Scale(tune,from_=.40,to=.85,variable=self.click_sensitivity,command=self.update_tuning,length=155).grid(row=0,column=1)
        ttk.Label(tune,text='Smoothing').grid(row=0,column=2,padx=(15,4))
        self.smoothness=tk.DoubleVar(value=smooth)
        ttk.Scale(tune,from_=.20,to=.90,variable=self.smoothness,command=self.update_tuning,length=155).grid(row=0,column=3)
        ttk.Label(tune,text='More  →').grid(row=0,column=4,padx=4)
        self.update_tuning()
        reachbar=ttk.Frame(self.root); reachbar.pack(pady=2)
        ttk.Label(reachbar,text='Pointer area').pack(side='left',padx=4)
        self.mapping=ttk.Combobox(reachbar,state='readonly',values=['Auto center','Saved area'],width=13); self.mapping.current(0); self.mapping.pack(side='left',padx=4); self.mapping.bind('<<ComboboxSelected>>',self.mapping_changed)
        ttk.Label(reachbar,text='Hand movement: small').pack(side='left')
        self.reach=tk.DoubleVar(value=.30)
        ttk.Scale(reachbar,from_=.18,to=.50,variable=self.reach,length=120).pack(side='left',padx=4)
        ttk.Label(reachbar,text='large').pack(side='left')
        ttk.Button(reachbar,text='Recenter',command=self.recenter).pack(side='left',padx=6)
        self.preview=ttk.Label(self.root); self.preview.pack(pady=6)
        self.state=tk.StringVar(value='Paused. Starting hotkey...'); ttk.Label(self.root,textvariable=self.state,font=('Segoe UI',12,'bold'),wraplength=650).pack(pady=6)
        self.info=tk.StringVar(value='Select camera and Start.'); ttk.Label(self.root,textvariable=self.info,wraplength=650).pack(pady=4)
        self.pose_info=tk.StringVar(value='Hand pose: unavailable'); ttk.Label(self.root,textvariable=self.pose_info,wraplength=650).pack(pady=2)
        ttk.Label(self.root,text='Pointer: move your hand; pinch thumb and index to click / drag. Tabs: swipe hand left/right. Window swipes: left/right snap; up maximize; down minimize. Camera processing is local.',wraplength=650).pack(pady=8)
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        threading.Thread(target=hotkeys,args=(self.events,),daemon=True).start(); self.root.after(30,self.poll)
    def update_tuning(self, _=None):
        self.gesture.pinch_threshold=self.click_sensitivity.get()
        self.gesture.smoothing=self.smoothness.get()
    def mapping_changed(self, event=None):
        self.gesture.release()
        if self.mapping.get()=='Auto center':
            self.needs_center=True; self.info.set('Show your hand in a comfortable position to recenter.')
            return
        try:
            value=json.loads(self.config_path.read_text(encoding='utf-8')).get(self.camera.get())
            if not valid_bounds(value): raise ValueError('No saved area for this camera')
            self.gesture.bounds=tuple(value); self.needs_center=False
            self.info.set('Using saved hand area.')
        except (OSError, ValueError, TypeError, AttributeError):
            self.mapping.set('Auto center'); self.needs_center=True
            self.info.set('No saved area for this camera; using auto center. Calibrate to create one.')
    def recenter(self):
        if not self.started:
            self.state.set('Start the camera first.'); return
        self.gesture.release(); self.mapping.set('Auto center'); self.needs_center=True
        self.info.set('Show your hand in a comfortable central position to recenter.')
    def mode_changed(self,event=None):
        self.armed=False; self.gesture.release(); self.togglebutton.config(text='Enable controls (F8)'); self.state.set('Paused after mode change. Press F8 to enable.')
    def toggle(self):
        self.gesture.release()
        if self.calibrating or self.pinch_calibrating:
            self.state.set('Finish calibration before enabling controls.'); return
        if not self.started or time.monotonic()-self.last_frame>=.5:
            self.armed=False; self.state.set('Cannot enable: waiting for live camera frames.'); return
        self.armed=not self.armed
        self.needs_center=self.armed and self.mode.get()=='Pointer / drag' and self.mapping.get()=='Auto center'
        self.togglebutton.config(text='Pause controls (F8)' if self.armed else 'Enable controls (F8)')
        self.state.set('ENABLED — press F8 to pause' if self.armed else 'Paused — press F8 to enable')
    def begin_calibration(self):
        if self.pinch_calibrating: return
        if not self.started or time.monotonic()-self.last_frame>=.5:
            self.state.set('Start the camera before calibration.'); return
        self.armed=False; self.gesture.release(); self.togglebutton.config(text='Enable controls (F8)')
        self.calibrating=True; self.calibration=[]
        self.state.set('Calibrating for 8 seconds: move your hand comfortably left, right, up and down.')
        self.calibration_jobs.append(self.root.after(8000,self.finish_calibration))
    def finish_calibration(self):
        if not self.calibrating: return
        self.calibrating=False
        bounds=calculate_bounds(self.calibration)
        if bounds is None:
            self.state.set('Calibration failed: keep your hand visible and move it farther in all directions.'); return
        self.gesture.bounds=bounds
        self.mapping.set('Saved area')
        try:
            existing=json.loads(self.config_path.read_text(encoding='utf-8')) if self.config_path.exists() else {}
            existing[self.camera.get()]=list(bounds)
            self.config_path.write_text(json.dumps(existing,indent=2),encoding='utf-8')
        except (OSError, ValueError, TypeError) as e:
            self.state.set('Calibrated for this session, but could not save: '+str(e)); return
        self.state.set('Calibration saved. Press F8 or Enable controls to try it.')
    def begin_pinch_calibration(self):
        if self.calibrating: return
        if not self.started or time.monotonic()-self.last_frame>=.5:
            self.state.set('Start the camera before pinch calibration.'); return
        if self.pinch_calibrating:
            if self.pinch_phase=='waiting': self.start_pinch_closed()
            return
        self.armed=False; self.gesture.release(); self.togglebutton.config(text='Enable controls (F8)')
        self.pinch_calibrating=True; self.pinch_samples={'open':[],'closed':[]}
        self.pinch_phase='open'; self.pinch_start=time.monotonic()
        self.pinchbutton.config(state='disabled')
        self.state.set('Step 1: hold thumb and index APART for 4 seconds. Keep the hand visible.')
        self.calibration_jobs.append(self.root.after(4000,self.finish_pinch_open))
    def finish_pinch_open(self):
        if not self.pinch_calibrating or self.pinch_phase!='open': return
        self.pinch_phase='waiting'
        if len(self.pinch_samples['open'])<10:
            count=len(self.pinch_samples['open']); self.reset_pinch_calibration()
            self.state.set(f'Open-hand capture failed: only {count} samples; keep the hand visible and retry.'); return
        self.pinchbutton.config(state='normal',text='Capture pinched hand')
        self.state.set('Step 1 saved. Put thumb and index TOGETHER, then click Capture pinched hand.')
    def start_pinch_closed(self):
        self.pinch_phase='closed'; self.pinch_start=time.monotonic(); self.pinchbutton.config(state='disabled')
        self.state.set('Step 2: keep thumb and index TOGETHER for 4 seconds. Keep the hand visible.')
        self.calibration_jobs.append(self.root.after(4000,self.finish_pinch_calibration))
    def reset_pinch_calibration(self):
        self.pinch_calibrating=False; self.pinch_phase=None
        self.pinchbutton.config(state='normal',text='Calibrate pinch gesture')
    def finish_pinch_calibration(self):
        if not self.pinch_calibrating or self.pinch_phase!='closed': return
        self.reset_pinch_calibration()
        opened=self.pinch_samples['open']; closed=self.pinch_samples['closed']
        if len(closed)<10:
            self.state.set(f'Pinched-hand capture failed: only {len(closed)} samples; keep the hand visible and retry.'); return
        bounds=pinch_calibration(opened,closed)
        if not bounds:
            om=sorted(opened)[len(opened)//2]; cm=sorted(closed)[len(closed)//2]
            self.state.set(f'Cannot distinguish poses: open {om:.2f}, pinched {cm:.2f}. Try a clearer view of both fingertips and retry.'); return
        self.gesture.pinch_bounds=bounds
        self.click_sensitivity.set(.60); self.update_tuning()
        try:
            settings=json.loads(self.pinch_path.read_text(encoding='utf-8')) if self.pinch_path.exists() else {}
            settings[self.camera.get()]=list(bounds)
            self.pinch_path.write_text(json.dumps(settings,indent=2),encoding='utf-8')
        except (OSError, ValueError, TypeError, AttributeError) as e:
            self.state.set('Pinch calibrated for this session, but could not save: '+str(e)); return
        self.state.set('Pinch calibration saved. Enable controls and try opening and pinching.')
    def start_camera(self):
        if self.running or not self.hotkey: return
        self.gesture.pinch_bounds=(.60,.80)
        try:
            value=json.loads(self.pinch_path.read_text(encoding='utf-8')).get(self.camera.get())
            if valid_pinch_thresholds(value): self.gesture.pinch_bounds=tuple(value)
        except (OSError,ValueError,TypeError,AttributeError): pass
        self.gesture.aspect=1.0 if self.camera.get()=='Infrared (experimental)' else .75
        self.gesture.bounds=(.18,.82,.12,.65)
        try:
            settings=json.loads(self.config_path.read_text(encoding='utf-8'))
            value=settings.get(self.camera.get())
            if valid_bounds(value): self.gesture.bounds=tuple(value)
        except (OSError,ValueError,TypeError): pass
        self.running=True; self.start.config(state='disabled'); self.camera.config(state='disabled'); self.stop=threading.Event()
        threading.Thread(target=capture,args=(self.stop,self.events,self.camera.get()),daemon=True).start(); self.state.set('Starting camera; controls paused.')
    def stop_camera(self):
        for job in self.calibration_jobs:
            self.root.after_cancel(job)
        self.calibration_jobs.clear()
        self.calibrating=False; self.reset_pinch_calibration(); self.needs_center=False; self.armed=False; self.started=False; self.gesture.release(); self.togglebutton.config(text='Enable controls (F8)'); self.state.set('Stopping camera; controls paused.')
        if self.stop: self.stop.set()
    def poll(self):
        try:
            while True:
                kind,data=self.events.get_nowait()
                if kind=='hotkey_ok': self.hotkey=True; self.state.set('Paused. Start a camera.')
                elif kind=='hotkey_error': self.state.set('F8 is already in use; close the other app and restart.'); self.start.config(state='disabled')
                elif kind=='toggle': self.toggle()
                elif kind=='frame':
                    rgb,pts,world,stamp=data
                    if not self.started or time.monotonic()-stamp>.35: continue
                    self.last_frame=stamp
                    live=Image.fromarray(rgb).resize((400,300))
                    skeleton=Image.fromarray(draw_world_skeleton(world)).resize((225,300))
                    combined=Image.new('RGB',(625,300)); combined.paste(live,(0,0)); combined.paste(skeleton,(400,0))
                    self.photo=ImageTk.PhotoImage(combined); self.preview.configure(image=self.photo)
                    fingers=finger_states(world)
                    self.pose_info.set('Estimated fingers: '+', '.join(f'{name} {state}' for name,state in zip(('index','middle','ring','little'),fingers)) if fingers else 'Hand pose: unavailable')
                    if self.pinch_calibrating and self.pinch_phase in ('open','closed'):
                        elapsed=time.monotonic()-self.pinch_start
                        sample=pinch_measure(world)
                        if sample is not None and .5<elapsed<3.8:
                            self.pinch_samples[self.pinch_phase].append(sample)
                    if self.calibrating and pts is not None:
                        px,py=palm_center(pts); self.calibration.append((1-px,py))
                    if self.pinch_calibrating:
                        self.info.set(f"Pinch calibration: open samples {len(self.pinch_samples['open'])}, pinched samples {len(self.pinch_samples['closed'])}.")
                    elif self.calibrating:
                        self.info.set(f'Calibration: {len(self.calibration)} hand samples. Keep your full hand visible.')
                    elif pts is None:
                        self.gesture.release(); self.info.set('No hand detected; any drag released.')
                    elif self.armed:
                        if self.needs_center and self.mode.get()=='Pointer / drag':
                            self.gesture.release(); self.gesture.bounds=centered_bounds(palm_center(pts),self.reach.get()); self.needs_center=False
                        try:
                            detail=self.gesture.update(pts,self.mode.get(),time.monotonic(),world)
                            if any(x<.025 or x>.975 or y<.025 or y>.975 for x,y in pts): detail += ' | Hand near camera edge'
                            self.info.set(detail)
                        except OSError as e:
                            self.armed=False; self.gesture.release(); self.togglebutton.config(text='Enable controls (F8)'); self.state.set('Input error: '+str(e))
                    else: self.info.set('Hand detected. Controls paused.')
                elif kind=='error': self.armed=False; self.gesture.release(); self.state.set('Error: '+data)
                elif kind=='stopped':
                    self.calibrating=False; self.reset_pinch_calibration()
                    for job in self.calibration_jobs: self.root.after_cancel(job)
                    self.calibration_jobs.clear()
                    self.running=False; self.started=False; self.armed=False; self.gesture.release(); self.camera.config(state='readonly'); self.start.config(state='normal' if self.hotkey else 'disabled')
                elif kind=='started':
                    self.started=True; self.state.set('Camera running. Controls paused; press F8 to enable.')
        except queue.Empty: pass
        if self.armed and time.monotonic()-self.last_frame>.5:
            self.armed=False; self.gesture.release(); self.togglebutton.config(text='Enable controls (F8)'); self.state.set('Paused: camera frames stopped. Press F8 when frames resume.')
        self.root.after(30,self.poll)
    def close(self):
        self.stop_camera()
        try: self.prefs_path.write_text(json.dumps({'click_sensitivity':self.click_sensitivity.get(),'smoothing':self.smoothness.get()},indent=2),encoding='utf-8')
        except OSError: pass
        self.root.destroy()

if __name__=='__main__': App().root.mainloop()
