from manager.exceptions import VoltPyFailed


def check_datalen(curveSet, minimum_points=1):
    for cd in curveSet.curvesData.all():
        if len(cd.yVector) < minimum_points:
            raise VoltPyFailed('Data needs to have at least %i data points.' % minimum_points)
