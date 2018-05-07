import numpy as np 

def fitScaling(scores,Popsize):

    [m,n] = scores.shape
    # st = np.sort(scores,axis=0)
    index = np.argsort(scores,axis=0) 

    expectation = np.zeros_like(scores)

    temp = np.linspace(1,m,m)
    for i in range(0,m):
        expectation[index[i,:],:] = 1/np.power(temp[i],0.5)

    expectation = Popsize*expectation/np.sum(expectation)

    #print(expectation)

    return expectation