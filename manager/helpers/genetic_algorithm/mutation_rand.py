import numpy as np 
import math

def mutationRand(parents,pop,MutP):

    [m,n] = pop.shape
    Pm = int(np.round(MutP * parents.size))
    if Pm < 1:
        Pm = 1
    
    # Selekcja do mutacji
    points = np.random.permutation(parents.size)
    toMut = points[0:Pm]
    noToMut = points[Pm:]
    popToMut = np.zeros([Pm,n])
    popNotToMut = np.zeros([m-Pm,n])
    for i in range(0,Pm):
        popToMut[i,:] = pop[toMut[i],:]
    for j in range(0,m-Pm):
        popNotToMut[j,:] = pop[noToMut[j],:]
    
    # Mutacja
    for i in range(0,Pm):
        breakPoint = math.ceil(np.random.rand()*(n-1))
        if popToMut[i,breakPoint] == 1:
           popToMut[i,breakPoint] = 0
        else:
           popToMut[i,breakPoint] = 1 

     # Populacja po mutacji
    popAfterMut = np.concatenate((popToMut, popNotToMut), axis=0)

    return popAfterMut