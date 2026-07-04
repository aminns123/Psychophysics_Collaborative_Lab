

import sys
import os
cwd                 = os.getcwd()

import Functions.functionsForUse as funcs
from Events.stimuliC import *
import datetime
from Events.libC import ExpWindow
import pyglet

from pathlib import Path

WORKING_DIR  = str(Path(__file__).resolve().parent.parent.parent.parent)+'/'
print('WORKING_DIR', WORKING_DIR)


working_Directory       = WORKING_DIR+'psychophysics_experiments_git'
data_save_repository    = WORKING_DIR+"Psychophysics_DATA_2024"


os.path.abspath(working_Directory)
os.chdir(       working_Directory)
sys.path.append(working_Directory)
cwd = os.getcwd()

print('============== CWD ===============================')
print('cwd:', cwd)
print('============== FILES ===============================')
print(os.listdir('.'))
print('============== FILES ===============================')



"""Initialize params:"""

pyglet.options['vsync'] = True
pyglet.options['double_buffer'] = True
win = ExpWindow(fullscreen=True)


current_time    	    = datetime.datetime.now()
today           	    = str(current_time.year)+'_'+str(current_time.month)+'_'+str(current_time.day)
print("Today date is: ", today)


"At max 500 cdm2"
listLum   = [19.0, 29,     41 , 49,    204,   255, 300,    322, 370, 403,   415]
listCPULum= [0.24,0.294, 0.34, 0.374, 0.72,  0.8, 0.86, 0.89,  0.95, 0.98, 0.99]
"At max 400 cdm2"
# listLum   = [0.3,1.0,2.6 ,5.5,  10.0, 10.2, 15.0, 20,25, 26.15,30,38,       46, 49, 50, 100 ,200,245,300,350]
# listCPULum= [0.006, 0.06, 0.1, 0.14, 0.189, 0.19, 0.259, 0.26, 0.286,  0.29,0.35,0.38, 0.39, 0.392, 0.54, 0.735,0.8,0.89,0.95]


listName  = os.listdir(data_save_repository)
listExps  = ['Flanker_Selectivity_Experiment']
listBool  = ['NEW', 'OLD']
checkDict = {'NEW_or_OLD':listBool, 'Name':listName}
boolDict  = funcs.optionPrompt(checkDict)

"""
    Below you can set:
        1. the monitor refresh rate.
        2. screen pixel width and height.
        3. the screen width and height in meters.
        4. the pixel per degree (ppd) for x and y.
        5. the viewing distance from subject to screen in meters.
        6. the aspect ratio of the screen.
        7. the pixel to meter ratio.
        8. the center of the screen in pixels (cx, cy).

"""


fullscreen              = True
logStatement            = False
SimulateBOOL            = False
monitor_refresh_rate     = 60 
pyglet_wakeup_rate_check = 180
print("Window vsync is on, target refresh:", pyglet.options['vsync']) 
print('monitor_refresh_rate:', monitor_refresh_rate)
""" Pixel: """
pixel_width             = win.width
pixel_height            = win.height
screen_width_pixel      = pixel_width
screen_height_pixel     = pixel_height
aspect_ratio            = screen_width_pixel/screen_height_pixel

""" Metre: """
metre_width             = 596.2e-3 # 610e-3 # 
metre_height            = 335.3e-3 # 350e-3 # 
screen_width_m          = metre_width
screen_height_m         = metre_height
""" Pixel: """
cx, cy                  = win.width // 2, win.height // 2 

"""
    Use Pixel per inch, then calculate 1 pixel width in meters.
    1 pixel (width) = pixel_metre_ratio
"""
print('win.width (pixel)', win.width, 'win.height (pixel)', win.height)
pixel_metre_ratio   = funcs.ratio_PIXEL_Meter(win.width, metre_width) # <- seems to give correct answer.

viewing_distance_m = 1.0

fov_x_deg = 2 * np.degrees(np.arctan((screen_width_m / 2) / viewing_distance_m))
fov_y_deg = 2 * np.degrees(np.arctan((screen_height_m / 2) / viewing_distance_m))

ppd_x     = screen_width_pixel / fov_x_deg
ppd_y     = screen_height_pixel / fov_y_deg

win.set_logger(funcs.record_event)

Experiment_TYPE = [Text((cx, cy),      Params(msg=ExperimnetTYPE+'\n')        )]
welcome_line    = [Text((cx, cy-50),   Params(msg='Press SPACE when ready.')        )]
farewell_line   = [Text((cx, cy-50),   Params(msg='Experiment over!')                     )]

trials          = []
keys_none       = []
keys_default    = [key.SPACE, key.LEFT, key.RIGHT, key.UP, key.DOWN, key.LSHIFT, key.RSHIFT] 
written_words   = [Experiment_TYPE]

trials         += [funcs.Trial_small('Start',Experiment_TYPE, 5*1000, keys_default, mouse=False)]
trials         += [funcs.Trial_small('Start',welcome_line, 0, keys_default, mouse=False)]
trial_exps      = []