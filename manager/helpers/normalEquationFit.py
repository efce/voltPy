import numpy as np
def normalEquationFit(x, y):
    """
    Computes polynomial 1st degree fit
    using normal equation.
    """
    xlen = len(x)
    assert xlen >= 3 and len(y) == xlen, 'x and y should have the same length.  However, len(x)=%i, len(y)=%i.' % (xlen,len(y))
    x = np.matrix(x)
    x = x.transpose()
    unitVec = np.ones((xlen,1), dtype='float')
    X = np.concatenate((unitVec, x), axis=1)
    XX = np.dot(X, np.transpose(X))
    normalFit = np.linalg.pinv(XX)
    normalFit = np.dot(normalFit, X);
    normalFit = np.transpose(normalFit)
    res = np.dot(normalFit,y)
    return { 
            'slope': res[0,1], 
            'intercept': res[0,0]
           }

