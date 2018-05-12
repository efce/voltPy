from manager.exceptions import VoltPyFailed


def check_sampling(curveSet, same_sampling=True):
    if len(curveSet.curvesData.all()) == 0:
        return
    ptnr = len(curveSet.curvesData.all()[0].currentSamples)
    if ptnr == 0:
        raise VoltPyFailed('Data have to include multi-sampling (nonaveraged).')
    if same_sampling:
        for cd in curveSet.curvesData.all():
            if len(cd.currentSamples) != ptnr:
                raise VoltPyFailed('Each curve needs to have the same sampling length.')
