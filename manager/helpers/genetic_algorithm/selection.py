import numpy as np 

def selectionRouletteWheel(expectation,Popsize):

    wheel = np.cumsum(expectation,axis=0)/Popsize
    parents = np.zeros([1,Popsize])
    stepSize = 1/Popsize
    position = np.random.rand()*stepSize
    lowest = 0

    for i in range(0,Popsize):
        for j in range(lowest,np.size(wheel)):
            if (position < wheel[j,:]):
                parents[0,i] = j
                lowest = j
                break
        position = position + stepSize

    #print(parents)
    return parents