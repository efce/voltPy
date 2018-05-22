import numpy as np
import manager.models as mmodels
from manager.models import Dataset
from manager.exceptions import VoltPyFailed

TYPE_SEPARATE = 0
TYPE_TOGETHER = 1
TYPE_COMBINED = 2


def prepareDataForASD(
        dataset: Dataset,
        start_index: int,
        end_index: int,
        tptw: int,
        method_type: int,
        centering: bool
):
    cds = dataset.curves_data.all()
    if len(cds) == 0:
        raise VoltPyFailed('Dataset error.')
    cd1 = cds[0]
    Param = mmodels.Curve.Param
    if all([
        cd1.curve.params[Param.method] != Param.method_dpv,
        cd1.curve.params[Param.method] != Param.method_sqw
    ]):
        raise VoltPyFailed('Method works only for DP/SQW data.')

    needSame = [
        Param.tp,
        Param.tw,
        Param.ptnr,
        Param.nonaveragedsampling,
        Param.Ep,
        Param.Ek,
        Param.Estep
    ]
    for cd in cds:
        for p in needSame:
            if cd.curve.params[p] != cd1.curve.params[p]:
                raise VoltPyFailed('All curves in dataset have to be similar.')

    if method_type == TYPE_SEPARATE:
        main_data_1 = np.zeros(
            (tptw, int(len(cd1.current_samples)/tptw/2), len(cds))
        )
        main_data_2 = np.zeros(
            (tptw, int(len(cd1.current_samples)/tptw/2), len(cds))
        )
        for cnum, cd in enumerate(cds):
            pos = 0
            for i in np.arange(0, len(cd1.current_samples), 2*tptw):
                pos = int(i/(2*tptw))
                main_data_1[:, pos, cnum] = cd.current_samples[i:(i+tptw)]
                main_data_2[:, pos, cnum] = cd.current_samples[(i+tptw):(i+(2*tptw))]
        main_data_1 = main_data_1[:, start_index:end_index, :]
        main_data_2 = main_data_2[:, start_index:end_index, :]

    elif method_type == TYPE_TOGETHER:
        main_data_1 = np.zeros(
            (tptw, int(len(cd1.current_samples)/tptw), len(cds))
        )
        for cnum, cd in enumerate(cds):
            pos = 0
            for i in np.arange(0, len(cd1.current_samples), tptw):
                pos = int(i/tptw)
                main_data_1[:, pos, cnum] = cd.current_samples[i:(i+tptw)]
        main_data_1 = main_data_1[:, 2*start_index:2*end_index, :]

    elif method_type == TYPE_COMBINED:
        main_data_1 = np.zeros(
            (2*tptw, int(len(cd1.current_samples)/tptw/2), len(cds))
        )
        for cnum, cd in enumerate(cds):
            pos = 0
            for i in np.arange(0, len(cd1.current_samples), 2*tptw):
                pos = int(i/(2*tptw))
                main_data_1[:, pos, cnum] = cd.current_samples[i:(i+2*tptw)]
        main_data_1 = main_data_1[:, start_index:end_index, :]

    if centering:
        main_mean = np.mean(main_data_1, axis=0)
        for i in range(main_data_1.shape[1]):
            for ii in range(main_data_1.shape[2]):
                main_data_1[:, i, ii] = main_data_1[:, i, ii] - main_mean[i, ii]
        if method_type == TYPE_SEPARATE:
            main_mean2 = np.mean(main_data_2, axis=0)
            for i in range(main_data_2.shape[1]):
                for ii in range(main_data_2.shape[2]):
                    main_data_2[:, i, ii] = main_data_2[:, i, ii] - main_mean2[i, ii]

    if method_type == TYPE_SEPARATE:
        return (main_data_1, main_data_2)
    return (main_data_1, None)
