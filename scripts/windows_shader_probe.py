"""Invisible-window production GLSL draw/readback probe; not optical calibration.

Never opens fullscreen, changes display mode, or uses participant data. Requires
Windows/OpenGL compatibility context. Output directory must be a NEW test folder.
"""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import math
import sys
import os
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"src"))


def probe(output):
    import numpy as np
    import pyglet
    from pyglet.gl import (glClear,glClearColor,glViewport,glMatrixMode,glLoadIdentity,
        glOrtho,glDisable,glReadPixels,glReadBuffer,glFinish,glGetString,GL_COLOR_BUFFER_BIT,
        GL_PROJECTION,GL_MODELVIEW,GL_BLEND,GL_DITHER,GL_DEPTH_TEST,GL_BACK,
        GL_RGBA,GL_UNSIGNED_BYTE,GL_RENDERER,GL_VENDOR,GL_VERSION)
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    condition_file=output/"probe_conditions.json"
    condition_file.write_text(json.dumps({"staircase_Identity_active":[0],"condition_list":[2.],
        "stimulus_choice_active":[144],"weber_contrast_active":[.1]}))
    report={"hardware_test":"production GLSL offscreen readback", "optical_calibration":False,
        "photon_timing_verified":False,"tests":[],"source_sha256":hashlib.sha256((ROOT/"src/psychophysics_lab/_reference_csf/stimuliC.py").read_bytes()).hexdigest()}
    window=None
    old_cwd=Path.cwd()
    try:
        os.chdir(ROOT)  # legacy dependency archive has checkout-relative imports
        window=pyglet.window.Window(width=256,height=256,visible=False,vsync=False)
        window.switch_to()
        from psychophysics_lab._reference_csf.stimuliC import Grating_ADM
        from psychophysics_lab._reference_csf.libC import Params
        for key,enum in (("renderer",GL_RENDERER),("vendor",GL_VENDOR),("version",GL_VERSION)):
            report[key]=ctypes.cast(glGetString(enum),ctypes.c_char_p).value.decode(errors="replace")
        width=192.; cx,cy=144.,128.
        pitch_x,pitch_y,distance=.00022,.00025,.5
        glViewport(0,0,256,256)
        glMatrixMode(GL_PROJECTION);glLoadIdentity();glOrtho(0,256,0,256,-1,1)
        glMatrixMode(GL_MODELVIEW);glLoadIdentity()
        for state in (GL_BLEND,GL_DITHER,GL_DEPTH_TEST): glDisable(state)
        yy,xx=np.mgrid[48:208,64:224]
        dx,dy=xx+.5-cx,yy+.5-cy
        envelope=np.exp(-.5*((dx/width/.5)**2+(dy/width/.5)**2))
        for mode in ("cycles_per_degree","legacy_shader_radians"):
            for theta in (0.,math.pi/2,.5):
                phase=(2*math.pi*2*(np.degrees(np.arctan((xx+.5-128)*pitch_x/distance))-math.degrees(math.atan((cx-128)*pitch_x/distance)))*math.cos(theta)
                    +2*math.pi*2*np.degrees(np.arctan((yy+.5-128)*pitch_y/distance))*math.sin(theta)) if mode=="cycles_per_degree" else 2*(dx/width*math.cos(theta)+dy/width*math.sin(theta))
                expected=.5+envelope*.1*np.sin(phase)/2
                stimulus=Grating_ADM((cx,cy),str(condition_file),Params(width=width,bg=.5,box=False,theta=theta,SdeX=.5,SdeY=.5),
                    condition_unit=mode,spatial_geometry={"pitch_x_m":pitch_x,"pitch_y_m":pitch_y,"viewing_distance_m":distance,"screen_cx_px":128.,"screen_cy_px":128.})
                glClearColor(.5,.5,.5,1);glClear(GL_COLOR_BUFFER_BIT)
                stimulus.draw();glFinish();glReadBuffer(GL_BACK)
                pixels=(ctypes.c_ubyte*(256*256*4))()
                glReadPixels(0,0,256,256,GL_RGBA,GL_UNSIGNED_BYTE,pixels)
                rgb=np.ctypeslib.as_array(pixels).reshape(256,256,4)[48:208,64:224,:3]/255.
                error=float(np.max(np.abs(rgb-expected[...,None])))
                report["tests"].append({"mode":mode,"orientation_rad":theta,"max_rgb_error":error,"tolerance":2/255,"passed":error<=2/255})
        report["passed"]=all(item["passed"] for item in report["tests"])
    except Exception as exc:
        report["passed"]=False;report["error"]=repr(exc)
    finally:
        if window is not None:window.close()
        os.chdir(old_cwd)
        (output/"shader_probe.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if sys.platform!="win32":
        print("Windows graphics probe only; run headless unit tests on other platforms.")
        return 2
    result=probe(args.output)
    print(json.dumps(result,indent=2))
    return 0 if result["passed"] else 1

if __name__=="__main__":raise SystemExit(main())
