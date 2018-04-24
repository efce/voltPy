import numpy as np
from scipy.optimize import curve_fit


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
    Computes standard deviation of x0, slope, and intercept
    for slope, intercept and points [xvec, yvec]
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
    sxx = np.sum(np.power(np.subtract(xvec, xmean), 2))
    sx0 = np.multiply(
        (sr/slope),
        np.sqrt(
            1
            + 1/len(xvec)
            + (yvec[x0index]-np.average(yvec))**2
                / (slope**2*np.sum((xi-xmean)**2 for xi in xvec))
            )
    )
    sSlope = np.divide(sr, np.sqrt(sxx))
    sIntercept = sr * np.sqrt(np.sum(np.power(xvec, 2))/(len(xvec)*sxx))
    return sx0, sSlope, sIntercept


def significant_digit(value, sig_num=2):
    """
    Calculates on which decimal place is the sig_num'th significant digit
    """
    fl = -np.floor(np.log10(value))
    if fl + sig_num < 0:
        return int(0)
    return int((fl + sig_num) - 1)


def fit_capacitive_eq(
        xvec,
        yvec,
        dE=1,
        initialR=100,
        initialTau=1,
        initialEps=0.001,
        Romega_bounds=(0, np.inf),
        tau_bounds=(0, np.inf),
        teps_bounds=(-10, 10)):

    def capacitive(x, Rom, eps, tau):
        dEoR = np.divide(dE, Rom)
        power_of = np.divide(np.add(-x, eps), tau)
        ret = np.dot(dEoR, np.exp(power_of))
        return ret

    p0 = (initialR, initialEps, initialTau)

    capacitive_bounds = list(zip(Romega_bounds, teps_bounds, tau_bounds))

    capac_fit, capac_cov = curve_fit(
        f=capacitive,
        xdata=xvec,
        ydata=yvec,
        p0=p0,
        bounds=capacitive_bounds,
    )

    return capac_fit, capac_cov


def fit_faradaic_eq(
        xvec,
        yvec,
        initialA=30,
        initialEps=0,
        A_bounds=(-np.inf, np.inf),
        Eps_bounds=(-2, 2)):

    faradaic_bounds = list(zip(A_bounds, Eps_bounds))
    p0 = (initialA, initialEps)

    def faradaic(t, a, eps):
        return np.dot(a, np.sqrt(np.add(t, eps)))

    farad_fit, farad_cov = curve_fit(
        f=faradaic,
        xdata=xvec,
        ydata=yvec,
        bounds=faradaic_bounds,
        p0=p0
    )

    return farad_fit, farad_cov
