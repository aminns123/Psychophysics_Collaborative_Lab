
import os
import json
import numpy as np


def CheckFileName(folderName, fileName):
    """
    Check if file name exist, if it does, add a number to the end of the file name to make it unique.
    """
    i = 0
    nameFile = False
    while nameFile == False:
        lengthDir       = len(os.listdir(folderName))
        filename_everytg= folderName+"/"+str(lengthDir+1+i)+fileName
        
        filename = filename_everytg
        if os.path.isfile(filename) == True:
            print(filename)
            i+=1
        elif os.path.isfile(filename) == False:
            nameFile = True
    
    index = lengthDir+1+i
    return filename_everytg, index
"""
||$|| 
"""
def check_folder_exist(folderName=[]):
    """
    Check if folder exist, if it does not, create it.
    """
    for index in range(len(folderName)):
        folderNAME = folderName[index]
        
        if not os.path.exists(folderNAME): 
            os.makedirs(folderNAME) 
        else:
            pass
"""
||$||
"""
def findCorrespondingIndex(valueList, findValue):
    """
    Find the index of the value in the list, if it does not exist, return False.
    """
    xfit_max = 0
    found = False
    for i in range(len(valueList)):
        if valueList[i] == findValue:
            xfit_max = i
            found = True
            break
        elif valueList[i] != findValue:
            found = False
            pass
    if found == True:
        pass
    elif found == False:
        xfit_max = False
    return xfit_max
"""
||$||
"""
def ProbabilitySimilarWord(lettersList1, lettersList2):
    """
    Check the probability of two words being similar by comparing the letters in the two lists.
    If the two lists are of different lengths, return False.
    """
    issueFound = True
    percentCorrect = 0.0
    if len(lettersList1) == len(lettersList2):
        countCheck = 0
        for index in range(len(lettersList1)):
            if lettersList1[index] == lettersList2[index]:
                countCheck += 1
            elif lettersList1[index] != lettersList2[index]:
                pass
        percentCorrect = (countCheck/len(lettersList1))*100
        if int(percentCorrect) == 100:
            issueFound = False
        elif int(percentCorrect) != 100:
            issueFound = True
    elif len(lettersList1) != len(lettersList2):
        pass
    return issueFound, percentCorrect
"""
||$||
"""
def checkWordForWord(listStings, wordSting):
    """
    Check if the word is in the list of strings, if it is not, check for similar words.
    If a similar word is found, return the similar word and the percentage of similarity.
    If no similar word is found, return False.
    """
    percentList = []
    issueList = []

    for word in listStings:
        contents = list(str(word))
        issueFound, percentCorrect = ProbabilitySimilarWord(
            contents, list(str(wordSting)))

        percentList.append(percentCorrect)
        issueList.append(issueFound)

    response = 'No similar word.'
    error = True
    limitFound = max(percentList)

    # for index in range(len(percentList)):
    index = findCorrespondingIndex(percentList, limitFound)

    if limitFound < 50:
        pass
    elif limitFound >= 50 and limitFound < 100:
        response = "Similar word:" + \
            str(listStings[index])+'\n'+"You have given:" + \
            str(wordSting)+'\n'+"%" + str(limitFound)
    elif int(limitFound) == 100:
        response = "%100 found:" + \
            str(listStings[index])+'\n'+"You have given:" + \
            str(wordSting)+'\n'+"%" + str(limitFound)
        error = False

    print(response)
    print("#=======#")
    return error
"""
||$||
"""
def optionPrompt(keyWords):
    """
    Option prompt for user to input values for the keys in the dictionary. 
    If the value is a list, the user can choose from the list or append a new value. 
    If the value is not a list, the user can input a new value. 
    The function will return a new dictionary with the updated values.  
    """
    NewDict = keyWords.copy()
    index = 0
    indexKey = 'nan'
    for word in keyWords.keys():
        index += 1
        print(str(index)+':'+str(word))
    checkBool = False
    error = False

    while checkBool == False:
        for word in keyWords.keys():
            if type(keyWords[str(word)]) == list:
                print('type:', type(keyWords[str(word)]), keyWords[str(word)])
                print('Choose from list, else append.')
                error = True
            else:
                pass

            if type(keyWords[str(word)]) == list:
                while error == True:
                    answer = input(word+":")
                    error = checkWordForWord(keyWords[str(word)], answer)
            else:
                answer = input('type:'+word+":")

            NewDict[str(word)] = answer

        print('Your anwsers: \n', NewDict)
        endCheck = input('Finish set up?: (yes, no)')
        if endCheck == 'yes':
            checkBool = True
        elif endCheck == 'no' or endCheck != 'yes':
            checkBool = False
    return NewDict
"""
||$||
"""
def ratio_PIXEL_Meter(win_WIDTH_pixel, win_WIDTH_meter):
    """
    Calculate the ratio of pixels to meters for a given window width in pixels and meters.
    This ratio is useful for converting between pixel and meter measurements in visual experiments.
    """
    pixel_to_meter = win_WIDTH_meter/win_WIDTH_pixel
    return pixel_to_meter
"""
||$||
"""
def from_Text(path):
    """
    Read a list of floats from a text file and return it as a list.
    The text file should contain a list in the format: [value1, value2, ..., valueN]
    """
    file            = open(path, "r")
    content         = file.read()
    res2            = list(map(float, content[1:-1].split(',')))
    file.close()
    return res2
"""
||$||
"""
def to_Text(path, response: list):
    """
    Write a list of floats to a text file.
    The list will be written in the format: [value1, value2, ..., valueN]
    """
    file = open(path, "w")
    file.write(str(response))
    file.close()
"""
    ||$||
"""
def create_Text(filename, subtitles: list):
    path = filename
    file = open(path, "w")
    
    for j in range(len(subtitles)):
        if j < len(subtitles)-1:
            file.write(subtitles[j]+':'+str([0]) + "\n" )
        elif j == len(subtitles)-1:
            file.write(subtitles[j]+':'+str([0]))
    file.close()
"""
    ||$||
"""
def create_JSON(filename, dictionary: dict):
    with open(filename, "w") as f:
        json.dump(dictionary, f, indent=4)
"""
||$||
"""
def write_toText(path, data):
    """
    Write a x-Dimensional list (matrix) to a text file, transposing it in the process.
    Each row of the matrix will be written as a line in the text file, with values separated by tabs.
    """
    file = open(path, "w")
    
    
    data =  list(map(list, zip(*data))) # Transpose list (must be a complete matrix/list, no gaps)
    
    for y in range(len(data)): # new rows 
        if (y > 0) and (y < len(data)):
            file.write('\n')
            
        for x in range(len(data[y])): # new columns
        
            if x < len(data[y])-1:
                file.write(str(data[y][x])+'\t') # want to swap col with row thus [y][x]->[x][y]
            elif x == len(data[y])-1:
                file.write(str(data[y][x]))          
    file.close()
"""
||$||
""" 

def convertArcangleTOPixel(arcAngle, distanceToMonitor, pixel_metre_ratio):
    """
    Convert visual angle in degrees to pixel distance on the screen.
    arcAngle: visual angle in degrees
    distanceToMonitor: distance from the observer to the monitor in meters
    pixel_metre_ratio: ratio of pixels to meters for the monitor
        - The formula used is based on the geometry of a right triangle formed by the observer's eye, 
        the center of the screen, and the point on the screen corresponding to the visual angle.
        The relationship is given by:
        ____________________________________
        x=tan((pi/180})*deg)*d
        x=tan(phi)*d
        x=2*tan(phi/2)*d
        phi=2arctan((x/2)*d)
        1 pixel (width) = pixel_metre_ratio
        ------------------------------------
    """
    #posRatioPixel = (np.tan(np.radians(arcAngle))*distanceToMonitor) 
    posRatioPixel = 2*(np.tan(np.radians(arcAngle)/2)*distanceToMonitor)
    return posRatioPixel/pixel_metre_ratio
"""
||$||
"""
def Meter_convertToArcangle(Meter_distanceM, distanceToMonitor, pixel_metre_ratio):
    """
    Convert a distance in meters to visual angle in degrees.
    The function takes into account the distance from the observer to the monitor and the pixel-to-meter ratio of the monitor.
        - The formula used is based on the geometry of a right triangle formed by the observer's eye, 
        the center of the screen, and the point on the screen corresponding to the visual angle.
        The relationship is given by:
        _______________________________________
        In pixels: Pixel_distanceM
        In metres: distanceToMonitor
        + Covert pixel to metre, then to arc visual angle.
        + 1 Pixel = metre: pixel_metre_ratio
        x/2=tan(2*phi)*d
        phi=2arctan((x/2)*d)
        ---------------------------------------
    """
    radians_to_degree   = 180/np.pi
    meterDist           = Meter_distanceM # *pixel_metre_ratio
    
    #arcAngle = radians_to_degree*np.arctan(meterDist/distanceToMonitor)
    arcAngle  = 2*np.arctan((meterDist/2)/distanceToMonitor)
    return arcAngle*radians_to_degree # <- added here -> radians_to_degree.