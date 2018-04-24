import numpy as np
from abc import ABC
import manager.models as mmodels
from manager.models import Curve as mcurve
Param = mcurve.Param


class Parser(ABC):
    """
    This is a template for creating a new parser,
    however, it is recommended to extend the Txt
    parser in case of generic text files.
    """
    _curves = []

    class CurveFromFile():
        name = ''
        comment = ''
        vec_param = [0] * Param.PARAMNUM
        vec_time = []
        vec_potential = []
        vec_current = []
        vec_sampling = []
        date = ''

    methodDict = {
        'lsv': Param.method_lsv,
        'scv': Param.method_scv,
        'npv': Param.method_npv,
        'dpv': Param.method_dpv,
        'swv': Param.method_sqw,
        'chronoamp': -1
    }

    def saveModels(self, user):
        cf = mmodels.CurveFile(
            owner=user,
            name=self.cfile.name,
            fileName=self.cfile.name,
            fileDate=self._curves[0].date,
        )
        cs = mmodels.CurveSet(
            owner=user,
            name=self.cfile.name
        )
        cs.save()
        cf.curveSet = cs
        cf.save()

        order = 0
        for c in self._curves:
            cb = mmodels.Curve(
                curveFile=cf,
                orderInFile=order,
                name=c.name,
                comment=c.comment,
                params=c.vec_param,
                date=c.date
            )
            cb.save()

            cd = mmodels.CurveData(
                curve=cb,
                date=c.date,
                time=c.vec_time,
                potential=c.vec_potential,
                current=c.vec_current,
                currentSamples=c.vec_sampling
            )
            cd.save()
            cs.curvesData.add(cd)

            ci = mmodels.CurveIndex(
                curve=cb,
                potential_min=np.min(c.vec_potential),
                potential_max=np.max(c.vec_potential),
                potential_step=c.vec_potential[1]-c.vec_potential[0],
                time_min=np.min(c.vec_time),
                time_max=np.max(c.vec_time),
                time_step=c.vec_time[1]-c.vec_time[0],
                current_min=np.min(c.vec_current),
                current_max=np.max(c.vec_current),
                current_range=np.max(c.vec_current)-np.min(c.vec_current),
                samplingRate=c.vec_param[Param.nonaveragedsampling],
            )
            ci.save()
            order += 1

        cs.save()
        return cf.id

    @staticmethod
    def calculateMethod(yvec, pointsPerPoint, method=Param.method_dpv):
        yvec_avg = []
        for i in range(int(len(yvec)/pointsPerPoint)):
            yvec_avg.append(np.average(yvec[i*pointsPerPoint:i*pointsPerPoint+pointsPerPoint]))
        yvec_res = []
        if method == Param.method_dpv or method == Param.method_npv:
            for i in np.arange(0, len(yvec_avg), 2):
                yvec_res.append(yvec_avg[i+1]-yvec_avg[i])
        elif method == Param.method_sqw:
            for i in np.arange(0, len(yvec_avg), 2):
                yvec_res.append(yvec_avg[i]-yvec_avg[i+1])
        else:
            yvec_res = yvec_avg
        return yvec_res
