# -*- coding: utf-8 -*-
"""
APC40 MK2 LED Mapper v2
Windows-only, no third-party Python packages.

Features:
- Configures every APC40 MK2 button that has a host-controllable LED.
- 45 RGB LEDs (40 Clip Launch + 5 Scene Launch): selectable APC palette color.
- Single-color LEDs are also listed and can be Solid / Blink / Off.
- Exactly three user states: SOLID, BLINK, OFF.
- Press a mapped button on the APC40: SOLID <-> BLINK.
- RGB blink uses the APC40 hardware blink mode.
- Single-color blink is software-timed because the protocol exposes only
  off/on for those LEDs.
- Opens both MIDI OUT and MIDI IN using Windows winmm.dll.
"""
import ctypes
from ctypes import wintypes
import json, os, sys, threading
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox

PALETTE = ["000000","1E1E1E","7F7F7F","FFFFFF","FF4C4C","FF0000","590000","190000","FFBD6C","FF5400","591D00","271B00","FFFF4C","FFFF00","595900","191900","88FF4C","54FF00","1D5900","142B00","4CFF4C","00FF00","005900","001900","4CFF5E","00FF19","00590D","001902","4CFF88","00FF55","00591D","001F12","4CFFB7","00FF99","005935","001912","4CC3FF","00A9FF","004152","001019","4C88FF","0055FF","001D59","000819","4C4CFF","0000FF","000059","000019","874CFF","5400FF","190064","0F0030","FF4CFF","FF00FF","590059","190019","FF4C87","FF0054","59001D","220013","FF1500","993500","795100","436400","033900","005735","00547F","0000FF","00454F","2500CC","7F7F7F","202020","FF0000","BDFF2D","AFED06","64FF09","108B00","00FF87","00A9FF","002AFF","3F00FF","7A00FF","B21A7D","402100","FF4A00","88E106","72FF15","00FF00","3BFF26","59FF71","38FFCC","5B8AFF","3151C6","877FE9","D31DFF","FF005D","FF7F00","B9B000","90FF00","835D07","392B00","144C10","0D5038","15152A","16205A","693C1C","A8000A","DE513D","D86A1C","FFE126","9EE12F","67B50F","1E1E30","DCFF6B","80FFBD","9A99FF","8E66FF","404040","757575","E0FFFF","A00000","350000","1AD000","074200","B9B000","3F3100","B35F00","4B1502"]

SOLID, BLINK, OFF = 0, 1, 2
STATE_NAMES = ["Solid", "Blink", "Off"]

# LED objects from the APC40 Mk2 Communications Protocol v1.2.
# Each tuple: (key, label, kind, note, channel, track)
# kind=rgb means velocity is palette index and channel is LED type.
# kind=single means velocity 0/127; track None means channel 0.
LED_CONTROLS = []

# RGB Clip Launch 1-40
for i in range(40):
    LED_CONTROLS.append((f"clip_{i+1}", f"Clip Launch {i+1}", "rgb", i, None, None))
# Track LED groups
for group, note, label in [
    ("record_arm",0x30,"Record Arm"),
    ("solo",0x31,"Solo"),
    ("activator",0x32,"Track Activator"),
    ("track_select",0x33,"Track Select"),
    ("clip_stop",0x34,"Clip Stop"),
    ("crossfade",0x42,"Crossfade A/B"),
]:
    for t in range(8):
        LED_CONTROLS.append((f"{group}_{t+1}", f"{label} {t+1}", "single", note, t, t+1))
# Global single-color LED buttons
for key,label,note in [
    ("device_left","Device Left",0x3A),("device_right","Device Right",0x3B),
    ("bank_left","Bank Left",0x3C),("bank_right","Bank Right",0x3D),
    ("device_onoff","Device On/Off",0x3E),("device_lock","Device Lock",0x3F),
    ("clip_device_view","Clip/Device View",0x40),("detail_view","Detail View",0x41),
    ("master","Master",0x50),
    ("pan","Pan",0x57),("sends","Sends",0x58),("user","User",0x59),
    ("metronome","Metronome",0x5A),("play","Play",0x5B),("record","Record",0x5D),
    ("session_record","Session Record",0x66),
]:
    LED_CONTROLS.append((key,label,"single",note,0,None))
# RGB Scene Launch 1-5
for i in range(5):
    LED_CONTROLS.append((f"scene_{i+1}", f"Scene Launch {i+1}", "rgb", 0x52+i, None, None))

CONTROL_INDEX={c[0]:i for i,c in enumerate(LED_CONTROLS)}

winmm=ctypes.WinDLL("winmm.dll")
class MIDIOUTCAPSW(ctypes.Structure):
    _fields_=[("wMid",wintypes.WORD),("wPid",wintypes.WORD),("vDriverVersion",wintypes.UINT),
              ("szPname",wintypes.WCHAR*32),("wTechnology",wintypes.WORD),("wVoices",wintypes.WORD),
              ("wNotes",wintypes.WORD),("wChannelMask",wintypes.WORD),("dwSupport",wintypes.DWORD)]
winmm.midiOutGetNumDevs.restype=wintypes.UINT
winmm.midiOutGetDevCapsW.argtypes=[wintypes.UINT,ctypes.POINTER(MIDIOUTCAPSW),wintypes.UINT]
winmm.midiOutGetDevCapsW.restype=wintypes.UINT
winmm.midiOutOpen.argtypes=[ctypes.POINTER(wintypes.HANDLE),wintypes.UINT,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD]
winmm.midiOutOpen.restype=wintypes.UINT
winmm.midiOutShortMsg.argtypes=[wintypes.HANDLE,wintypes.DWORD]
winmm.midiOutShortMsg.restype=wintypes.UINT
winmm.midiOutReset.argtypes=[wintypes.HANDLE]; winmm.midiOutReset.restype=wintypes.UINT
winmm.midiOutClose.argtypes=[wintypes.HANDLE]; winmm.midiOutClose.restype=wintypes.UINT
winmm.midiInGetNumDevs.restype=wintypes.UINT
winmm.midiInGetDevCapsW.argtypes=[wintypes.UINT,ctypes.POINTER(MIDIOUTCAPSW),wintypes.UINT]
winmm.midiInGetDevCapsW.restype=wintypes.UINT
winmm.midiInOpen.argtypes=[ctypes.POINTER(wintypes.HANDLE),wintypes.UINT,ctypes.c_void_p,wintypes.DWORD_PTR,wintypes.DWORD]
winmm.midiInOpen.restype=wintypes.UINT
winmm.midiInStart.argtypes=[wintypes.HANDLE]; winmm.midiInStart.restype=wintypes.UINT
winmm.midiInStop.argtypes=[wintypes.HANDLE]; winmm.midiInStop.restype=wintypes.UINT
winmm.midiInReset.argtypes=[wintypes.HANDLE]; winmm.midiInReset.restype=wintypes.UINT
winmm.midiInClose.argtypes=[wintypes.HANDLE]; winmm.midiInClose.restype=wintypes.UINT
MMSYSERR_NOERROR=0
MIM_DATA=0x3C3
CALLBACK_FUNCTION=0x30000
MIDIINPROC=ctypes.WINFUNCTYPE(None,wintypes.HANDLE,wintypes.UINT,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD)

class MidiIO:
    def __init__(self):
        self.out_handle=None; self.in_handle=None; self._callback=None; self.on_message=None
    @staticmethod
    def devices():
        out=[]
        for i in range(int(winmm.midiOutGetNumDevs())):
            caps=MIDIOUTCAPSW()
            if winmm.midiOutGetDevCapsW(i,ctypes.byref(caps),ctypes.sizeof(caps))==0:
                out.append((i,caps.szPname))
        return out
    def open(self, device_id, cb):
        self.close()
        h=wintypes.HANDLE()
        err=winmm.midiOutOpen(ctypes.byref(h),int(device_id),0,0,0)
        if err: raise RuntimeError(f"midiOutOpen error {err}")
        self.out_handle=h; self.on_message=cb
        def _cb(hin,msg,instance,p1,p2):
            if msg==MIM_DATA and self.on_message:
                s=int(p1)&255; d1=(int(p1)>>8)&127; d2=(int(p1)>>16)&127
                try: self.on_message(s,d1,d2)
                except Exception: pass
        self._callback=MIDIINPROC(_cb)
        hi=wintypes.HANDLE()
        err=winmm.midiInOpen(ctypes.byref(hi),int(device_id),ctypes.cast(self._callback,ctypes.c_void_p),0,CALLBACK_FUNCTION)
        if err==0:
            self.in_handle=hi; winmm.midiInStart(hi)
    def send(self,ch,note,vel):
        if self.out_handle is None: raise RuntimeError("No hay salida MIDI conectada.")
        msg=(0x90|(ch&15))|((note&127)<<8)|((vel&127)<<16)
        err=winmm.midiOutShortMsg(self.out_handle,msg)
        if err: raise RuntimeError(f"midiOutShortMsg error {err}")
    def close(self):
        if self.in_handle:
            try: winmm.midiInStop(self.in_handle); winmm.midiInReset(self.in_handle); winmm.midiInClose(self.in_handle)
            except Exception: pass
            self.in_handle=None
        if self.out_handle:
            try: winmm.midiOutReset(self.out_handle); winmm.midiOutClose(self.out_handle)
            except Exception: pass
            self.out_handle=None
        self._callback=None

def rgb(h):
    h=h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def lum_fg(h):
    r,g,b=rgb(h); return "white" if .299*r+.587*g+.114*b<145 else "black"
def nearest_color(h):
    r,g,b=rgb(h); best=0; bd=10**30
    for i,h2 in enumerate(PALETTE):
        r2,g2,b2=rgb(h2); rm=(r+r2)//2; dr=r-r2; dg=g-g2; db=b-b2
        d=(((512+rm)*dr*dr)>>8)+4*dg*dg+(((767-rm)*db*db)>>8)
        if d<bd: bd=d; best=i
    return best

class Mapper(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("APC40 MK2 LED Mapper v2")
        self.geometry("1200x820"); self.minsize(1050,700)
        self.midi=MidiIO(); self.device_map={}
        self.states=[SOLID]*len(LED_CONTROLS)
        self.colors=[18]*len(LED_CONTROLS)  # bright green-ish APC palette default
        self.selected=0
        self.blink_phase=[True]*len(LED_CONTROLS)
        self._blink_job=None
        self._build()
        self.refresh_devices()
        self.select_control(0)
        self.protocol("WM_DELETE_WINDOW",self.close)

    def _build(self):
        root=ttk.Frame(self,padding=10); root.pack(fill="both",expand=True)
        top=ttk.Frame(root); top.pack(fill="x",pady=(0,8))
        ttk.Label(top,text="MIDI OUT / IN:").pack(side="left")
        self.combo=ttk.Combobox(top,state="readonly",width=42); self.combo.pack(side="left",padx=6)
        ttk.Button(top,text="Actualizar",command=self.refresh_devices).pack(side="left")
        ttk.Button(top,text="Conectar",command=self.connect).pack(side="left",padx=5)
        self.status=tk.StringVar(value="Sin conectar"); ttk.Label(top,textvariable=self.status).pack(side="right")

        pan=ttk.Panedwindow(root,orient="horizontal"); pan.pack(fill="both",expand=True)
        left=ttk.Frame(pan,padding=(0,0,8,0)); right=ttk.Frame(pan,padding=(8,0,0,0))
        pan.add(left,weight=3); pan.add(right,weight=2)

        ttk.Label(left,text="BOTONES CON LED CONTROLABLE",font=("Segoe UI",11,"bold")).pack(anchor="w")
        self.tree=ttk.Treeview(left,columns=("state","type","color"),show="headings",selectmode="browse")
        self.tree.heading("state",text="Estado"); self.tree.heading("type",text="Tipo"); self.tree.heading("color",text="Color")
        self.tree.column("state",width=75,anchor="center"); self.tree.column("type",width=80,anchor="center"); self.tree.column("color",width=100,anchor="center")
        self.tree.pack(side="left",fill="both",expand=True)
        sb=ttk.Scrollbar(left,orient="vertical",command=self.tree.yview); sb.pack(side="right",fill="y"); self.tree.configure(yscrollcommand=sb.set)
        for i,c in enumerate(LED_CONTROLS):
            self.tree.insert("", "end", iid=str(i), text=c[1], values=("Solid","RGB" if c[2]=="rgb" else "Single",""))
        self.tree.bind("<<TreeviewSelect>>",lambda e:self._tree_select())

        sel=ttk.LabelFrame(right,text="Control seleccionado",padding=12); sel.pack(fill="x")
        self.namevar=tk.StringVar(); ttk.Label(sel,textvariable=self.namevar,font=("Segoe UI",15,"bold")).pack(anchor="w")
        self.preview=tk.Label(sel,text="   ",width=12,height=2,relief="sunken"); self.preview.pack(pady=10)
        self.hexvar=tk.StringVar(); ttk.Label(sel,textvariable=self.hexvar,font=("Consolas",11,"bold")).pack()
        ttk.Button(sel,text="Elegir color…",command=self.choose_color).pack(fill="x",pady=(8,5))
        ttk.Label(sel,text="Estado:").pack(anchor="w")
        self.statecombo=ttk.Combobox(sel,state="readonly",values=STATE_NAMES)
        self.statecombo.pack(fill="x",pady=4)
        self.statecombo.bind("<<ComboboxSelected>>",lambda e:self.set_state(self.statecombo.current()))
        ttk.Button(sel,text="APLICAR",command=self.apply_selected).pack(fill="x",pady=3)
        ttk.Button(sel,text="APLICAR TODO",command=self.apply_all).pack(fill="x",pady=3)
        ttk.Button(sel,text="TODO SOLID",command=lambda:self.set_all_state(SOLID)).pack(fill="x",pady=3)
        ttk.Button(sel,text="TODO OFF",command=lambda:self.set_all_state(OFF)).pack(fill="x",pady=3)

        pal=ttk.LabelFrame(right,text="Paleta APC40 MK2 (RGB)",padding=8); pal.pack(fill="both",expand=True,pady=(10,0))
        canv=tk.Canvas(pal,highlightthickness=0); canv.pack(side="left",fill="both",expand=True)
        scroll=ttk.Scrollbar(pal,orient="vertical",command=canv.yview); scroll.pack(side="right",fill="y"); canv.configure(yscrollcommand=scroll.set)
        inner=ttk.Frame(canv); canv.create_window((0,0),window=inner,anchor="nw")
        inner.bind("<Configure>",lambda e:canv.configure(scrollregion=canv.bbox("all")))
        for i,h in enumerate(PALETTE):
            tk.Button(inner,width=3,height=1,bg="#"+h,relief="flat",command=lambda x=i:self.set_color(x)).grid(row=i//8,column=i%8,padx=2,pady=2)

        bottom=ttk.Frame(root); bottom.pack(fill="x",pady=(8,0))
        ttk.Button(bottom,text="Guardar configuración…",command=self.save).pack(side="left")
        ttk.Button(bottom,text="Cargar configuración…",command=self.load).pack(side="left",padx=5)
        ttk.Label(bottom,text=f"{len(LED_CONTROLS)} LEDs/botones controlables").pack(side="left",padx=12)
        ttk.Button(bottom,text="Salir",command=self.close).pack(side="right")

    def refresh_devices(self):
        devs=MidiIO.devices(); self.device_map={n:i for i,n in devs}; names=list(self.device_map)
        self.combo["values"]=names
        if names:
            pref=next((n for n in names if "APC40" in n.upper()),names[0]); self.combo.set(pref)
            self.status.set(f"{len(names)} salida(s) MIDI")
        else: self.combo.set(""); self.status.set("No hay MIDI OUT")

    def connect(self):
        n=self.combo.get()
        if not n: messagebox.showwarning("MIDI","Selecciona la APC40 MK2."); return
        try:
            self.midi.open(self.device_map[n],self.on_midi)
            self.status.set(f"Conectado: {n} — feedback activo")
            self.apply_all(False)
            self.start_blink_timer()
        except Exception as e: messagebox.showerror("MIDI",str(e))

    def select_control(self,i):
        self.selected=i
        c=LED_CONTROLS[i]
        self.tree.selection_set(str(i)); self.tree.see(str(i))
        self.namevar.set(c[1] + ("  [RGB]" if c[2]=="rgb" else "  [LED]"))
        h=PALETTE[self.colors[i]]; self.hexvar.set("#"+h); self.preview.configure(bg="#"+h)
        self.statecombo.set(STATE_NAMES[self.states[i]])
        self._refresh_tree()

    def _tree_select(self):
        s=self.tree.selection()
        if s: self.select_control(int(s[0]))

    def _refresh_tree(self):
        for i,c in enumerate(LED_CONTROLS):
            st=STATE_NAMES[self.states[i]]
            typ="RGB" if c[2]=="rgb" else "Single"
            col="#"+PALETTE[self.colors[i]] if c[2]=="rgb" else "—"
            self.tree.item(str(i),values=(st,typ,col))
        h=PALETTE[self.colors[self.selected]]
        self.preview.configure(bg="#"+h); self.hexvar.set("#"+h)

    def set_color(self,i):
        self.colors[self.selected]=i; self._refresh_tree()
        self.apply_selected(False)

    def choose_color(self):
        if LED_CONTROLS[self.selected][2]!="rgb":
            messagebox.showinfo("Color","Este botón tiene un LED de un solo color según el protocolo de la APC40 MK2.")
            return
        ch=colorchooser.askcolor(color="#"+PALETTE[self.colors[self.selected]],title="Elige un color")
        if ch and ch[1]:
            i=nearest_color(ch[1]); self.set_color(i)

    def set_state(self,state,apply=True):
        self.states[self.selected]=state
        self.statecombo.set(STATE_NAMES[state]); self._refresh_tree()
        if apply: self.apply_selected(False)

    def set_all_state(self,state):
        for i in range(len(self.states)): self.states[i]=state
        self._refresh_tree(); self.apply_all(False)

    def send_control(self,i,force_phase=None):
        key,label,kind,note,ch,track=LED_CONTROLS[i]
        state=self.states[i]
        if kind=="rgb":
            # APC RGB LED type: 0 solid; 11 blink 1/24; 0 with color 0 = off.
            if state==OFF: self.midi.send(0,note,0)
            elif state==SOLID: self.midi.send(0,note,self.colors[i])
            else: self.midi.send(11,note,self.colors[i])
        else:
            if state==OFF: vel=0
            elif state==SOLID: vel=127
            else:
                phase=self.blink_phase[i] if force_phase is None else force_phase
                vel=127 if phase else 0
            channel=ch if ch is not None else 0
            self.midi.send(channel,note,vel)

    def apply_selected(self,show=True):
        if not self.midi.out_handle:
            if show: messagebox.showwarning("MIDI","Conecta primero la APC40 MK2.")
            return
        try:
            self.send_control(self.selected)
            self.status.set(f"{LED_CONTROLS[self.selected][1]} → {STATE_NAMES[self.states[self.selected]]}")
        except Exception as e:
            if show: messagebox.showerror("MIDI",str(e))

    def apply_all(self,show=True):
        if not self.midi.out_handle:
            if show: messagebox.showwarning("MIDI","Conecta primero la APC40 MK2.")
            return
        try:
            for i in range(len(LED_CONTROLS)): self.send_control(i)
            self._refresh_tree()
            self.status.set("Configuración enviada")
        except Exception as e:
            if show: messagebox.showerror("MIDI",str(e))

    def start_blink_timer(self):
        if self._blink_job: self.after_cancel(self._blink_job)
        def tick():
            if self.midi.out_handle:
                changed=False
                for i,c in enumerate(LED_CONTROLS):
                    if self.states[i]==BLINK and c[2]=="single":
                        self.blink_phase[i]=not self.blink_phase[i]
                        try: self.send_control(i)
                        except Exception: pass
                        changed=True
                if changed: self._refresh_tree()
            self._blink_job=self.after(500,tick)
        self._blink_job=self.after(500,tick)

    def on_midi(self,status,data1,data2):
        mt=status&0xF0; ch=status&0x0F
        if mt not in (0x80,0x90): return
        pressed=(mt==0x90 and data2>0)
        if not pressed: return
        i=self.match_input(data1,ch)
        if i is None: return
        # Requested behavior: first press -> blink, second press -> solid.
        # OFF remains OFF until changed from the GUI.
        if self.states[i]==OFF: self.states[i]=SOLID
        elif self.states[i]==SOLID: self.states[i]=BLINK
        else: self.states[i]=SOLID
        self.blink_phase[i]=True
        try: self.send_control(i)
        except Exception: pass
        self.after(0,self._refresh_tree)

    def match_input(self,note,ch):
        # RGB clip launch: note 0-39; channel identifies track for input.
        if 0 <= note <= 39:
            return note
        # Track-dependent LEDs use note 0x30..0x34 and 0x42, channel 0..7.
        for i,c in enumerate(LED_CONTROLS):
            if c[2]=="single" and c[3]==note and c[4] is not None and c[4]==ch:
                return i
        # Global single-color buttons.
        if note in (0x3A,0x3B,0x3C,0x3D,0x3E,0x3F,0x40,0x41,0x50,0x57,0x58,0x59,0x5A,0x5B,0x5D,0x66):
            for i,c in enumerate(LED_CONTROLS):
                if c[2]=="single" and c[3]==note and c[4]==0: return i
        # Scene RGB.
        if 0x52 <= note <= 0x56:
            return CONTROL_INDEX[f"scene_{note-0x51}"]
        return None

    def save(self):
        p=filedialog.asksaveasfilename(defaultextension=".apc40.json",filetypes=[("APC40 Mapper","*.apc40.json"),("JSON","*.json")])
        if not p:return
        data={"controller":"Akai APC40 MK2","version":2,
              "controls":[{"key":c[0],"state":self.states[i],"color_index":self.colors[i]} for i,c in enumerate(LED_CONTROLS)]}
        try:
            with open(p,"w",encoding="utf-8") as f: json.dump(data,f,indent=2)
            self.status.set("Configuración guardada")
        except Exception as e: messagebox.showerror("Guardar",str(e))

    def load(self):
        p=filedialog.askopenfilename(filetypes=[("APC40 Mapper","*.apc40.json"),("JSON","*.json")])
        if not p:return
        try:
            with open(p,encoding="utf-8") as f:d=json.load(f)
            controls=d.get("controls")
            if not controls: raise ValueError("No hay controles v2 en el archivo.")
            bykey={x.get("key"):x for x in controls}
            for i,c in enumerate(LED_CONTROLS):
                x=bykey.get(c[0])
                if x:
                    self.states[i]=int(x.get("state",SOLID)); self.colors[i]=int(x.get("color_index",18))
                    if self.states[i] not in (SOLID,BLINK,OFF): self.states[i]=SOLID
                    if not 0<=self.colors[i]<len(PALETTE): self.colors[i]=18
            self.select_control(self.selected); self.apply_all(False); self.status.set("Configuración cargada")
        except Exception as e: messagebox.showerror("Cargar",str(e))

    def close(self):
        if self._blink_job:
            try:self.after_cancel(self._blink_job)
            except Exception:pass
        self.midi.close(); self.destroy()

if __name__=="__main__":
    if sys.platform!="win32":
        raise SystemExit("Este programa está diseñado para Windows.")
    Mapper().mainloop()
