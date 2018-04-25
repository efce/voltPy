import numpy as np
from matplotlib.mlab import PCA


def osc_pred(xvec, yvec, factors, xpred):
    """
    Orthogonal Signal Correction with Prediction
    Args:
        xvec - 2d matrix: calibration signals (each signal in one row)
        yvec - 2d matrix: concentrations of analytes (each analyte in one row)
        factors - scalar: number of latent variables to use
        xpred - 2d matrxi: signals with unknown concentrations
    """

    xvec = np.array(xvec)
    yvec = np.array(yvec)
    xpred = np.array(xpred)

    n, q = xvec.shape
    nn, q2 = xpred.shape
    assert q == q2

    w = np.zeros([q, 1])
    p = np.zeros([q, 1])

    nnmean = np.mean(xpred, axis=0)
    for i in range(xpred.shape[1]):
        xpred[:, i] = np.subtract(xpred[:, i], nnmean[1, i])

    t = np.zeros([n, factors])
    for i in range(factors):
        i = 1
        weights = PCA(xvec).Wt
        p[:, i] = weights[:q, 1]
        w[:, i] = np.divide(p, np.multiply(p.T, p))
        t[:, i] = np.dot(xvec, w[:, i])
        t[:, i] = t[:, i] - np.dot(
            yvec,
            np.linalg.pinv(np.dot(yvec.T, yvec))
        ).dot(yvec.T).dot(t[:, i])
        p[:, i] = xvec.T.dot(t[:, i]).dot(
            np.linalg.pinv(np.dot(t[:, i], t[:, i].T))
        )
        xvec = np.subtract(xvec, t[:, i].dot(p[:, i].T))
        # t1[:, i] = xpred.dot(w[:, i])
        # xpred = np.subtract(xpred, xpred.dot(w[:, i].dot(np.linalg.pinv(p[:, i].T.dot(w[:, i])).dot(p[:, i].T))))
    for i in range(nn):
        xpred[:, i] = np.add(xpred[:, i], nnmean[1, i])

    return xvec, xpred
