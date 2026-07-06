
import numpy as np


def findCorrespondingIndex(valueList, findValue):
    # return index
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
    # 1 pixel = 
    pixel_to_meter = win_WIDTH_meter/win_WIDTH_pixel
    return pixel_to_meter
"""
||$||
"""
def from_Text(path):
    file            = open(path, "r")
    content         = file.read()
    res2            = list(map(float, content[1:-1].split(',')))
    file.close()
    return res2
"""
||$||
"""
def to_Text(path, response: []): # allows all other fucntion to access response
    file = open(path, "w")
    file.write(str(response))
    file.close()
"""
||$||
"""
def write_toText(path, data):
    file = open(path, "w")
    
    colS = 0
    rowS = 0
    
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
    x=tan((pi/180})*deg)*d
    x=tan(phi)*d
    x=2*tan(phi/2)*d
    phi=2arctan((x/2)*d)
    1 pixel (width) = pixel_metre_ratio
    """
    #posRatioPixel = (np.tan(np.radians(arcAngle))*distanceToMonitor) 
    posRatioPixel = 2*(np.tan(np.radians(arcAngle)/2)*distanceToMonitor)
    return posRatioPixel/pixel_metre_ratio
"""
||$||
"""
def Meter_convertToArcangle(Meter_distanceM, distanceToMonitor, pixel_metre_ratio):
    """
    In pixels: Pixel_distanceM
    In metres: distanceToMonitor
    + Covert pixel to metre, then to arc visual angle.
    + 1 Pixel = metre: pixel_metre_ratio
    x/2=tan(2*phi)*d
    """
    radians_to_degree   = 180/np.pi
    meterDist           = Meter_distanceM # *pixel_metre_ratio
    
    #arcAngle = radians_to_degree*np.arctan(meterDist/distanceToMonitor)
    arcAngle  = 2*np.arctan((meterDist/2)/distanceToMonitor)
    return arcAngle*radians_to_degree # <- added here -> radians_to_degree.