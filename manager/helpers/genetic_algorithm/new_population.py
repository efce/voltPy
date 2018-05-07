import numpy as np 

def newPopulation(parents,pop,Popsize):

    newPop = np.zeros_like(pop)

    for i in range(0,Popsize):
        newPop[i,:] = pop[int(parents[0,i]),:]

    # print(newPop)

    return newPop