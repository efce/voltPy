from manager.exceptions import VoltPyFailed


def check_analyte(dataset, minimum_number=1):
    if len(dataset.analytes.all()) < minimum_number:
        raise VoltPyFailed('Data needs to have at least %i analyte(s) defined.' % minimum_number)