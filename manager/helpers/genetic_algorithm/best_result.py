import numpy as np 
from scipy.interpolate import CubicSpline
from scipy.interpolate import InterpolatedUnivariateSpline
# import matplotlib.pyplot as plt

def bestResult(bestChrom,signals,Pmax):
    [m,n] = signals.shape
    
    # dodanie pierwszego i ostatniego punktu
    bestChrom[0] = 1
    bestChrom[n-1] = 1

    xx = np.linspace(1,n,n)
    bkg = np.zeros_like(signals)
    signalsWithoutBkg = np.zeros_like(signals)

    X = np.zeros([m,np.count_nonzero(bestChrom)])
    Y = np.zeros([m,np.count_nonzero(bestChrom)])
    ind = 0
    for i in range(0,n):
        if bestChrom[i] == 1:
            X[0:m,ind] = i+1
            Y[:,ind] = signals[:,i]
            ind = ind + 1   

    for j in range(0,m):
        # tło dopasowywane splajnami 3-ego stopnia (cubic spline)
        #f2 = InterpolatedUnivariateSpline(X[j,:], Y[j,:])
        f2 = CubicSpline(X[j,:], Y[j,:], extrapolate=True)
        bkg[j,:] = f2(xx)
        signalsWithoutBkg[j,:] = signals[j,:] - bkg[j,:]
    
    """
    plt.subplot(121)
    plt.plot(xx,signals.T,'-b')
    plt.plot(xx,bkg.T,'-r')
    plt.scatter(X,Y)
    plt.subplot(122)
    plt.plot(xx,signalsWithoutBkg.T)
    plt.show()
    """

    return (signalsWithoutBkg,bkg)