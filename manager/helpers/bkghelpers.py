import numpy as np


def calc_abc(xvec, yvec, degree, iterations):
    ybkg = list(yvec)
    for i in range(iterations):
        p = np.polyfit(xvec, ybkg, degree)
        poly_ybkg = np.polyval(p, xvec)
        changed = False
        for ii, iybkg in enumerate(ybkg):
            if poly_ybkg[ii] < iybkg:
                ybkg[ii] = poly_ybkg[ii]
                changed = True
        if not changed:
            break
    
    yNoBkg = np.subtract(yvec, ybkg)

    return {
        'yvec': list(yNoBkg),
        'ybkg': list(ybkg)
    }
