from manager.exceptions import VoltPyFailed


def check_datalenuniform(dataset, minimum_points=1):
    if len(dataset.curves_data.all()) == 0:
        return
    ptnr = len(dataset.curves_data.all()[0].yVector)
    for cd in dataset.curves_data.all():
        if len(cd.yVector) < minimum_points:
            raise VoltPyFailed('Data needs to have at least %i data points.' % minimum_points)
        elif len(cd.yVector) != ptnr:
            raise VoltPyFailed('Each curve needs to have the same number of data points.')