from manager.exceptions import VoltPyFailed


def check_analyte(curveSet, minimum_number=1):
    if len(curveSet.analytes.all()) < minimum_number:
        raise VoltPyFailed('Data needs to have at least %i analyte(s) defined.' % minimum_number)