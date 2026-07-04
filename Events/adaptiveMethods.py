

import os
import sys

import numpy as np



"""
||$|| 
"""
def rate_dw(rateDW, reversals, reversePOINT):
    value = 0.3
    if reversals < reversePOINT:
        value = 0.3
    elif reversals >= reversePOINT:
        value = rateDW # 0.5
    return value
"""
||$|| 
"""
def conditionRateUPDW(nowLUM, prevLUM, rate, stepDWUP, logUNIT, condRule):
    if int(condRule) == 0:
        value = (nowLUM+prevLUM)*rate
    elif int(condRule) == 1:
        value = nowLUM+stepDWUP
    elif int(condRule) == 2:
        value = nowLUM*pow(10, logUNIT)
    elif int(condRule) == 3:
        value = nowLUM*pow(10, np.log10(1+logUNIT))
    return value
"""
||$|| 
"""
def defineReversal_Multi(data_Store, stepBacks): # uses entire file
    starT       = len(data_Store[0])-2 # len(data_Store)-2
    enD         = 0
    ranGE       = list(range(starT,enD, -1))
    storeData   = data_Store
    
    probe_pos_list  = storeData[0]
    probe_LR_list   = storeData[1]
    human_LR_list   = storeData[2]
    admID_List      = storeData[4]
    
    correctTick_list= storeData[10]
    
    admIDNow        = int(admID_List[len(admID_List)-1])
    posItionNow     = storeData[0][len(storeData[0])-1]
    lumNow          = storeData[6][len(storeData[6])-1] # <-- new line
    
    stop  = False
    index = 0
    count = 0  
    INDEXcorrect    = 0
    INDEXwrong      = 0
    
    foundIndex      = False
    j               = len(probe_pos_list)-1 # len(correctTick_list)-1
    while foundIndex == False: 
        #
        """
            Here we find the last incorrect with respect to positiona and admID was used.
        """
        #
        if j > 0:
            j += -1
            
            probe_LR = probe_LR_list[j]
            human_LR = human_LR_list[j]
            #probePos = probe_pos_list[j]
            admID    = int(admID_List[j])
            
            if (probe_LR != human_LR) and (admID == admIDNow):

                INDEXwrong = j # -1
                
                if storeData[6][INDEXcorrect] > lumNow: # <-- new line
                    foundIndex = True
                    break
                elif storeData[6][INDEXcorrect] <= lumNow: # <-- new line
                    pass
            elif (probe_LR == human_LR) and (admID == admIDNow):
                INDEXcorrect = j # -1
                
            elif (admID != admIDNow):
                pass
        elif j == 0:
            INDEXcorrect = 1
            foundIndex   = True
            break
    return INDEXcorrect, INDEXwrong
"""
|$|
"""
def count_reversals_HighLow(contrastList):
    averageList = []
    TrialNumber = []
    countR      = 0
    checkSign   = 0
    signValue   = -1
    
    j           = 0
    
    if len(contrastList) > 1:
        if contrastList[j+1]-contrastList[j] < 0: # i.e. N12 - N10, then get  j-1
            signValue = -1
        elif contrastList[j+1]-contrastList[j] > 0: 
            signValue = 1
        elif contrastList[j+1]-contrastList[j] == 0: 
            pass
            
        checkSign = signValue
        j         = 0
        while j < len(contrastList)-2:
            j+=1
            if contrastList[j+1]-contrastList[j] < 0: # i.e. N12 - N10, then get  j-1
                signValue = -1
            elif contrastList[j+1]-contrastList[j] > 0: 
                signValue = 1
            elif contrastList[j+1]-contrastList[j] == 0: 
                pass
            
            if checkSign != signValue:
                checkSign = signValue 
                countR   += 1
                averageList.append(contrastList[j])
                TrialNumber.append(j)
            elif checkSign == signValue:
                pass
    elif len(contrastList) <= 1:
        TrialNumber=[1]
        TrialNumber=[0]
        averageList=[0] 
        
    return len(TrialNumber), TrialNumber, averageList 
"""
|$|
"""       
def weberContrast(contrast_cpu: list, background_crt, max_crt, logFunction, logStatment: bool):
    maxC        = max_crt # max(contrast_cpu)
    contrast_W  = []
    if logStatment == False:
        for i in range(len(contrast_cpu)):
            contrast_W.append((contrast_cpu[i]-background_crt)/(maxC-background_crt))
    elif logStatment == True:
        for i in range(len(contrast_cpu)):
            contrast_W.append(logFunction((contrast_cpu[i]-background_crt)/(maxC-background_crt)))
    return contrast_W
"""
||$|| 
"""      
def admID_staircase(adm_list, contrast_list, admIDNow):
    contrastComb = []
    """
    for n in range(0, len(adm_list), 1):
        probePos = pos_list[n] 
        admID    = int(adm_list[n])
        if (abs(probePos) == abs(posItionNow)) and (admID == admIDNow):
                
            contrastComb.append(contrast_list[n])
        elif (abs(probePos) != abs(posItionNow)) or  (admID != admIDNow):
            continue   
    """
    for n in range(0, len(adm_list), 1):
        admID    = int(adm_list[n])
        if (admID == admIDNow):   
            contrastComb.append(contrast_list[n])
        elif (admID != admIDNow):
            continue 
    return contrastComb
"""
||$|| 
"""
def findIndex(arrayList, indexNow):
    indexPOSfound = 0
    for i in range(len(arrayList)):
        if int(indexNow) == int(arrayList[i]):
            indexPOSfound = i
            break
        elif int(indexNow) != int(arrayList[i]):
            pass
    return indexPOSfound
"""
||$|| 
"""
def findIndexFloat(arrayList, indexNow):
    indexPOSfound = 0
    for i in range(len(arrayList)):
        if (indexNow) == (arrayList[i]):
            indexPOSfound = i
            break
        elif (indexNow) != (arrayList[i]):
            pass
    return indexPOSfound
"""
|$|
"""   
def returnOnce(lisT):
    newList = []
    for i in range(len(lisT)):
        value = abs(lisT[i])
        if value not in newList:
            newList.append(value)
        elif value in newList:
            continue
    return newList
"""
||$||
"""
def count_Abs_type(count_type_array):
    checkedValues = []
    checkekCounts = []
    for i in range(len(count_type_array)):
        if abs(count_type_array[i][0]) not in checkedValues:
            checkedValues.append(abs(count_type_array[i][0]))
            checkekCounts.append(count_type_array[i][1])
        elif abs(count_type_array[i][0]) in checkedValues:
            indexfound                = findIndexFloat(checkedValues, abs(count_type_array[i][0])) 
            checkekCounts[indexfound] = checkekCounts[indexfound] + count_type_array[i][1]
    
    returnType = []
    for i in range(len(checkedValues)):
        e1 = checkedValues[i]
        e2 = checkekCounts[i]
        returnType.append([e1, e2])
    return returnType
"""
||$||
"""
def appendTrials(trails):
    arrayT = []
    for i in range(0, len(trails), 1):
        arrayT.append(trails[i][0])
    return arrayT  
"""
||$||
"""
def count_values_type(list_of_values, value_array, startIndex):
    count_type_array = []
    total            = 0
    for z in range(len(value_array)):
        count = 0.0
        for i in range(startIndex, len(list_of_values), 1):
            if list_of_values[i] == value_array[z]:
                count += 1
            elif list_of_values[i] != value_array[z]:
                continue
        count_type_array.append([value_array[z], count])
    for index in range(len(count_type_array)):
        total += count_type_array[index][1]
    return count_type_array, total
"""
||$||
""" 
def check_values(value_array):
    new_array = []

    for i in range(len(value_array)):
        if  value_array[i] not in new_array:
            new_array.append(value_array[i])
        elif value_array[i] in new_array:
            continue
    return new_array
"""
||$|| 
"""

def conditions(storeData, dataParams, conditionS):
    probeStart = dataParams[4]
    rateDW = dataParams[6]
    rateUP = dataParams[10]

    bkg_contrast = dataParams[12]
    max_contrast = dataParams[13]
    bkg_cpu, max_cpu = bkg_contrast, max_contrast
    logStatement = False
    logFunction = np.log10  # dataParams[25]

    reversePOINT = dataParams[14]
    nUP = dataParams[15]
    stepDWUP = dataParams[21]
    condRule = dataParams[22]
    logUNIT_UP = dataParams[23]
    logUNIT_DW = dataParams[24]

    preReversalStep = dataParams[28]
    conditionBool = dataParams[29]
    trialPOINT = dataParams[30]

    count_Reversals_List = storeData[3]
    reversalN = storeData[8][len(storeData[8])-1]

    rDW = storeData[5][len(storeData[5])-1]
    probe_pos_list = storeData[0]
    probe_LR_list = storeData[1]
    human_LR_list = storeData[2]
    contrast_list = storeData[6]
    admID_List = storeData[4]

    reversals_list = storeData[3]
    reverCount_list = storeData[8]
    paramStart_list = storeData[9]
    correctTick_list = storeData[10]

    listSize = len(probe_LR_list)
    j = len(correctTick_list)

    admIDNow = int(admID_List[len(admID_List)-1])
    posItionNow = storeData[0][len(storeData[0])-1]

    startIndex = 1
    checked_ids = check_values(storeData[4])
    n_types_ids, totaln = count_values_type(
        storeData[4], checked_ids, startIndex)
    arrayID = appendTrials(n_types_ids)
    valueN = 1  # nUP or 1

    checked_pos = check_values(storeData[0])
    n_types_pos, totaln = count_values_type(
        storeData[0], checked_pos, startIndex)
    n_types_pos = count_Abs_type(n_types_pos)
    arrayPOS = appendTrials(n_types_pos)
    arrayPOS = returnOnce(arrayPOS)

    indexPOSfound = findIndexFloat(arrayPOS, abs(posItionNow))
    indexIDfound = findIndex(arrayID, admIDNow)

    """
    Here we find the associated webercontrast for the ADM given.
    """
    contrast_adm = admID_staircase(admID_List, contrast_list, admIDNow)
    weberLIST_TH = weberContrast(
        contrast_adm, bkg_contrast, max_contrast, logFunction, logStatement)
    totalReverses = count_reversals_HighLow(weberLIST_TH)[0]

    # print('posItionNow: ',posItionNow)
    # print('pos found: ',  n_types_pos[indexPOSfound],' index: ', indexPOSfound)
    # print('admIDNow: ',   admIDNow)
    # print('n_types_ids: ',n_types_ids[indexIDfound],  ' index: ', indexIDfound)

    # {===========STEP 1==============}
    if (n_types_ids[indexIDfound][1] >= valueN):
        foundIndex = False

        while foundIndex == False:
            #
            """
                Here we find the last time the correctTick with respect to position and admID that was used.
                I.e., find 'correctTick'. <-- main thing needed from here.
                Thus, here deals with the previous response.
                j < 0 means this ADM at this position hasn't happened before.
            """
            #
            j += -1
            if j >= 0:
                probePos = probe_pos_list[j]  # +1
                admID = int(admID_List[j])
                if (admID == admIDNow):  # (abs(probePos) == abs(posItionNow)) and

                    reversals_total = reversals_list[j]
                    reversalN = reverCount_list[j]
                    paramStart = paramStart_list[j]
                    correctTick = correctTick_list[j]
                    count_Reversals_total = count_Reversals_List[j]
                    foundIndex = True
                    break
                elif (admID != admIDNow):  # (abs(probePos) != abs(posItionNow)) or
                    pass

            elif j < 0:
                cL = probeStart
                paramStart = 0
                correctTick = correctTick_list[0]  # 0
                count_Reversals_total = 0
                break

    elif (n_types_ids[indexIDfound][1] < valueN):
        cL = probeStart
        paramStart = 0
        correctTick = correctTick_list[0]  # 0
        count_Reversals_total = 0
    # ====
    # ====
    bkg = bkg_contrast
    wrong = False
    count = 0
    dataMatrix = storeData
    # {===========STEP 2==============}
    if (n_types_ids[indexIDfound][1] >= nUP):
        j = listSize
        jIndex = 0

        # rev_COUNT, rev_LIST, rev_CONTR
        # totalReverses   = count_reversals_HighLow(weberLIST_TH)[0]

        while jIndex < nUP+1:  # <=
            j += -1
            if j > 0:
                #
                """
                    Here we find the last time the contrast with respect to position and admID was used.
                    As well as the LR response for those consecutive index's.
                    Thus, here deals with the now response.
                """
                #
                probe_LR = probe_LR_list[j]
                human_LR = human_LR_list[j]
                probePos = probe_pos_list[j]
                admID = int(admID_List[j])

                # and (abs(probePos) == abs(posItionNow))
                if (probe_LR == human_LR) and (admID == admIDNow):
                    count += -1
                    jIndex += 1
                # and (abs(probePos) == abs(posItionNow))
                elif (probe_LR != human_LR) and (admID == admIDNow):
                    count += +1
                    jIndex += 1
                elif (admID != admIDNow):  # (abs(probePos) != abs(posItionNow)) or
                    pass
            elif j == 0:
                break

        lastIndex = len(probe_LR_list)-1  # <------ new
        probePos = probe_pos_list[lastIndex]
        admID = int(admID_List[lastIndex])

        # and ((probePos) == (posItionNow))
        if (probe_LR_list[lastIndex] != human_LR_list[lastIndex]) and (admID == admIDNow):
            wrong = True
        # and ((probePos) == (posItionNow))
        elif (probe_LR_list[lastIndex] == human_LR_list[lastIndex]) and (admID == admIDNow):
            wrong = False
        base_cL = contrast_list[lastIndex]

    elif (n_types_ids[indexIDfound][1] < nUP):
        # int(n_types_ids[indexIDfound][1])-1 ## <- new code : -1. new code: 0
        totalReverses = 0
        # pass

        """
            Here, either the id has only shown once or twice, or none at all.
            Thus is been seen/recorded for the first time.
            Thus, here deals with the now response.
        """

        lastIndex = len(probe_LR_list)-1  # <------ new
        if probe_LR_list[lastIndex] != human_LR_list[lastIndex]:
            wrong = True
        elif probe_LR_list[lastIndex] == human_LR_list[lastIndex]:
            wrong = False
        base_cL = contrast_list[lastIndex]
    # {===========STEP 3==============}
    """
        # Add code: here give webercontrast, apply log unit step, then convert back to cpu luminace intensity.
    """

    if conditionS == True:
        if int(paramStart) == 0:
            crt_Prev_UP = probeStart
            paramStart += 1
        elif int(paramStart) != 0:
            # reversalN --> !!! (old, still in code but NOT USED) !!!
            crt_index, INDEXwrong = defineReversal_Multi(dataMatrix, reversalN)
            crt_Prev_UP = contrast_list[crt_index]  # +1
            crt_Prev_wrong = contrast_list[INDEXwrong]  # +1
            ### New CODE: ####
            crt_Prev_wrong = weberContrast(
                [crt_Prev_wrong], bkg_cpu, max_cpu, np.log10, False)[0]
            """
                Here we find the last time the contrast with respect to positiona and admID was used.
                As well as the index of the last mistake, then an index + (wrt position and ID), to get the peak up.
            """

        crt_Prev_UP = weberContrast(
            [crt_Prev_UP], bkg_cpu, max_cpu, np.log10, False)[0]
        ### New CODE: ####
        base_cL = weberContrast(
            [base_cL], bkg_cpu, max_cpu, np.log10, False)[0]
        bkg_web = weberContrast(
            [bkg_cpu], bkg_cpu, max_cpu, np.log10, False)[0]
        max_web = weberContrast(
            [max_cpu], bkg_cpu, max_cpu, np.log10, False)[0]

        ##### ===========######
        if (wrong == True):
            count_Reversals_total = totalReverses  # += 1
            correctTick = 0
            if totalReverses >= reversePOINT:
                cL_param_new = conditionRateUPDW(
                    base_cL, crt_Prev_UP, rateUP, stepDWUP, logUNIT_UP, condRule)
            elif totalReverses < reversePOINT:
                cL_param_new = conditionRateUPDW(
                    base_cL, crt_Prev_UP, rateUP, stepDWUP, logUNIT_UP, condRule)

            reversalN += 1
            print('wrong: base_cL     :', base_cL)
            print('wrong: cL_param_new:', cL_param_new)
            print('wrong: bkg_web     :', bkg_web)
        ##### ===========######
        elif (wrong == False):
            count_Reversals_total = totalReverses  # += 0

            # if (count < nUP) and (correctTick >= nUP):  # Previous: (count <= -nUP) and (correctTick >= nUP):
            print('totalReverses: ', totalReverses)
            print('reversePOINT: ', reversePOINT)

            """
            Here is for the beginning of the experiment.
            """
            if conditionBool == 0:
                conditionNOW = totalReverses
                conditionPOINT = reversePOINT
            elif conditionBool == 1:
                conditionNOW = n_types_ids[indexIDfound][1]
                conditionPOINT = trialPOINT
            else:
                conditionNOW = totalReverses
                conditionPOINT = reversePOINT

            if (conditionNOW >= conditionPOINT) or (totalReverses >= reversePOINT):
                if (correctTick >= nUP):
                    correctTick = 0
                    reversalN = 1

                    rDW = rate_dw(rateDW, totalReverses, reversePOINT)
                    cL_param_new = conditionRateUPDW(
                        base_cL, crt_Prev_wrong, rDW, -1*stepDWUP, -1*logUNIT_DW, condRule)

                elif (correctTick < nUP):
                    cL_param_new = base_cL
                    correctTick += 1

            elif (conditionNOW < conditionPOINT) and (totalReverses < reversePOINT):
                rDW = rate_dw(rateDW, totalReverses, reversePOINT)
                cL_param_new = conditionRateUPDW(
                    base_cL, bkg_web, rDW, -1*stepDWUP, -1*preReversalStep, condRule)
                correctTick = 0

            # print('=======')
            # print('correct: base_cL     :', base_cL)
            # print('correct: cL_param_new:', cL_param_new)
            # print('correct: bkg_web     :', bkg_web)
    # {==========================}
    # =========================== Below without ticks
    weberCRT = cL_param_new
    cpu_LUM = findCPU_fromWeberContrast(max_cpu, bkg_cpu, weberCRT)
    cL_param_new = cpu_LUM

    if cL_param_new < bkg_cpu:
        cL_param_new = bkg_cpu
    elif cL_param_new >= bkg_cpu:
        pass

    reversalTick = reversalN
    return cL_param_new, reversalTick, correctTick, paramStart, rDW, count, count_Reversals_total, rateUP
"""
||$||
"""
def findCPU_fromWeberContrast(maxCPU, bkgCPU, weberCRT):
    value = ((maxCPU-bkgCPU)*weberCRT)+bkgCPU
    return value