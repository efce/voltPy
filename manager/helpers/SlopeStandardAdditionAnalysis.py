import numpy as np
import scipy

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
    sortIndexes = [ i[0] for i in sorted(enumerate(conc), key=lambda x:x[1]) ]
    concSort = []
    sensSort = []
    dataYSort = []
    for i in sortIndexes:
        concSort.append(conc[i])
        sensSort.append(sens[i])
        dataYSort.append([ 0 ])
        dataYSort[-1] = dataY[i]

    if ( options['smooth'] == True ):
        # smooth is required
        #===================
        for sig in dataYSort:
            sig = scipy.signal.savgol_filter(sig, 13, 3)

    # Very important step -- find the slope of each peak in inflection point. 
    # By default it reuses the point where the slope was taken from the peak
    # with the highest concentration -- if the location of the peak 
    # changes in subsequent data please use:
    # options.forceSamePoints = false;
    # Variables may end with R, L or AVG, which means they deal with
    # rigth, left or average slope in inflection point respectivly.
    # getSlopeInInflection is included in this file.
    #================================================================
    slopeL = np.matrix([[None]]*len(conc))
    slopeR = np.matrix([[None]]*len(conc))
    slopeAVG = np.matrix([[None]]*len(conc))
    fitRange = [None]*len(conc)
    last = len(conc) - 1
    peakLocation = None
    i=0
    slopeL[last], slopeR[last], slopeAVG[last], fitRange[last] = \
            getSlopeInInflection(dataYSort[last], peakLocation, False, 0)
    for i in np.arange(last-1, -1, -1):
        slopeL[i], slopeR[i], slopeAVG[i], fitRange[i] = \
                getSlopeInInflection(dataYSort[i], peakLocation, options['forceSamePoints'], fitRange[i+1])

    
    # It uses Normal Equation to find the optimal fit of calibration plot.
    #=====================================================================
    sensUnique = set(sensSort)
    sensUniqueLen = len(sensUnique)
    normalFitL = np.matrix([ [0,0] ] *sensUniqueLen, dtype='float')
    normalFitR = np.matrix([ [0,0] ] *sensUniqueLen, dtype='float')
    normalFitAVG = np.matrix([ [0,0] ] *sensUniqueLen, dtype='float')
    corrAr = {}
    corrAr['L'] = np.matrix([ 0 ] * sensUniqueLen, dtype='float')
    corrAr['R'] =np.matrix([ 0 ] * sensUniqueLen, dtype='float')
    corrAr['AVG'] =np.matrix([ 0 ] * sensUniqueLen, dtype='float')
    for s in sensUnique:
        list = [ x==s for x in sensSort ]
        msize = np.sum(list)
        conc_sens = np.array([[None]]*msize, dtype='float')
        slopeL_sens = np.array([[None]]*msize, dtype='float')
        slopeR_sens = np.array([[None]]*msize, dtype='float')
        slopeAVG_sens = np.array([[None]]*msize, dtype='float')
        cnt = 0
        for i,istrue in enumerate(list):
            if istrue:
                print(cnt)
                conc_sens[cnt]=concSort[i]
                slopeL_sens[cnt]=slopeL[i]
                slopeR_sens[cnt]=slopeR[i]
                slopeAVG_sens[cnt]=slopeAVG[i]
                cnt+=1
        unitVec = np.matrix([[1.0]]*len(conc_sens), dtype='float')

        # FIT using normal equation:
        X = np.concatenate((unitVec, conc_sens), axis=1)
        XX = X* np.transpose(X)
        normalFitX = np.linalg.pinv(XX)
        normalFitX = normalFitX * X;
        normalFitX = np.transpose(normalFitX)
        normalFitL[s] = np.transpose(normalFitX * slopeL_sens)
        normalFitR[s] = np.transpose(normalFitX * slopeR_sens)
        normalFitAVG[s] = np.transpose(normalFitX * slopeAVG_sens)

        v = [ normalFitL.item(s,0)*x[0]+normalFitL.item(s,1) for x in conc_sens.tolist() ]
        print(v)
        slopeL_sens = np.ravel(slopeL_sens)
        print(slopeL_sens);
        tmp = np.corrcoef( 
            v, 
            slopeL_sens );
        print(tmp);
        tmp = np.corrcoef( 
            [ normalFitR.item(s,0)*x[0]+normalFitR.item(s,1) for x in conc_sens.tolist() ], 
            slopeR_sens.squeeze() );
        corrAr['R'][s] = tmp.item((0,1));
        tmp = np.corrcoef( 
            [ normalFitAVG.item(s,0)*x[0]+normalFitAVG.item(s,1) for x in conc_sens.tolist() ], 
            slopeAVG_sens.squeeze() );
        corrAr['AVG'][s] = tmp.item((0,1));

    return
"""
    
    calibration.L = slopeL(1,:);
    calibration.R = slopeR(1,:);
    calibration.AVG = slopeAVG(1,:);
    
    % Generate initial matrix of intercepts
    %======================================
    crossL = zeros(size(normalFitL,2),size(normalFitL,2),2);
    crossR = zeros(size(normalFitR,2),size(normalFitR,2),2);
    crossAVG = zeros(size(normalFitAVG,2),size(normalFitAVG,2),2);
    
    rpos = 1;
    fres = [];
    
    % We need to verify if slopes for each peak are found
    %====================================================
    avOK = true;
    rOK = true;
    lOK = true;
    if ( any(isnan(slopeR)))
        rOK=false;
        avOK=false;
    end
    if ( any(isnan(slopeL)))
        lOK=false;
        avOK=false;
    end
    
    for i=1:size(normalFitAVG,2)
        for ii=1:size(normalFitAVG,2)
            if ( i >= ii )
                crossAVG(i,ii,1) = NaN;
                crossR(i,ii,1) = NaN;
                crossL(i,ii,1) = NaN;
                continue;
            end
            % Note that it finds the intersect point for two lines at the
            % time, filling upper triangle of the matrix
            %============================================================
            if ( avOK )
                prop = normalFitAVG(2,i) / normalFitAVG(2,ii);
                if ( prop > (1+slopeDiffRequired) || prop < (1-slopeDiffRequired) )
                    % Check if sensitivities are different enough, to small
                    % difference will result in serious problem with precission
                    % (and possible accuracy) of the result
                    %==========================================================
                    crossAVG(i,ii,:) = pinv([normalFitAVG(2,i) -1; normalFitAVG(2,ii) -1]) * [-normalFitAVG(1,i);-normalFitAVG(1,ii)];
                    plot([ crossAVG(i,ii,1) concSort(end) ], [ crossAVG(i,ii,1) concSort(end) ].*normalFitAVG(2,i) + normalFitAVG(1,i), 'g-');
                    plot([ crossAVG(i,ii,1) concSort(end) ], [ crossAVG(i,ii,1) concSort(end) ].*normalFitAVG(2,ii) + normalFitAVG(1,ii), 'g-');
                    fresAVG(rpos) = -crossAVG(i,ii,1);
                    plot(crossAVG(i,ii,1),crossAVG(i,ii,2),'gx','MarkerSize',20);
                else
                    disp (['Sens1: ' num2str(normalFitAVG(2,i)) '; Sens2: ' num2str(normalFitAVG(2,ii)) '; Sens1/Sens2:' num2str(normalFitAVG(2,i)/normalFitAVG(2,ii)) ]);
                    disp('Sensitivities are too similar for AVERAGE');
                    avOK = false;
                end
                
            end

            
            % The same as above, but for L
            %=============================
            if ( lOK )
                prop = normalFitL(2,i) / normalFitL(2,ii);
                if ( prop > (1+slopeDiffRequired) || prop < (1-slopeDiffRequired) )
                    crossL(i,ii,:) = pinv([normalFitL(2,i) -1; normalFitL(2,ii) -1]) * [-normalFitL(1,i);-normalFitL(1,ii)];
                    plot([ crossL(i,ii,1) concSort(end) ], [ crossL(i,ii,1) concSort(end) ].*normalFitL(2,i) + normalFitL(1,i), 'b-');
                    plot([ crossL(i,ii,1) concSort(end) ], [ crossL(i,ii,1) concSort(end) ].*normalFitL(2,ii) + normalFitL(1,ii), 'b-');
                    fresL(rpos) = -crossL(i,ii,1);
                    plot(crossL(i,ii,1),crossL(i,ii,2),'bx','MarkerSize',20);
                else
                    disp (['Sens1: ' num2str(normalFitL(2,i)) '; Sens2: ' num2str(normalFitL(2,ii)) '; Sens1/Sens2:' num2str(normalFitL(2,i)/normalFitL(2,ii)) ]);
                    disp('Sensitivities are too similar for LEFT');
                    lOK = false;
                end
            end
            
            % The same as above but for R
            %============================
            if ( rOK )
                prop = normalFitR(2,i) / normalFitR(2,ii);
                if ( prop > (1+slopeDiffRequired) || prop < (1-slopeDiffRequired) )
                    crossR(i,ii,:) = pinv([normalFitR(2,i) -1; normalFitR(2,ii) -1]) * [-normalFitR(1,i);-normalFitR(1,ii)];
                    plot([ crossR(i,ii,1) concSort(end) ], [ crossR(i,ii,1) concSort(end) ].*normalFitR(2,i) + normalFitR(1,i), 'r-');
                    plot([ crossR(i,ii,1) concSort(end) ], [ crossR(i,ii,1) concSort(end) ].*normalFitR(2,ii) + normalFitR(1,ii), 'r-');
                    fresR(rpos) = -crossR(i,ii,1);
                    plot(crossR(i,ii,1),crossR(i,ii,2),'rx','MarkerSize',20);
                else
                    disp (['Sens1: ' num2str(normalFitR(2,i)) '; Sens2: ' num2str(normalFitR(2,ii)) '; Sens1/Sens2:' num2str(normalFitR(2,i)/normalFitR(2,ii)) ]);
                    disp('Sensitivities are too similar for RIGHT');
                    rOK = false;
                end
            end
            rpos = rpos+1;
        end
    end
    
    regressionEquations.AVG = normalFitAVG;
    regressionEquations.L = normalFitL;
    regressionEquations.R = normalFitR;
    
    % Here, is a little trick, to remove the intersection points
    % which are too far from average. It is done by the means of
    % Coefficient of Variance value, and can be tweaked in the setting at
    % the beggining of the file.
    % minimizeCV is included in this file.
    %====================================================================
    [ crossAVG, removedORDER ] = minimizeCV(squeeze(crossAVG(:,:,1)), 3, rowRemoveTresholdPercent);
    for i=1:length(removedORDER)
        correlation.AVG(removedORDER(i)) = [];
    end
    fresAVG = -crossAVG(logical(triu(ones(size(crossAVG)),1)));
    stdAVG = std(fresAVG);
    
    [ crossR, removedORDER ] = minimizeCV(squeeze(crossR(:,:,1)), 3, rowRemoveTresholdPercent);
    for i=1:length(removedORDER)
        correlation.R(removedORDER(i)) = [];
    end
    fresR = -crossR(logical(triu(ones(size(crossR)),1)));
    stdR = std(fresR);
    
     [ crossL, removedORDER ] = minimizeCV(squeeze(crossL(:,:,1)), 3, rowRemoveTresholdPercent);
    for i=1:length(removedORDER)
        correlation.L(removedORDER(i)) = [];
    end
    fresL = -crossL(logical(triu(ones(size(crossL)),1)));
    stdL = std(fresL);
    
    disp('Corelations Left:')
    for i=1:size(correlation.L,2)
        disp(correlation.L(i));
    end
    disp('===============')
    disp('Corelations Right:')
    for i=1:size(correlation.R,2)
        disp(correlation.R(i));
    end
    disp('===============')
    disp('Corelations AVG:')
    for i=1:size(correlation.AVG,2)
        disp(correlation.AVG(i));
    end
    
    % Here it selects, if it is possible to offer the final result, for which
    % set of data, the result is the best (left, right or average)
    %=====================================================================
    if ( lOK && min(correlation.L) > correlationTreshhold  ...
    && ( isnan(stdAVG) || stdL <= stdAVG || min(correlation.AVG) <= correlationTreshhold ) ...
    && ( isnan(stdR) || stdL <= stdR || min(correlation.R) <= correlationTreshhold ) )
        disp('Selecting left slope');
        fres = fresL;
    elseif ( rOK && min(correlation.R) > correlationTreshhold ...
    && ( isnan(stdAVG) || stdR <= stdAVG || min(correlation.AVG) <= correlationTreshhold ) ...
    && ( isnan(stdL) || stdR <= stdL || min(correlation.L) <= correlationTreshhold ) )
        disp('Selecting right slope');
        fres = fresR;
    elseif ( avOK && min(correlation.AVG) > correlationTreshhold )
        disp('Selecting average slope');
        fres = fresAVG;
    else 
        error('Could not select slope for calibration, please verify the data');
    end

    disp(sprintf('Partial results median: %0.6e ',median(fres)));
    disp(sprintf('The final result of standard addition: %0.6e ± %0.6e',mean(fres), (std(fres)/sqrt(numel(fres))*tinv(1-(.05/2),length(fres)-1))));

end

function [slopeL, slopeR, slopeAVGfitRange, fitRange] = getSlopeInInflection(signal, peak, forceFitRange, fitRange, lineColor )
% I find this as one of the most important steps, I has gone trou many
% iterations, so the code is a bit of mixture of different ideas.
% Some tweakalbe setting:
%======================================================================
    fitSize = 5; %How many points should be fitted to get slope%
    maxHit = 4;  %How many times the slope has to change to call it inflection point%
    verbose = true; %Draw some additional plots%
    
    % Prepare data structures:
    %=========================
    hitCnt = 0;
    sigLen = length(signal);
    prevNormalFit = [ NaN NaN ];
    finalNormalFit = [ NaN NaN ];
    %signal = smooth(signal,13,'sgolay',3);
    signal = smooth(signal,17,'sgolay',3);
    
    if ( forceFitRange ) 
        % If we have already the point range in which the slope has to be
        % found (i.e. this is not the plot with the highest concentration)
        %=================================================================
        [blackhole,pos] = max(isnan(fitRange));
        fitrangeL = fitRange(1:pos-1);
        fitrangeR = fitRange(pos+1:end);

        % Get linear fit on the left side
        %===========================
        X = [ ones(fitSize,1) (1:1:fitSize)' ];
        normalFitX = pinv( X' * X );
        normalFitX = normalFitX * X';
        yL = signal(fitrangeL,1);
        normalFitL = normalFitX * yL;
        
        % Get linear fit on the rigth side
        %===========================
        yR = signal(fitrangeR,1);
        normalFitR = normalFitX * yR;

        % Get slopes:
        %======================
        slopeL = normalFitL(2);
        slopeR = normalFitR(2);
        
    else
        % This is either the plot with the highest concentration or
        % option.forceSamePoints == false
        % So first, we need to find the inflection point, and then
        % compute its slope.
        %==========================================================
        X = [ ones(fitSize,1) (1:1:fitSize)' ];
        normalFitX = pinv( X' * X );
        normalFitX = normalFitX * X';
        fitrange = [];
%         if ( verbose )
%             figure;
%         end
        for fitPos = peak:-1:fitSize
            % We start from the left side of the peak:
            %=========================================
            if ( peak < fitPos-fitSize )
                error('error');
            end
            fitrange = [ (fitPos-fitSize+1) :1: fitPos ];
            y = signal(fitrange,1);
            normalFit = normalFitX * y;

            if ( isnan(prevNormalFit(1)) )
                prevNormalFit = normalFit;
            elseif ( normalFit(2) < prevNormalFit(2) )
                if ( hitCnt == 0 ) 
                    finalFitrange = fitrange;
                    finalNormalFit = normalFit;
                end
                hitCnt = hitCnt+1;
                if ( hitCnt == maxHit ) 
                    break;
                end
            elseif ( normalFit(2) >= prevNormalFit(2) )
                finalNormalFit = [ NaN NaN ];
                hitCnt = 0;
            end
            prevNormalFit = normalFit;

%             if ( verbose ) 
%                 plot(X(:,2)+fitPos-5,y,'r*');
%                 hold on;
%                 plot(X(:,2)+fitPos-5,normalFit(1)+normalFit(2).*X(:,2));
%             end
        end
        if ( isnan(finalNormalFit(2)) ) 
            % fit failed %
            disp('failed');
        else
            slopeL = finalNormalFit(2);
            fitrangeL = finalFitrange;
        end
        fitrange = [];
%         if ( verbose )
%             figure;
%         end
        for fitPos = peak:1:(sigLen-fitSize)
            % And now rigth side:
            %====================
            fitrange= [ fitPos :1: (fitPos+fitSize-1) ];
            y = signal(fitrange,1);
            normalFit = normalFitX * y;
            if ( isnan(prevNormalFit(2)) )
                prevNormalFit = normalFit;
            elseif ( normalFit(2) > prevNormalFit(2) )
                if ( hitCnt == 0 ) 
                    finalFitrange = fitrange;
                    finalNormalFit = normalFit;
                end
                hitCnt = hitCnt+1;
                if ( hitCnt == maxHit ) 
                    break;
                end
            elseif ( normalFit(2) <= prevNormalFit(2) )
                finalNormalFit = [ NaN NaN ];
                hitCnt = 0;
            end
            prevNormalFit = normalFit;

%             if ( verbose ) 
%                 plot(X(:,2)+fitPos-1,y,'r*');
%                 hold on;
%                 plot(X(:,2)+fitPos-1,normalFit(1)+normalFit(2).*X(:,2));
%             end
        end
        if ( isnan(finalNormalFit(2)) ) 
            % fit failed %
        else
            slopeR = finalNormalFit(2);
            fitrangeR = finalFitrange;
        end
        fitRange = [ fitrangeL NaN fitrangeR ];
    end %end catch
    
    % This part provide alternative method of getting the slope in the
    % infleciton, as any noise will make it much more difficult, here are
    % tested approaches. This overrites previous method, as is more
    % difficult to follow.
    %=====================================================================
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

    % Get average slope (rigth slope has negative slope (or should have):
    %==================================================================
    slopeAVGfitRange = (slopeL - slopeR)/2;
    
    if ( verbose )
        plot(signal,'Color', lineColor); hold on;
        plot(fitrangeL,signal(fitrangeL),'*b', 'MarkerSize', 2);
        plot(fitrangeR,signal(fitrangeR),'*r', 'MarkerSize', 2);
    end
    
end

function [ matrixNANDIAG, removedORDER ] = minimizeCV( matrixNANDIAG, minEntities, minCVchange)
    % We can try 3-sigma here, however I think, this needs to be more
    % tweakable:
    %================================================================
    removedORDER = [];
    while ( size(matrixNANDIAG,1) > minEntities )
        inrow = inrows(matrixNANDIAG);
        oldstdrows = std(inrow');
        oldmeancvtotal = std(inrow(:)) / abs(mean(mean(inrow)));
        [mval, mpos]=max(oldstdrows);
        newmatrixNANDIAG = matrixNANDIAG;
        newmatrixNANDIAG(:,mpos) = [];
        newmatrixNANDIAG(mpos,:) = [];
        newinrow = inrows(newmatrixNANDIAG);
        newstd = std(newinrow(:));
        newmeancvtotal = newstd / abs(mean(mean(newinrow)));
        if ( (oldmeancvtotal-newmeancvtotal) > minCVchange )
            matrixNANDIAG = newmatrixNANDIAG;
            removedORDER = [ removedORDER mpos ];
        else
            break;
        end
    end
end

function inrow = inrows(mat)
    inrow = zeros(size(mat,1), size(mat,1)-1);
    pos = ones(size(mat,1) , 1);
    for i=1:size(mat,1)
        for ii=1:size(mat,1)
            if ( ~isnan(mat(i,ii)) )
                inrow(i,pos(i)) = mat(i,ii);
                inrow(ii,pos(ii)) = mat(i,ii);
                pos(i) = pos(i)+1;
                pos(ii) = pos(ii)+1;
            end
        end
    end
end
                    
            
"""

def getSlopeInInflection(sig, peakLocation, samePoints, firRange):
    import random
    return random.random(),0,0,[ x for x in range(1,20)]

if ( __name__ == '__main__' ):
    import prepareStructForSSAA
    stru = prepareStructForSSAA.importForSSAA()
    SlopeStandardAdditionAnalysis(stru, None, {})
