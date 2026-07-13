
import Functions.functionsForUse as funcs
from Events.adaptiveMethods import (retrieve_staircase_weber_contrasts)
import matplotlib as plt


def plot_staircase(file_response_record):
    data_responses      = funcs.readText_toList(file_response_record)

    stimulus_condition_history       = data_responses[0]
    probe_Alternative_Choice_history = data_responses[1]
    human_Alternative_Choice_history = data_responses[2]
    staircase_Identity_history       = data_responses[3]
    probe_weber_contrast_history     = data_responses[4]
    probe_screen_intensity_history   = data_responses[5]


    for j in range(2):
        weber_contrast_j = retrieve_staircase_weber_contrasts(staircase_Identity_history, probe_weber_contrast_history, 2)
        staircase_index_j = list(range(len(weber_contrast_j)))
        plt.scatter(staircase_index_j, weber_contrast_j)

    plt.show()