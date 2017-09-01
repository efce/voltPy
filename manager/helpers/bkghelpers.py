import numpy as np

def calc_abc(xvec, yvec, degree, iterations):
    ybkg = list(yvec)
    for i in range(iterations):
        p = np.polyfit(xvec, ybkg, degree)
        poly_ybkg = np.polyval(p,xvec)
        changed=False
        for i in range(len(ybkg)): # for py,y in zip(poly_ybkg, ybkg): -- zip doesnt work as expected
            if poly_ybkg[i]<ybkg[i]:
                ybkg[i]=poly_ybkg[i]
                changed=True
        if not changed:
            break
    
    yNoBkg = np.subtract(yvec, ybkg)

    return { 
            'yvec': list(yNoBkg), 
            'ybkg': list(ybkg)
        }
