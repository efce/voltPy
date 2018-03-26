import numpy as np

def selfReferencingBackgroundCorrection(yvectors, concs, sens, peak_ranges):

    assert len(yvectors) == len(concs) == len(sens) == len(peak_ranges)

    requested_multiplier = 4.3


    sens_yvec = {}
    sens_conc = {}
    uniq_sens = set(sens)
    for us in uniq_sens:
      selector = (np.array(sens) == us)
      us_conc = np.array(concs)[selector]
      us_yvec = np.array(yvectors)[selector]
      us_uc = set(us_conc)
      for uc in us_uc:
          selector_conc = (np.array(us_conc) == uc)
          mean_vec = np.mean(us_yvec[selector_conc], axis=0)
          ysens = sens_yvec.get(us,[])
          ysens.append([])
          ysens[-1] = mean_vec
          sens_yvec[us] = ysens
          csens = sens_conc.get(us, [])
          csens.append(uc)
          sens_conc[us] = csens

    sig = []
    peak_max = None
    peak_half_width = None
    for sen, yvecs in sens_yvec.items():
        maxconc = np.argmax(sens_conc[sen])
        peak_param = peakParameters(yvecs[maxconc])
        if peak_param is not None:
            peak_max = peak_param['peak_max_index']
            peak_half_width = peak_param['peak_half_width']
            sig = yvecs[maxconc]
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
    dconc = np.zeros(shape=dy.shape, dtype=float)
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
    print('Total operations: {opnum}'.format(opnum=total_calc))
    
    test_iterator = 1
    
    # DA OPERATION:
    width_bkg_ctr = -1
    for width_bkg in width_vector:
        width_bkg_ctr += 1
        procentos = np.floor(width_bkg_ctr/len(width_vector)*100)
        print('{proce}% completed ...'.format(proce=procentos))
        pos_bkg_ctr = -1
        for pos_bkg in span_vector:
            pos_bkg_ctr += 1
            push_bkg_ctr = -1
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

                Xvec = np.hstack([
                    np.arange(fitintervals[0][0],fitintervals[0][1]+1),
                    np.arange(fitintervals[1][0],fitintervals[1][1]+1)
                ])
                """
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
                """

                sens_ctr = -1
                for sen, yvecs in sens_yvec.items():
                    sens_ctr += 1
                    yvec_ctr = -1
                    for yvec, yvec_conc in zip(yvecs, sens_conc[sen]):
                        yvec_ctr += 1
                        xl = np.arange(len(yvec))
                        yvec_range = np.hstack([
                            yvec[int(fitintervals[0][0]):int(fitintervals[0][1])+1],
                            yvec[int(fitintervals[1][0]):int(fitintervals[1][1])+1]
                        ])
                        """
                        poly_coef = np.dot(normalFit, yvec)
                        bkg = poly_coef[3] * xl**3 + poly_coef[2] * xl**2 + poly_coef[1] * xl + poly_coef[0]
                        """
                        p = np.polyfit(Xvec, yvec_range, 3)
                        bkg = np.polyval(p, xl)
                        no_bkg = yvec - bkg
                        peakh = (
                            max(no_bkg[peak_ranges[0][0]:peak_ranges[0][1]])
                            - min(no_bkg[peak_ranges[0][0]:peak_ranges[0][1]]) 
                        )
                        dy[width_bkg_ctr, pos_bkg_ctr, push_bkg_ctr, sens_ctr, yvec_ctr] = peakh
                        dconc[width_bkg_ctr, pos_bkg_ctr, push_bkg_ctr, sens_ctr, yvec_ctr] = yvec_conc
                        """
                        import matplotlib.pyplot as plt
                        plt.plot(Xvec, yvec, '*y')
                        plt.plot(bkg, '--g')
                        plt.plot(s,'b')
                        plt.plot(no_bkg, 'k')
                        plt.show()
                        print(peakh)
                        """
    print('===============\nAnalyzing Data:\n==========')
    (best_result, all_analyzedData) = fullDataAnalysis(dy, dconc)
    return best_result

def peakParameters(curve):
    from manager.helpers.bkghelpers import calc_abc
    import scipy.signal
    peak_is_sure = False
    no_bkg = calc_abc(list(range(len(curve))), curve, 6, 20)['yvec']
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
    peak_max = maxindx# + (half_index_left+half_index_right)/2)/2
    if (abs(peak_max-half_index_left) > abs(peak_max-half_index_right)):
        half_width = (abs(peak_max-half_index_right))
    else:
        half_width = (abs(peak_max-half_index_left))
    return {
        'peak_max_index': int(np.round(peak_max)),
        'peak_half_width': int(half_width),
    }

def fullDataAnalysis(dy, concs):
    import manager.helpers.fithelpers as fithelpers
    results = {}
    best_result = {}
    minstd = float('inf')
    for wi,width in enumerate(dy):
        if width is None:
            continue
        results[wi] = {}
        for spi,span in enumerate(width):
            if span is None:
                continue
            results[wi][spi] = {}
            for ei,ecc in enumerate(span):
                if ecc is None:
                    continue
                results[wi][spi][ei] = {}
                results[wi][spi][ei]['__RES__'] = []
                for sei,sens in enumerate(ecc):
                    if sens is None:
                        continue
                    results[wi][spi][ei][sei] = {}
                    yvconc = concs[wi,spi,ei,sei,:]
                    p = np.polyfit(yvconc, sens, 1)
                    results[wi][spi][ei][sei]['fit'] = {'slope': p[0], 'intercept': p[1]}
                    results[wi][spi][ei][sei]['sx0'] = fithelpers.calc_sx0(p[0], p[1], yvconc, sens)
                    results[wi][spi][ei][sei]['rsq'] = np.corrcoef(yvconc, sens)[0,1] ** 2
                    results[wi][spi][ei]['__RES__'].append( p[1]/p[0])
                    """
                    import matplotlib.pyplot as plt
                    plt.plot(yvconc, sens, '*r')
                    cpoly = np.vectorize(lambda x: p[0]*x+p[1])
                    caly = cpoly(yvconc)
                    plt.plot(yvconc, caly.reshape(5,1), '-b')
                    plt.show()
                    """
                results[wi][spi][ei]['__STD__'] = np.std(results[wi][spi][ei]['__RES__'])
                results[wi][spi][ei]['__AVG__'] = np.average(results[wi][spi][ei]['__RES__'])
                """
                print('std and result:')
                print(results[wi][spi][ei]['__STD__'])
                print(results[wi][spi][ei]['__AVG__'])
                """
                if ( results[wi][spi][ei]['__STD__'] < minstd ):
                    best_result = results[wi][spi][ei]
                    minstd = results[wi][spi][ei]['__STD__']
    return (best_result, results)
