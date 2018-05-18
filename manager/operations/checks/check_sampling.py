from manager.exceptions import VoltPyFailed


def check_sampling(dataset, same_sampling=True):
    if len(dataset.curves_data.all()) == 0:
        return
    ptnr = len(dataset.curves_data.all()[0].current_samples)
    if ptnr == 0:
        raise VoltPyFailed('Data have to include multi-sampling (nonaveraged).')
    if same_sampling:
        for cd in dataset.curves_data.all():
            if len(cd.current_samples) != ptnr:
                raise VoltPyFailed('Each curve needs to have the same sampling length.')
