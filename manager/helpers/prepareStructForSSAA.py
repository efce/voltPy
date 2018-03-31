from manager.helpers.setTpTw import *


def prepareStructForSSAA(rawData, concVec, realStepTime, tpValue, twVector, technique):
    """
    This funtion prepares raw data from 1 ms measurement for further
    processing by standardAddition()
    rawData -- is data from measurement (nrofpoints x nrofmeasurements)
    concVect -- is vector containing the concentration of analyte of each
               column of rawData
    tptotal -- is total number of samples per measurement point (usually
              tp+tw)
    tpVal -- value of tp to be used for callibration (usually low 1-5)
    twVect -- vector of values of tw's to prepare the final calibration set
             (eg. [ 5 10 15 20] - provides 4 sets for calibration)
    technique -- voltammetric technique: 'sc' | 'np' | 'dp' | 'sqw'
    """
    assert (len(concVec) == len(rawData)), ('len(concVec)=%i and len(rawData)=%i' % (len(concVec), len(rawData)))

    dataStruct = dict(
        X=[],
        Y=[],
        CONC=[],
        SENS=[]
    )

    data = dataStruct
    for i, dataColumn in enumerate(rawData):
        for itw, twValue in enumerate(twVector):
            data['Y'].append([])
            data['CONC'].append([])
            data['SENS'].append([])
            data['Y'][-1], __, __ = setTpTw(dataColumn, realStepTime, tpValue, twValue, technique)
            data['CONC'][-1] = concVec[i]
            data['SENS'][-1] = itw

    return data
