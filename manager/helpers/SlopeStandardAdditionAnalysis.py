import numpy as np
from scipy.signal import savgol_filter
from scipy.stats import t
from normalEquationFit import normalEquationFit

def SlopeStandardAdditionAnalysis(DATACELL, peakLocation, options):
    """
%
% SlopeStandardAdditionAnalysis(DATACELL, peakLocation, options) is a function which tries
% to perform standard addition analysis using peak slope at the inflection points
% without any background correction.
%
%
% DATACELL has four cell arrays (can be generated via prepareStructFromRawData):
%    Y: MATRIX with registered signals in each column
%    X: VECTOR with values to plot Y(:,i) against (the same number of rows as Y, and one
%    column) -- used only for plots.
%    CONC: VECTOR with values of concentration for each column of Y (so the same
%    number of columns and one row)
%    SENS: VECTOR with the INDEX (so 1:nrOfSens values) of sensitivity of each Y column (so the same
%    number of columns as Y and one row). There has to be minimum two
%    different sensitivities for each concentration.
%
% peakLocation is a scalar with rough estimate of the signal of interest
%    maximum. It is expressed as a field number i.e. of single curve cosists
%    of 100 data points peakLocation can be a number between 1 and 100.
%
% options is a structure, which may contain fields:
%      .average - boolean, true means that columns with the same concentration
%                and sensitivity should be everaged
%      .smooth - boolean, true means that data should be smoothed before further
%                processing
%      .forceSamePoints - boolean, true means that inflection points should only
%                be calculated for the curve with highest concentration
%                and used for all (as opposed to calculating the
%                inflection point for all curves independiently.
    """

# Check input and set some default values (this may be tweaked)
#==============================================================
    assert( len(DATACELL.SENS) == len(DATACELL.Y) \
        and len(DATACELL.CONC) == len(DATACELL.Y) )
    correlationTreshhold = 0.8
    rowRemoveTresholdPercent = 0.3
    slopeDiffRequired = 0.05
    options['average'] = options.get('average', False)
    options['smooth'] = options.get('smooth', False)
    options['forceSamePoints'] = options.get('forceSamePoints', False)

    dataY = DATACELL.Y
    conc = DATACELL.CONC
    sens = DATACELL.SENS

    if ( options['average'] == True ):
        # try to perform data averaging by sensitivity && concentration
        #==============================================================
        if ( __debug__ ):
            print('Averaging curves with the same concentration and sensitivity');
        newDataY = []
        newConc = []
        newSens = []
        for s in set(sens): #unique values
            for c in set(conc): #unique values
                sum = [0] * len(dataY[-1])
                num = 0
                for i,cc in enumerate(conc):
                    if s == sens[i]:
                        if c == conc[i]:
                            sum = np.sum([ sum, dataY[i] ])
                            num = num+1
                newDataY.append([])
                newDataY[-1] = [ x/num for x in sum ]
                newConc.append(c);
                newSens.append(s);
        dataY = newDataY
        conc = newConc
        sens = newSens

    # sort data by conc, so it is easier to follow the work flow
    #===========================================================

    sortIndexes = [ i[0] for i in sorted(enumerate(conc), reverse=True, key=lambda x:x[1]) ]
    datas = {}
    for s in set(sens):
        datas[s] = {
                    'CONC': [],
                    'Y': []
                }

    for i in sortIndexes:
        datas[sens[i]]['CONC'].append(conc[i])
        datas[sens[i]]['Y'].append( [0] )
        datas[sens[i]]['Y'][-1] = dataY[i]
    # datas contains all data divided by SENS 
    # in order from highest to lowest CONC

    if ( options['smooth'] == True ):
        # smooth is required
        #===================
        for key,sData in datas.items():
            for sig in sData['Y']:
                sig = savgol_filter(sig, 13, 3)

    # Very important step -- find the slope of each peak in inflection point.
    # By default it reuses the point where the slope was taken from the peak
    # with the highest concentration -- if the location of the peak
    # changes in subsequent data please use:
    # options.forceSamePoints = false;
    # Variables may end with R, L or AVG, which means they deal with
    # rigth, left or average slope in inflection point respectivly.
    # getSlopeInInflection is included in this file.
    #================================================================
    
    result = {}
    for o in ['L', 'R', 'AVG']:
        result[o] = dict() 

    for r_l_avg,r in result.items():
        r['Fit'] = {}
        r['R'] = {}
        r['Slopes'] = {}
        r['OK'] = True
        r['Intersections'] = []
        r['Results'] = []
        r['Mean'] = None
        r['Median'] = None
        r['STD'] = None #Standard Dev
        r['CI'] = None #Confidence Interval

    fitRanges = {}
    for s,sData in datas.items():
        fitRanges[s] = {}
        for k,r in result.items():
            r['Fit'][s] = []
            r['R'][s] = []
            r['Slopes'][s] = []
        for i,yvector in enumerate(sData['Y']):
            slopeL, slopeR, slopeAVG, fr =  getSlopeInInflection(
                            yvector, 
                            peakLocation,
                            options['forceSamePoints'], 
                            fitRanges[s].get(i-1,(None, None))
                        )
            result['L']['Slopes'][s].append(slopeL)
            result['R']['Slopes'][s].append(slopeR)
            result['AVG']['Slopes'][s].append(slopeAVG)
            fitRanges[s][i] = fr

    # It uses Normal Equation to find the optimal fit of calibration plot.
    #=====================================================================
    for r_l_avg, r in result.items():
        for s,d in r['Slopes'].items():
            r['Fit'][s] = normalEquationFit(datas[s]['CONC'], r['Slopes'][s])
            tmp = np.corrcoef(
                    [ r['Fit'][s]['slope']*x+r['Fit'][s]['intercept'] for x in datas[s]['CONC'] ],
                    r['Slopes'][s] 
                )
            r['R'][s] = tmp[0,1]


    # Generate initial matrix of intercepts
    #======================================
    for r_l_avg, r in result.items():
        r['Intersections'] = np.array([ [None]*len(r['Fit']) ]*len(r['Fit']))

    # We need to verify if slopes for each peak are found
    #====================================================
    for r_l_avg,r in result.items():
        if None in r['Slopes']:
            r['OK'] = False

    for r_l_avg,r in result.items():
        if not r['OK']:
            continue
        for s,d in r['Slopes'].items():
            for ss,dd in r['Slopes'].items():
                # Note that it finds the intersect point for two lines at the
                # time, filling upper triangle of the matrix
                #============================================================
                if (s >= ss ):
                    continue

                slopeProportion = r['Fit'][s]['slope'] / r['Fit'][ss]['slope']
                # Check if sensitivities are different enough, to small
                # difference will result in serious problem with precission
                # (and possible accuracy) of the result
                #==========================================================
                if True or ( slopeProportion > (1+slopeDiffRequired) \
                or slopeProportion < (1-slopeDiffRequired) ):
                    # Matrix solution (not used for performance):
                    #toInv = np.array([ 
                    #                    [r['Fit'][s]['slope'],-1],
                    #                    [r['Fit'][ss]['slope'],-1] 
                    #                ])
                    #afterInv = np.linalg.pinv(toInv)
                    #otherArr = np.matrix([ 
                    #                        [-r['Fit'][s]['intercept']],
                    #                        [-r['Fit'][ss]['intercept']]
                    #                    ])
                    x = ( (r['Fit'][s]['intercept']-r['Fit'][ss]['intercept'])\
                          / (r['Fit'][ss]['slope']-r['Fit'][s]['slope']) )
                    y = r['Fit'][s]['slope'] * x + r['Fit'][s]['intercept']
                    r['Intersections'][s,ss] = (x,y)
                else:
                    r['OK'] = False
                    print('Slopes for two sensitivities are too similar for %s' % r_l_avg )

    # Here, is a little trick, to remove the intersection points
    # which are too far from average. It is done by the means of
    # Coefficient of Variance value, and can be tweaked in the setting at
    # the beggining of the file.
    # minimizeCV is included in this file.
    #====================================================================
    #TODO:FIXME: Na razie to pomijam:
    #crossAVG, removedORDER = minimizeCV(np.squeeze(crossAVG[:,:,1]), 3, rowRemoveTresholdPercent);
    #for rm in removedORDER:
    #    corrArr['AVG'][rm] = None;
    #fresAVG = -crossAVG(logical(triu(ones(size(crossAVG)),1)));
    #stdAVG = std(fresAVG);

    #crossR, removedORDER = minimizeCV(np.squeeze(crossR[:,:,1]), 3, rowRemoveTresholdPercent);
    #for rm in removedORDER:
    #    corrArr['R'][rm] = None;
    #fresR = -crossR(logical(triu(ones(size(crossR)),1)));
    #stdR = std(fresR);

    #crossL, removedORDER = minimizeCV(np.squeeze(crossL[:,:,1]), 3, rowRemoveTresholdPercent);
    #for rm in removedORDER:
    #    corrArr['L'][rm] = None;
    #fresL = -crossL(logical(triu(ones(size(crossL)),1)));
    #stdL = std(fresL);
    for r_l_avg, r in result.items():
        s = 0
        for s in r['Intersections']:
            for ss in s:
                if not ss == None:
                    r['Results'].append(ss[0])
        r['STD'] = np.std(r['Results'])
        r['Median'] = np.median(r['Results'])
        r['Mean'] = np.average(r['Results'])
        r['CI'] = t.isf(0.05, len(r['Results'])) * r['STD'] / len(r['Results'])

    print(result)

    #TODO:FIXME: Na razie nie robie:
    # Here it selects, if it is possible to offer the final result, for which
    # set of data, the result is the best (left, right or average)
    #=====================================================================
    #if ( lOK and min(corrArr['L']) > correlationTreshhold \
    #and ( None in stdAVG or stdL <= stdAVG or min(corrArr['AVG']) <= correlationTreshhold ) \
    #and ( None in stdR or stdL <= stdR or min(corrArr['R']) <= correlationTreshhold ) ):
    #    print('Selecting left slope');
    #    fres = fresL;
    #elif ( rOK and min(corrArr['R']) > correlationTreshhold \
    #and ( None in stdAVG or stdR <= stdAVG or min(corrArr['AVG']) <= correlationTreshhold ) \
    #and ( None in stdL or stdR <= stdL or min(corrArr['L']) <= correlationTreshhold ) ):
    #    print('Selecting right slope');
    #    fres = fresR;
    #elif ( avOK or min(corrArr['AVG']) > correlationTreshhold ):
    #    print('Selecting average slope');
    #    fres = fresAVG;
    #else:
    #    raise ValueError('Could not select slope for calibration, please verify the data');

    ##disp(sprintf('Partial results median: %0.6e ',median(fres)));
    #print('The final result of standard addition: %d ± %d' % (mean(fres), (std(fres)/sqrt(numel(fres))*tinv(1-(.05/2),length(fres)-1))));


# returns: [slopeL, slopeR, slopeAVGfitRange, fitRange] 
def getSlopeInInflection(signal, peak, forceFitRange, fitRange):

# I find this as one of the most important steps, I has gone trou many
# iterations, so the code is a bit of mixture of different ideas.
# Some tweakalbe setting:
#======================================================================
    fitSize = 5 #How many points should be fitted to get slope%
    fitX = np.arange(0,fitSize)
    maxHit = 4  #How many times the slope has to change to call it inflection point%

    # Prepare data structures:
    #=========================
    hitCnt = 0;
    sigLen = len(signal);
    prevNormalFit = {'slope': None, 'intercept': None };
    finalNormalFit = {'slope':  None, 'intercept': None };
    #signal = smooth(signal,13,'sgolay',3);
    #signal = savgol_filter(signal, 17, 3);

    if (not None in fitRange) and forceFitRange:
        # If we have already the point range in which the slope has to be
        # found (i.e. this is not the plot with the highest concentration)
        #=================================================================
        fitrangeL = fitRange[0]
        fitrangeR = fitRange[1]

        # Get linear fit on the left side
        #===========================
        fitL=normalEquationFit(fitX, signal[fitrangeL[0]:fitrangeL[1]])
        # Get linear fit on the rigth side
        #===========================
        fitL=normalEquationFit(fitX, signal[fitrangeR[0]:fitrangeR[1]])

        # Get slopes:
        #======================
        slopeL = fitL['slope'];
        slopeR = fitR['slope'];

    else:
        # This is either the plot with the highest concentration or
        # option.forceSamePoints == false
        # So first, we need to find the inflection point, and then
        # compute its slope.
        #==========================================================
        for fitPos in np.arange(peak, fitSize, -1):
            # We start from the left side of the peak:
            #=========================================
            if ( peak < fitPos-fitSize ):
                raise ValueError('Signal too small to fit data');
            fitrange =  ( fitPos-fitSize, fitPos );
            y = signal[fitrange[0]:fitrange[1]]
            nfit = normalEquationFit(fitX, y)

            if None == prevNormalFit.get('slope', None):
                prevNormalFit = nfit;
            elif ( nfit['slope'] < prevNormalFit['slope'] ):
                if ( hitCnt == 0 ):
                    finalFitrange = fitrange;
                    finalNormalFit = nfit;
                hitCnt += 1;
                if ( hitCnt == maxHit ):
                    break;
            elif ( nfit['slope'] >= prevNormalFit['slope'] ):
                finalNormalFit = {'slope': None, 'intercept': None }
                hitCnt = 0;
            prevNormalFit = nfit

        if None == finalNormalFit.get('slope', None): 
            print('Fit failed')
        else:
            slopeL = finalNormalFit['slope'];
            fitrangeL = finalFitrange;

        fitrange = (None, None)
        prevNormalFit = { 'slope': None, 'intercept': None }

        for fitPos in np.arange(peak, (sigLen-fitSize)):
            # And now rigth side:
            #====================
            fitrange= (fitPos, (fitPos+fitSize) )
            y = signal[fitrange[0]:fitrange[1]]
            nfit = normalEquationFit(fitX, y)

            if None == prevNormalFit.get('slope', None):
                prevNormalFit = nfit;
            elif ( nfit['slope']  > prevNormalFit['slope'] ):
                if ( hitCnt == 0 ):
                    finalFitrange = fitrange
                    finalNormalFit = nfit
                hitCnt += 1;
                if ( hitCnt == maxHit ):
                    break;
            elif ( nfit['slope'] <= prevNormalFit['slope'] ):
                finalNormalFit = {'slope': None, 'intercept': None };
                hitCnt = 0;
            prevNormalFit = nfit

        if None == finalNormalFit.get('slope', None):
            print('Fit failed')
        else:
            slopeR = finalNormalFit['slope'];
            fitrangeR = finalFitrange;

        fitRange = [ fitrangeL, fitrangeR ]

    # This part provide alternative method of getting the slope in the
    # infleciton, as any noise will make it much more difficult, here are
    # tested approaches. This overrites previous method, as is more
    # difficult to follow.
    #=====================================================================
    '''
    experimental = 1;

    if ( experimental == 1 )
        a=( signal(fitrangeR(end))-signal(fitrangeL(1)) )/( fitrangeR(end)-fitrangeL(1));
        b=signal(fitrangeL(1)) - a*fitrangeL(1);
        p = [ a b ];
        %p = polyfit( [ fitrangeL(1) fitrangeR(end) ]', signal([ fitrangeL(1) fitrangeR(end) ]),1), pause
        levelPeak = signal - polyval(p,[ 1 : numel(signal) ])';
        range2 = [ floor((fitrangeR(end)+fitrangeL(1))/2)-ceil(1.2*(fitrangeR(end)-fitrangeL(1))) ceil((fitrangeR(end)+fitrangeL(1))/2)+ceil(1.2*(fitrangeR(end)-fitrangeL(1))) ];
        %levelPeak = levelPeak - min(levelPeak(range2(1):range2(end)));
        f = fit( [range2(1):range2(end)]', levelPeak([range2(1):range2(end)]), 'smoothingspline' );
        %figure(99);plot(f,[1:numel(signal)], levelPeak);hold on; pause
        slopeL = f(fitrangeL(2)) - f(fitrangeL(1));
        slopeR = f(fitrangeR(end)) - f(fitrangeR(end-1));
    elseif ( experimental == 2 )
        d1 = sgsdf(signal,2,1,0,0);
        d2 = sgsdf(d1,2,1,0,0);
        plot(signal,'k');hold on;plot(d1,'b'); hold on; plot(d2,'r')
        vl=abs(d2(1));
        pl=0;
        vr=abs(d2(end));
        pr=0;
        fr = [ fitrangeL(1)-20 : fitrangeR(end)+20 ];
        for i= fr;
            if ( abs(d2(i)) < vl && d2(i)>d2(i-1) ) %signal is increasing
                vl=abs(d2(i));
                pl=i;
            elseif ( abs(d2(i)) < vr && d2(i)<d2(i-1) ) %signal is decreasing
                vr = abs(d2(i));
                pr = i;
            end
        end

        %Set final values:
        %=================
        if ( pl ~= 0 )
            slopeL = d1(pl);
        else
            slopeL = NaN;
        end
        if ( pr ~= 0 )
            slopeR = d1(pr);
        else
            slopeR = NaN;
        end

    end
    '''

    # Get average slope (rigth slope has negative slope (or should have):
    #==================================================================
    slopeAVGfitRange = (slopeL - slopeR)/2;
    return slopeL, slopeR, slopeAVGfitRange, fitRange 

if ( __name__ == '__main__' ):
    import prepareStructForSSAA as ps
    import pandas as pd
    data = pd.read_csv('Tl_120s_RAW.csv', header=None)
    datal = [ data[x].tolist() for x in range(0,len(data.columns))]
    stru = ps.prepareStructForSSAA(datal, [0,1,2,3,4,5,6,7], 40, 4, [5, 10, 15], 'dp')
    SlopeStandardAdditionAnalysis(stru, 105, {})
