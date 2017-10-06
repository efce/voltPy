import numpy as np

def selfReferencingBackgroundCorrection(yvectors, concs, sens, peak_ranges):

    assert len(yvectors) == len(concs) == len(sens) == len(peak_ranges)

    requested_multiplier = 4.3

    # Complicated way of averaging of curves with the same sens and conc
    signals = {}
    rep = {}
    for i,sen in enumerate(sens):
        onesens = signals.get(sen, {})
        concsens = onesens.get(concs[i], np.array([0.0]))
        concsens = concsens + np.array(yvectors[i])
        onesens[concs[i]] = concsens
        signals[sen] = onesens
        rs = rep.get(sen,{})
        rc = rs.get(concs[i],0)
        rc += 1
        rs[concs[i]] = rc
        rep[sen] = rs

    for ks, vs in signals.items():
        for kc, vc in vs.items():
            vc = vc / rep[ks][kc]
    # done -- averaged 
    sig = []
    peak_max = None
    peak_half_width = None
    for ks, vs in signals.items():
        for kc, vc in vs.items():
            peak_param = peakParameters(vc)
            if peak_param is not None:
                peak_max = peak_param['peak_max_index']
                peak_half_width = peak_param['peak_half_width']
                sig = vc
                break
        else:
            continue
        break
    else:
        raise ValueError('Could not obtain result')

    if ( peak_max > len(sig)/2 ):
        #peak is in the right part
        width_multiply = (len(sig)-peak_max)/peak_half_width
        if width_multiply < requested_multiplier:
            peak_half_width = np.floor((len(sig)-peak_max)/4.3)-1
    else:
        #peak is in the left part
        width_multiply = peak_max/peak_half_width
        if width_multiply < requested_multiplier:
            peak_half_width = np.floor(peak_max/4.3)-1

    width_bkg_ctr = 0
    if ( peak_half_width/3 > 3 ):
        start_width = np.ceil(peak_half_width/3)
    else:
        start_width = 3

    move_factor = 0.3
    width_vector = np.arange(peak_half_width, start_width, -1)
    span_vector = np.arange(
        np.floor(3*peak_half_width), 
        np.floor(peak_half_width*1.5), 
        -1
    )
    ecc_vector = list(np.arange(0, np.floor(-move_factor*peak_half_width), -1))
    ecc_vector.extend(list(np.arange(1, np.ceil(move_factor*peak_half_width), 1)))

    dy = np.empty(
        shape=(
            len(width_vector),
            len(span_vector), 
            len(ecc_vector),
            len(set(sens)), 
            len(set(concs))
        ), 
        dtype=float
    )
    dy.fill(np.NAN)
    param = np.zeros(
        shape=(
            dy.shape[0], 
            dy.shape[1], 
            dy.shape[2], 
            3
        )
    )
    total_calc = (
        dy.shape[0] * dy.shape[1] * dy.shape[2] * dy.shape[3] * dy.shape[4]
    )
    total_ex = [ [True]*total_calc ] * len(concs)
    
    test_iterator = 1
    
    # DA OPERATION:
    for width_bkg in width_vector:
        procentos = np.floor(width_bkg_ctr/len(width_vector))*100
        print('{proce}% completed ...'.format(proce=procentos))
        width_bkg_ctr += 1
        pos_bkg_ctr = 0
        for pos_bkg in span_vector:
            pos_bkg_ctr += 1
            push_bkg_ctr = 0
            for push_bkg in ecc_vector:
                if ( (peak_max - push_bkg - pos_bkg - width_bkg) < 1
                or (peak_max + push_bkg + pos_bkg + width_bkg) > len(sig)):
                    #OUT OF BOUNDS
                    continue
                push_bkg_ctr += 1
                new_fit = True
                fitintervals = (
                    (
                        (peak_max - pos_bkg + push_bkg - width_bkg), 
                        (peak_max - pos_bkg + push_bkg)
                    ),
                    (
                        (peak_max + pos_bkg + push_bkg),
                        (peak_max + pos_bkg + push_bkg + width_bkg)
                    )
                )
                #prepare for normal cubic fit
                Xvec = np.hstack([
                    np.arange(fitintervals[0][0],fitintervals[0][1]+1),
                    np.arange(fitintervals[1][0],fitintervals[1][1]+1)
                ])
                Xmat1 = np.array(Xvec)
                Xmat0 = Xmat1 ** 0
                Xmat2 = Xmat1 ** 2
                Xmat3 = Xmat1 ** 3
                Xmat = np.vstack([Xmat0, Xmat1, Xmat2, Xmat3])
                Xmat = Xmat.transpose()
                XX = np.dot(Xmat, Xmat.transpose())
                normalFit = np.linalg.pinv(XX)
                normalFit = np.dot(normalFit, Xmat);
                normalFit = np.transpose(normalFit)
                import pdb; pdb.set_trace()

                for ks, vs in signals.items():
                    concs = list(vs)
                    for conc in sorted(concs,reverse=True):
                        s = vs[conc]
                        yvec = np.hstack([
                            s[int(fitintervals[0][0]):int(fitintervals[0][1])+1],
                            s[int(fitintervals[1][0]):int(fitintervals[1][1])+1]
                        ])
                        poly_coef = np.dot(normalFit, yvec)
                        xl = np.arange(len(s))
                        bkg = poly_coef[3] * xl**3 + poly_coef[2] * xl**2 + poly_coef[1] * xl + poly_coef[0]
                        import matplotlib.pyplot as plt
                        plt.plot(s,'b')
                        plt.plot(bkg,'--r')
                        plt.show()
                        << #TODO: POROWNAC Z POLYFITEM !!! >>


def peakParameters(curve):
    from manager.helpers.bkghelpers import calc_abc
    import scipy.signal
    peak_is_sure = False
    no_bkg = calc_abc(list(range(len(curve))), curve, 5, 30)['yvec']
    no_bkg = scipy.signal.savgol_filter(np.array(no_bkg),11, 3)
    maxindx = no_bkg.argmax()
    to_left = maxindx - 1
    to_right = len(curve) - maxindx
    left_size = 0
    for i in range(to_left):
        if no_bkg[maxindx-i-1] < no_bkg[maxindx-i]:
            left_size += 1
            continue
        else:
            break
    right_size = 0
    for i in range(to_right):
        if no_bkg[maxindx+i+1] < no_bkg[maxindx+i]:
            right_size += 1
            continue
        else:
            break
    std = np.std([right_size, left_size])
    if (std/np.mean([right_size, left_size]) > 0.2):
        if ( __debug__ ):
            import matplotlib.pyplot as plt
            plt.plot(no_bkg,'b')
            plt.plot(maxindx, no_bkg[maxindx],'*r')
            plt.show()
            print('Peak is not symmetric, returning None.')
        return None
    half_height = no_bkg[maxindx]/2
    half_index_left = None
    diff = float("inf")
    for i,val in enumerate(no_bkg[maxindx-left_size:maxindx]):
        new_diff = abs(val-half_height)
        if (new_diff < diff):
            diff = new_diff
            half_index_left = i+(maxindx-left_size)
    diff = float("inf")
    half_index_right = None
    for i,val in enumerate(no_bkg[maxindx:maxindx+right_size]):
        new_diff = abs(val-half_height)
        if (new_diff < diff):
            diff = new_diff
            half_index_right = i+maxindx
    peak_max = (maxindx + (half_index_left+half_index_right)/2)/2
    half_width = 2*(abs(peak_max-half_index_left))
    return {
        'peak_max_index': int(np.round(peak_max)),
        'peak_half_width': int(half_width),
    }

