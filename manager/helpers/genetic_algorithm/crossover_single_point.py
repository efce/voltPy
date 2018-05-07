import numpy as np 
import math

def crossoverSinglePoint(parents,pop,CrossP):

    [m,n] = pop.shape
    Pc = int(np.round(CrossP * parents.size))
    
    # Selekcja do krzyzowania
    points = np.random.permutation(parents.size)
    toCross = points[0:Pc]
    noToCross = points[Pc:]
    popToCross = np.zeros([Pc,n])
    popNotToCross = np.zeros([m-Pc,n])
    for i in range(0,Pc):
        popToCross[i,:] = pop[toCross[i],:]
    for j in range(0,m-Pc):
        popNotToCross[j,:] = pop[noToCross[j],:]
    
    # Krzyzowanie
    newPop = np.zeros([Pc,n])
    pr = np.zeros([2,Pc])
    temp = np.arange(0,Pc)
    pr[0,:] = temp
    pr[1,:] = temp[::-1]
    for i in range(0,Pc):
        pr1 = popToCross[int(pr[0,i]),:]
        pr2 = popToCross[int(pr[1,i]),:]
        breakPoint = math.ceil(np.random.rand()*(n-1))
        newPop[i,:] = np.concatenate([pr1[0:breakPoint], pr2[breakPoint:]])

    # Populacja po krzyzowaniu
    popAfterCross = np.concatenate((newPop, popNotToCross), axis=0)

    return popAfterCross