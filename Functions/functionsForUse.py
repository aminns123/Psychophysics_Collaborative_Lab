
class Trial_small:
    def __init__(self,name,stimuli,T,keys=[],mouse=False):
        self.stimuli    = stimuli
        self.T          = T
        self.name       = name
        self.keys       = keys
        self.mouse      = mouse
    def draw(self,win):
        win.clear()    
        for stim in self.stimuli:
            stim.draw()
    def __str__(self):
        return self.name
    def default(self):
        return {'type':'Trial','name':self.name,'keys':self.keys,'mouse':self.mouse,'stimuli':self.stimuli}


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
def record_event(event,time,trial,args):
    """
        Here I am recording data values. The pos-cx gives the relative distance from fixation point.
        In the 'Trials' for loop, the actuall position in pixel from botton left is given to set stimuli
        in the centre of screen and shift accordingly.
        Need if and elif statmemts otherwise logger fo events does not call print function.
    """
    
    """
        @ Below: Probe condition is stored - using "print_Value" function.
    """

    stimuli_names = ['staircase', 'fixateDELAY', 'dot', 'flanker_selectivity_LR']
    
    if trial.name in stimuli_names:
        trial.print_Value()
    else:
        print('============== trial stimuli found none ===============')
    
    """
        @ Below: Details the point in the experiment the participent gives a response.
    """
    response_names = ['dot_stairCase', 'flank_selectivity_Response', 'dot_constant']    

    if event != 'MOUSE' and trial.name in response_names:
        trial.print_Value()
    else:
        print('============== trial response found none ===============') 
"""
||$||
"""
def ratio_PIXEL_Meter(win_WIDTH_pixel, win_WIDTH_meter):
    # 1 pixel = 
    pixel_to_meter = win_WIDTH_meter/win_WIDTH_pixel
    return pixel_to_meter