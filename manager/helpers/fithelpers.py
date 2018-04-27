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
    fl = -np.floor(np.log10(np.abs(value)))
    if fl + sig_num < 0:
        return int(0)
    return int((fl + sig_num) - 1)


def calc_capacitive(x, dE, Rom, teps, tau, yeps):
    dEoR = np.divide(dE, Rom)
    power_of = np.divide(-x, np.add(tau, teps))
    ret = np.add(np.dot(dEoR, np.exp(power_of)), yeps)
    return ret


def fit_capacitive_eq(
        xvec,
        yvec,
        dE=1,
        initialR=100,
        initialTau=1,
        initialEps=1E-10,
        Romega_bounds=(0, np.inf),
        tau_bounds=(0, np.inf),
        teps_bounds=(-1, 1)):

    p0 = (initialR, initialEps, initialTau, np.min(yvec))

    capacitive_bounds = list(zip(Romega_bounds, teps_bounds, tau_bounds, (np.min(yvec), np.max(yvec))))

    def calc_capacitive_part(x, Rom, teps, tau, yeps, dE=dE):
        return calc_capacitive(x, dE=dE, Rom=Rom, teps=teps, tau=tau, yeps=yeps)

    capac_fit, capac_cov = curve_fit(
        f=calc_capacitive_part,
        xdata=xvec,
        ydata=yvec,
        p0=p0,
        bounds=capacitive_bounds,
    )

    return capac_fit, capac_cov


def calc_faradaic(t, a, eps, eps2):
    return np.add(np.dot(a, np.power(np.add(t, eps), -0.5)), eps2)


def fit_faradaic_eq(
        xvec,
        yvec,
        initialA=30,
        initialEps=1E-10,
        A_bounds=(-np.inf, np.inf),
        Eps_bounds=(-1, 1)):

    faradaic_bounds = list(zip(A_bounds, Eps_bounds, (np.min(yvec), np.max(yvec))))
    p0 = (initialA, initialEps, np.min(yvec))

    farad_fit, farad_cov = curve_fit(
        f=calc_faradaic,
        xdata=xvec,
        ydata=yvec,
        bounds=faradaic_bounds,
        p0=p0
    )

    return farad_fit, farad_cov
