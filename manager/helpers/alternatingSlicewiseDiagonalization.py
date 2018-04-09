import numpy as np
import matplotlib.pyplot as plt


def asd(R, X0, Y0, I, J, K, F, lambdaa, eps, maxiter):
    """
    Implements Alternating Slice-wise Decomposition.
    Implementation based on:

    N. M. Faber, R. Bro, and P. K. Hopke, 
    “Recent developments in CANDECOMP/PARAFAC algorithms:A critical review,”
    Chemom. Intell. Lab. Syst., vol. 65, no. 1, pp. 119–137, 2003.

    R -- 3d matrix to be decomposed
    X0 -- 1d initial guess of 1st dimension
    Y0 -- 1d initial guess of 2nd dimension
    I, J, K -- number of variables in x, y,  order
    F -- scalar: estaminated number of components
    lambdaa -- scalar: penalty weight
    eps -- scalar: threshold for convergens criterion
    maxiter -- scalar: maximal number of iterations of procedure
    """
    R = np.array(R)
    X0 = np.array(X0)
    Y0 = np.array(Y0)

    sumRRt = np.zeros([I, I])
    sumRtR = np.zeros([J, J])
    for k in range(K):
        r = R[:, :, k]
        sumRRt = np.add(r.dot(r.transpose()), sumRRt)
        sumRtR = np.add(r.transpose().dot(r), sumRtR)
    (U, S, V) = np.linalg.svd(sumRRt, 0)
    Ux = U[:, 0:F]
    t, __ = sclmat(X0)
    A = Ux.transpose().dot(t.T)
    G = np.linalg.inv(A.transpose())
    (U, S, V) = np.linalg.svd(sumRtR, 0)
    Uy = U[:, 0:F]
    t, __ = sclmat(Y0)
    B = Uy.transpose().dot(t.T)
    H = np.linalg.inv(B.transpose())
    Rtilde = np.zeros([F, F, K])
    for k in range(K):
        Rtilde[:, :, k] = Ux.transpose().dot(R[:, :, k]).dot(Uy)
    sigmaold = -1
    cnv = eps + 1
    cnt_iter = 0
    while cnv > eps and cnt_iter < maxiter:
        A = np.linalg.inv(G.transpose())
        B = np.linalg.inv(H.transpose())
        Z = np.zeros([K, F])
        for k in range(K):
            Z[k, :] = np.diag(G.transpose().dot(Rtilde[:, :, k]).dot(H)).transpose()
        temp1 = np.zeros([F, F])
        temp2 = temp1
        for k in range(K):
            temp = Rtilde[:, :, k].dot(H)
            temp1 = np.add(temp1, temp.dot(temp.transpose()))
            temp2 = np.add(temp2, temp.dot(np.diag(Z[k, :])))
        temp3 = np.linalg.pinv(
            np.add(
                temp1,
                np.dot(lambdaa, A).dot(A.transpose())
            )
        ).dot(np.add(temp2, (np.dot(lambdaa, A))))
        G, __ = sclmat(temp3)
        temp1 = np.zeros([F, F])
        temp2 = temp1
        for k in range(K):
            temp = Rtilde[:, :, k].transpose().dot(G)
            temp1 = np.add(temp1, temp.dot(temp.transpose()))
            temp2 = np.add(temp2, temp.dot(np.diag(Z[k, :])))
        temp3 = np.linalg.pinv(
            np.add(
                temp1,
                np.dot(lambdaa, B).dot(B.transpose())
            )
        ).dot(np.add(temp2, (np.dot(lambdaa, B))))
        H, __ = sclmat(temp3)
        temp3 = []
        sigma = 0
        for k in range(K):
            s1 = np.power(
                np.linalg.norm(
                    np.subtract(
                        G.transpose().dot(Rtilde[:, :, k]).dot(H),
                        np.diag(Z[k, :])
                    ),
                    'fro'
                ),
                2
            )
            s2 = np.power(
                np.linalg.norm(
                    np.subtract(
                        G.transpose().dot(A),
                        np.eye(F)
                    ),
                    'fro'
                ),
                2
            )
            s3 = np.power(
                np.linalg.norm(
                    np.subtract(
                        B.transpose().dot(H),
                        np.eye(F)
                    ),
                    'fro'
                ),
                2
            )
            sigma += s1 + s2 + s3

        cnv = np.abs((sigma-sigmaold)/sigmaold)
        cnt_iter += 1
        sigmaold = sigma

    errflag = True
    if cnt_iter < maxiter:
        errflag = False
        
    X = Ux.dot(A)
    Y = Uy.dot(B)
    Z = xy2z(R, X, Y, K, F)
    (X, Y, Z) = scale_factors(X, Y, Z)
    (X, Y, Z, order) = sort_factor(X, Y, Z)
    """
    if __debug__:
        plt.subplot(3, 1, 1)
        plt.plot(X)
        plt.subplot(3, 1, 2)
        plt.plot(Y)
        plt.subplot(3, 1, 3)
        plt.plot(Z)
        plt.show()
    """
    return X, Y, Z, errflag, cnt_iter, cnv


def sclmat(A):
    sclA = np.dot(np.sqrt(np.power(A, 2).sum(axis=0)), np.sign(np.sum(A)))
    sclAD = np.diagflat(sclA)
    if sclAD[0, 0] == 1 and sclAD[1, 1] == 1:
        return A, sclAD
    else:
        B = np.dot(A.squeeze(), np.linalg.inv(sclAD))
        return B, sclA


def xy2z(R, X, Y, K, F):
    Z = np.zeros([K, F])
    invXtXYtY = np.linalg.inv(
        np.multiply(
            X.transpose().dot(X),
            Y.transpose().dot(Y)
        )
    )
    for k in range(K):
        Z[k, :] = np.transpose(
            invXtXYtY.dot(np.diag(X.transpose().dot(R[:, :, k]).dot(Y)))
        )
    return Z


def scale_factors(X, Y, Z):
    X, sclX = sclmat(X)
    Y, sclY = sclmat(Y)
    Z = Z.dot(np.diag(sclX)).dot(np.diag(sclY))
    return X, Y, Z


def sort_factor(X, Y, Z):
    order = np.argsort(
        np.dot(np.diag(Z.transpose().dot(Z)), -1)
    )
    X = X[:, order]
    Y = Y[:, order]
    Z = Z[:, order]
    return X, Y, Z, order
