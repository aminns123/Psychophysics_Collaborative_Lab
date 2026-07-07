
import sys
import os

from pathlib import Path
import datetime
import json


WORKING_DIR     = str(Path(__file__).resolve().parent.parent)+'/'
print('WORKING_DIR', WORKING_DIR)
LOCAL_DATA_DIR  = str(Path(__file__).resolve().parent.parent.parent)+'/'
print('LOCAL_DATA_DIR', LOCAL_DATA_DIR)

working_Directory       = WORKING_DIR
data_save_repository    = LOCAL_DATA_DIR+"local_psychophysics_data"


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


# ==================================================
# ==================================================
# ==================================================
current_time    	    = datetime.datetime.now()
today           	    = str(current_time.year)+'_'+str(current_time.month)+'_'+str(current_time.day)
print("Today date is: ", today)


"At max 500 cdm2"
listLum   = [19.0, 29,     41 , 49,    204,   255, 300,    322, 370, 403,   415]
listCPULum= [0.24,0.294, 0.34, 0.374, 0.72,  0.8, 0.86, 0.89,  0.95, 0.98, 0.99]

listName  = os.listdir(data_save_repository)
listExps  = ['Contrast_Sensitivity_Function']


listBool  = ['NEW', 'OLD']
checkDict = {'NEW_or_OLD':listBool, 'Name':listName}
boolDict  = funcs.optionPrompt(checkDict)

fileExperimentLast = data_save_repository+"/"+boolDict["Name"]+"/"+"ExperimentLast.txt"


print(fileExperimentLast)
if boolDict['NEW_or_OLD'] =='OLD':
    keyValue = funcs.readText_toList_keyValue(fileExperimentLast)
    keyList   =keyValue[0]
    valueList =keyValue[1]
    newDict = {}
    for j in range(len(keyList)):
        newDict.update({keyList[j]:valueList[j]})

elif boolDict['NEW_or_OLD']=='NEW':
    checkDict = {'Experiment_Type':listExps , 
                 'Luminance': listLum, 
                 'Screen_intensity': listCPULum
    }
    newDict   = funcs.optionPrompt(checkDict)

    newDict.update({'Name':boolDict['Name'],
                    'trialPOINT':9, # 8 , # 5
                    'start_Cw':1.0,
                    'stimulus_SF': 1.0,
                    'date_created':today,
                    'index_last_PosList':0,
                    'Npoints':12,
                    'positionBool':1, 
                    'positionFind':1})

print('--------------------------------')
print('newDict:\n', newDict)   

fileExperimentLast  = data_save_repository+"/"+boolDict["Name"]+"/"+"ExperimentLast.txt"
filePosition        = data_save_repository+"/"+boolDict["Name"]+"/"+"ExpLast_positionPixel.txt"

with open(data_save_repository+"/"+boolDict["Name"]+"/"+"experiment_defined.json", "w") as f:
    json.dump(newDict, f, indent=4)

NAME = boolDict['Name']
