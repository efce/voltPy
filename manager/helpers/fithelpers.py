import numpy as np


def calc_normal_equation_fit(xvec, yvec):
    """
    Computes polynomial 1st degree fit
    using normal equation.
    """
    xlen = len(xvec)
    assert xlen >= 3 and len(yvec) == xlen, 'xvec and yvec should have the same length.  However, len(xvec)=%i, len(yvec)=%i.' % (xlen,len(y))
    xvec = np.matrix(xvec)
    xvec = xvec.transpose()
    unitVec = np.ones((xlen, 1), dtype='float')
    X = np.concatenate((unitVec, xvec), axis=1)
    XX = np.dot(X, np.transpose(X))
    normalFit = np.linalg.pinv(XX)
    normalFit = np.dot(normalFit, X)
    normalFit = np.transpose(normalFit)
    res = np.dot(normalFit, yvec)
    return {
        'slope': res[0, 1],
        'intercept': res[0, 0]
    }


def calc_sx0(slope, intercept, xvec, yvec):
    """
    Computes standard deviation of x0 for
    slope, intercept and points [xvec, yvec]
    """
    yevec = np.polyval((slope, intercept), xvec)  # [slope*x+intercept for x in xvec]
    y0index = -1
    minx = np.min(xvec)
    if minx == 0:
        x0index = np.argmin(xvec)
    else:
        raise ValueError('Requires point with coordinates (0, y).')
    xmean = np.average(xvec)
    sr = np.sqrt(1/(len(xvec)-2) * np.sum((yi-ye)**2 for yi, ye in zip(yvec, yevec)))
    sx0 = np.multiply(
        (sr/slope),
        np.sqrt(
            1
            + 1/len(xvec)
            + (yvec[x0index]-np.average(yvec))**2
                / (slope**2*np.sum((xi-xmean)**2 for xi in xvec))
            )
    )
    return sx0


def significant_digit(value, sig_num=2):
    """
    Calculates on which decimal place is the sig_num'th significant digit
    """
    fl = -np.floor(np.log10(value))
    if fl > (0+sig_num):
        return int(0)
    else:
        return int((fl + sig_num) - 1)
