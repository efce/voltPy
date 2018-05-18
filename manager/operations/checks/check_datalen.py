from manager.exceptions import VoltPyFailed


def check_datalen(dataset, minimum_points=1):
    for cd in dataset.curves_data.all():
        if len(cd.yVector) < minimum_points:
            raise VoltPyFailed('Data needs to have at least %i data points.' % minimum_points)
