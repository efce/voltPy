import numpy as np
import math as math

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
    #TODO: preallocate arrays ?
    sumtptw = twValue + tpValue
    assert(realStepTime >= sumtptw)
    averagedTmp = []
    scvLike = [ 'sc', 'scv' ]
    pulseLike = [ 'dp', 'dpv', 'np', 'npv' ]
    sqwLike = [ 'sqw', 'swv' ]
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

        for i in np.arage(0, len(averagedTmp)-1, 2):
            i = int(i)
            res.append(averagedTmp[i] - averagedTmp[i+1] )
            partial1.append(averagedTmp[i+1])
            partial2.append(averagedTmp[i])
        return res, partial1, partial2

    else:
        raise LookupError('Unknown technique: %s' % technique)


if ( __name__ == '__main__' ):
    data = [-133.117676,-81.481934,-55.908203,-41.015625,-31.860352,-25.512695,-21.118164,-17.883301,-15.441895,-13.732910,-12.207031,-11.047363,-10.253906,-9.338379,-8.728027,-8.239746,-7.690430,-7.324219,-6.958008,-6.652832,136.962891,81.481934,54.077148,38.269043,28.381348,21.911621,17.395020,14.099121,11.596680,9.765625,8.178711,7.141113,6.164551,5.310059,4.577637,4.089355,3.601074,3.234863,2.868652,2.502441,-132.507324,-81.176758,-55.480957,-40.954590,-31.616211,-25.390625,-21.057129,-17.822266,-15.441895,-13.549805,-12.268066,-11.047363,-10.131836,-9.277344,-8.728027,-8.056641,-7.812500,-7.324219,-6.896973,-6.591797,136.474609,81.054688,53.649902,37.963867,28.381348,21.667480,17.272949,14.099121,11.535645,9.704590,8.239746,7.019043,6.042480,5.371094,4.638672,4.150391,3.601074,3.234863,2.807617,2.502441,-132.080078,-80.749512,-55.358887,-40.710449,-31.433105,-25.329590,-20.935059,-17.700195,-15.441895,-13.610840,-12.145996,-10.925293,-10.070801,-9.399414,-8.605957,-8.178711,-7.812500,-7.263184,-6.958008,-6.469727,136.108398,80.871582,53.405762,37.902832,28.076172,21.606445,17.150879,13.977051,11.352539,9.582520,8.239746,6.958008,6.042480,5.310059,4.638672,4.028320,3.540039,3.112793,2.807617,2.380371]
    a, p1, p2 = setTpTw(data, 20, 5, 5, 'dpv')
    print(a)
    print(p1)
    print(p2)

