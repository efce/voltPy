import numpy as np 
from scipy.interpolate import CubicSpline
from scipy.interpolate import InterpolatedUnivariateSpline

def fitnessFunction(pop,x,Pmax,Pb,Pe):

    [m,n] = pop.shape
    [m2,n2] = x.shape
    interv = 5
    sk = m2-1

    bkg = np.zeros([1,n2])
    bkgsub = np.zeros([1,n2])
    PeakH = np.zeros([m,1])
    symt = np.zeros([1,interv])
    symt2 = np.zeros([m,1])
    xx = np.linspace(1,n,n)

    for i in range(0,m):
        c1 = np.count_nonzero(pop[i,:])
        X = np.zeros(c1)
        Y = np.zeros(c1)
        ind = 0
        for j in range(0,n):
            if (pop[i,j] == 1):
                X[ind] = j+1
                Y[ind] = x[sk,j]
                ind = ind + 1
        
        # tło dopasowywane splajnami 3-ego stopnia (cubic spline)
        #f2 = InterpolatedUnivariateSpline(X, Y)
        f2 = CubicSpline(X, Y, extrapolate=True)
        bkg = f2(xx)
        bkgsub = x[sk,:] - bkg
        PeakH[i,:] = x[sk,Pmax] - bkg[Pmax]
        temp1 = np.absolute(bkgsub[Pe:Pe+5])
        symt = np.absolute(bkgsub[Pb-interv:Pb]) - temp1[::-1]
        symt2[i,:] = np.absolute(np.sum(symt))

    scores = -0.6*PeakH + 0.4*symt2

    return scores

    # [m,n] = pop.shape
    # [m2,n2] = x.shape
    # interv = 5

    # bkg = np.zeros_like(x)
    # bkgsub = np.zeros_like(x)
    # PeakH = np.zeros([m2,1])
    # symt = np.zeros([m2,interv])
    # symt2 = np.zeros([m2,1])
    # symt3 = np.zeros([m,1])
    # PeakH2 = np.zeros([m,1])
    # xx = np.linspace(1,n,n)

    # for i in range(0,m):
    #     c1 = np.count_nonzero(pop[i,:])
    #     X = np.zeros([1,c1])
    #     Y = np.zeros([m2,c1])
    #     ind = 0
    #     for j in range(0,n):
    #         if (pop[i,j] == 1):
    #             X[0,ind] = j+1
    #             Y[:,ind] = x[:,j]
    #             ind = ind + 1
        
    #     for k in range(0,m2):
    #         # tło dopasowywane splajnami 3-ego stopnia (cubic spline)
    #         f2 = CubicSpline(X[0,:], Y[k,:])
    #         bkg[k,:] = f2(xx)
    #         bkgsub[k,:] = x[k,:] - bkg[k,:]
    #         PeakH[k,:] = x[k,Pmax] - bkg[k,Pmax]
    #         temp1 = np.absolute(bkgsub[k,Pe:Pe+5])
    #         symt[k,:] = np.absolute(bkgsub[k,Pb-interv:Pb]) - temp1[::-1]
    #         symt2[k,:] = np.absolute(np.sum(symt[k,:]))

    #     PeakH2[i,:] = np.sum(PeakH)
    #     symt3[i,:] = np.sum(symt2)
    # scores = -0.6*PeakH2 + 0.4*symt3
    # return scores


