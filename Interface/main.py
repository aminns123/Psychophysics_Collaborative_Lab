
import sys
import os

from pathlib import Path
import datetime
import json
import importlib


WORKING_DIR     = str(Path(__file__).resolve().parent.parent)+'/'
print('WORKING_DIR', WORKING_DIR)
LOCAL_DATA_DIR  = str(Path(__file__).resolve().parent.parent.parent)+'/'
print('LOCAL_DATA_DIR', LOCAL_DATA_DIR)

working_Directory       = WORKING_DIR
data_save_repository    = LOCAL_DATA_DIR+"local_psychophysics_data"
EXPERIMENT_DIRECTORY    = WORKING_DIR+"Experiments"

os.path.abspath(working_Directory)
os.chdir(       working_Directory)
sys.path.append(working_Directory)
cwd = os.getcwd()

print('============== CWD ===============================')
print('cwd:', cwd)
print('============== FILES ===============================')
print(os.listdir('.'))
print('============== FILES ===============================')

import Functions.functionsForUse as funcs
from Interface.config import run_configure_experiment

# ------------------------------ Experiment setup ------------------------------

current_time    	    = datetime.datetime.now()
today           	    = str(current_time.year)+'_'+str(current_time.month)+'_'+str(current_time.day)
print("Today date is: ", today)


"At max 500 cdm2"
listLum   = [19.0, 29,     41 , 49,    204,   255, 300,    322, 370, 403,   415, 500]
listCPULum= [0.24,0.294, 0.34, 0.374, 0.72,  0.8, 0.86, 0.89,  0.95, 0.98, 0.99]

listName  = os.listdir(data_save_repository)

listExperiments = os.listdir(EXPERIMENT_DIRECTORY)

listBool  = ['NEW', 'OLD']
checkDict = {'NEW_or_OLD':listBool, 'Name':listName}
boolDict  = funcs.optionPrompt(checkDict)

fileExperimentLast = data_save_repository+"/"+boolDict["Name"]+"/"+"ExperimentLast.txt"
print(fileExperimentLast)

if boolDict['NEW_or_OLD'] =='OLD':
    keyValue = funcs.readText_toList_keyValue(fileExperimentLast)
    keyList   =keyValue[0]
    valueList =keyValue[1]
    setupDict = {}
    for j in range(len(keyList)):
        setupDict.update({keyList[j]:valueList[j]})

elif boolDict['NEW_or_OLD']=='NEW':
    checkDict = {'Experiment_Type':listExperiments,
                 'Max_monitor_Luminance': listLum, 
                 'Background_Luminance': listLum, 
                 'Screen_intensity': listCPULum
    }
    setupDict   = funcs.optionPrompt(checkDict)

    setupDict.update({'Name':boolDict['Name'],
                    'trialPOINT':9, # 8 , # 5
                    'starting_screen_intensity':1.0,
                    'stimulus_SF': 1.0,
                    'date_created':today,
                    'index_last_PosList':0,
                    'reversal_termination':10,
                    'Npoints':12,
                    'positionBool':1, 
                    'positionFind':1})

print('--------------------------------')
print('setupDict:\n', setupDict)   

fileExperimentLast  = data_save_repository+"/"+boolDict["Name"]+"/"+"ExperimentLast.txt"
filePosition        = data_save_repository+"/"+boolDict["Name"]+"/"+"ExpLast_positionPixel.txt"

NAME            = boolDict['Name']
EXPERIMENT_TYPE = setupDict['Experiment_Type']
module_name     = f"Experiments.{EXPERIMENT_TYPE}"
experiment      = importlib.import_module(module_name)

with open(data_save_repository+"/"+boolDict["Name"]+"/"+"experiment_defined.json", "w") as f:
    json.dump(setupDict, f, indent=4)

filename_Conditions, file_params_Stimulus, file_response_record = run_configure_experiment(NAME, data_save_repository, setupDict)

#experiment.run_experiment(filename_Conditions, file_params_Stimulus, file_response_record, data_save_repository)

print('============== CWD ===============================')
print('cwd:', os.getcwd())
print('============== FILES ===============================')
print(os.listdir('.'))
print('============== sys ===============================')
print(sys.path[0])