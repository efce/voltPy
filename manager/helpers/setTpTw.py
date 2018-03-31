import numpy as np


def setTpTw(data, realStepTime, tpValue, twValue, technique):
    """
    setTpTw is simple function to process RAW data form electrochemical
    analyzer. I can process data from SCV, DPV and NPV techniques.
    sig - signal with raw data (readout from A/D converter)
    realStepTime - total probing time of one step (i.e. in SCV it is tp, in DPV and
        NPV it is 2*tp
    tpValue - new tp time
    twValue - new wait time (tp + tw =< realStepTime)
    technique - type of technique: 'sc', 'scv', 'dp', 'dpv' 'dpasv', 'dpas' ,
        'np', 'npv', 'npasv', 'sqw', 'swv'

    if returns touple of
    ( finalVector, onPulseVector, onStepVector)
    """
    # TODO: preallocate arrays ?
    sumtptw = twValue + tpValue
    assert realStepTime >= sumtptw
    averagedTmp = []
    scvLike = ['sc', 'scv']
    pulseLike = ['dp', 'dpv', 'np', 'npv']
    sqwLike = ['sqw', 'swv']
    for i in np.arange(0, len(data), realStepTime):
        st = (i+twValue)
        end = st+tpValue
        averagedTmp.append(np.mean(data[st:end]))

    if technique in scvLike:
        return averagedTmp, averagedTmp, averagedTmp
    
    elif technique in pulseLike:
        res = []
        partial1 = []
        partial2 = []
        for i in np.arange(0, len(averagedTmp)-1, 2):
            i = int(i)
            res.append(averagedTmp[i+1] - averagedTmp[i] )
            partial1.append(averagedTmp[i])
            partial2.append(averagedTmp[i+1])

        return res, partial1, partial2

    elif technique in sqwLike:
        res = []
        partial1 = []
        partial2 = []

        for i in np.arange(0, len(averagedTmp)-1, 2):
            i = int(i)
            res.append(averagedTmp[i] - averagedTmp[i+1])
            partial1.append(averagedTmp[i+1])
            partial2.append(averagedTmp[i])
        return res, partial1, partial2

    else:
        raise LookupError('Unknown technique: %s' % technique)
