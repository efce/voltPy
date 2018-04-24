import numpy as np
from scipy.optimize import curve_fit
from django.utils import timezone
# import matplotlib.pyplot as plt
from manager.operations.methodsteps.selectanalyte import SelectAnalyte
import manager.operations.method as method
import manager.models as mmodels
from manager.exceptions import VoltPyNotAllowed
from manager.exceptions import VoltPyFailed
from manager.helpers.fithelpers import fit_capacitive_eq
from manager.helpers.fithelpers import fit_faradaic_eq


class ASDDecomposition(method.ProcessingMethod):
    can_be_applied = False
    _steps = (
        {
            'class': SelectAnalyte,
            'title': 'Select analyte',
            'desc': """Select analyte.""",
        },
    )
    description = """
Decomposes the data into factor, for which automatically selects,
the one which is correlated to the selected analyte.
It uses ASD, which is implemented based on:

N. M. Faber, R. Bro, and P. K. Hopke, 
“Recent developments in CANDECOMP/PARAFAC algorithms:A critical review,”
Chemom. Intell. Lab. Syst., vol. 65, no. 1, pp. 119–137, 2003.

    """

    @classmethod
    def __str__(cls):
        return "ASD Decomposition"

    def __perform(self, curveSet):
        import manager.helpers.alternatingSlicewiseDiagonalization as asd
        Param = mmodels.Curve.Param
        cd1 = curveSet.curvesData.all()[0]
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
        # TODO: assert all curves have the same tp/tw and no. of points
        for cd in curveSet.curvesData.all():
            for p in needSame:
                if cd.curve.params[p] != cd1.curve.params[p]:
                    raise VoltPyFailed('All curves in curveSet have to be similar.')

        self.model.customData['tp'] = cd1.curve.params[Param.tp]
        self.model.customData['tw'] = cd1.curve.params[Param.tw]
        tptw = cd1.curve.params[Param.tp] + cd1.curve.params[Param.tw]
        analyte = curveSet.analytes.all()[0]
        concs = []
        for cd in curveSet.curvesData.all():
            concs.append(curveSet.analytesConc[analyte.id].get(cd.id, 0))
        self.model.customData['analyte'] = analyte.name
        main_data_1 = np.zeros((tptw, int(len(cd1.currentSamples)/tptw/2), len(curveSet.curvesData.all())))
        main_data_2 = np.zeros((tptw, int(len(cd1.currentSamples)/tptw/2), len(curveSet.curvesData.all())))
        for cnum, cd in enumerate(curveSet.curvesData.all()):
            pos = 0
            for i in np.arange(0, len(cd1.currentSamples), 2*tptw):
                pos = int(i/(2*tptw))
                main_data_1[:, pos, cnum] = cd.currentSamples[i:(i+tptw)]
                main_data_2[:, pos, cnum] = cd.currentSamples[(i+tptw):(i+(2*tptw))]
        an_num = len(curveSet.analytes.all())
        factors = an_num + 2

        X0 = []
        Y0 = []
        for i in range(factors):
            X0.append([x for x in np.random.rand(main_data_1.shape[0], 1)])
            Y0.append([x for x in np.random.rand(main_data_1.shape[1], 1)])

        SamplingPred1, PotentialPred1, ConcentrationPred1, errflag1, iter_num1, cnv1 = asd.asd(
            main_data_1,
            X0,
            Y0,
            main_data_1.shape[0],
            main_data_1.shape[1],
            main_data_1.shape[2],
            factors,
            1,
            0.000001,
            100
        )
        X0 = SamplingPred1.T
        Y0 = PotentialPred1.T
        SamplingPred2, PotentialPred2, ConcentrationPred2, errflag2, iter_num2, cnv2 = asd.asd(
            main_data_2,
            X0,
            Y0,
            main_data_1.shape[0],
            main_data_1.shape[1],
            main_data_1.shape[2],
            factors,
            1,
            0.000001,
            100
        )

        dE = cd1.curve.params[Param.dE]

        def best_fit_factor(SamplingPred, PotentialPred, ConcentrationPred):
            is_farad = []
            for i, sp in enumerate(SamplingPred.T):
                x = np.array(range(sp.shape[0]-1))
                if sp[1] > 0:
                    yvec = sp[1:]
                else:
                    yvec = np.dot(sp[1:], -1)
                farad_fit, farad_cov = fit_faradaic_eq(
                    xvec=x,
                    yvec=yvec
                )
                capac_fit, capac_cov = fit_capacitive_eq(
                    xvec=x,
                    yvec=yvec,
                    dE=dE
                )

                if capac_cov[0, 1] > farad_cov[0, 1]:
                    is_farad.append(False)
                else:
                    is_farad.append(True)

            tobeat = 0
            best_factor = -1
            factor_conc = []
            for i, cp in enumerate(ConcentrationPred.T):
                if not is_farad[i]:
                    continue
                rr = np.corrcoef(cp, concs)
                if np.abs(rr[0, 1]) > ((1/1+(1-tobeat)) * tobeat):
                    # Prefer lower index because it has higher total variance
                    best_factor = i
                    tobeat = np.abs(rr[0, 1])
                    factor_conc = cp

            if best_factor == -1:
                raise VoltPyFailed('Decomposed factors do not meet the requriements.')

            chosen = {}
            chosen['x'] = SamplingPred[:, best_factor]
            chosen['y'] = PotentialPred[:, best_factor]
            chosen['z'] = ConcentrationPred[:, best_factor]
            return chosen

        def recompose(bfd):
            mult = np.mean(bfd['x'][self.model.customData['tw']:])
            yvecs = np.dot(np.matrix(bfd['y']).T, np.matrix(bfd['z']))
            yvecs = np.dot(yvecs, mult)
            return yvecs

        bfd0 = best_fit_factor(SamplingPred1, PotentialPred1, ConcentrationPred1)
        bfd1 = best_fit_factor(SamplingPred2, PotentialPred2, ConcentrationPred2)
        yv0 = recompose(bfd0)
        yv1 = recompose(bfd1)
        yvecs2 = np.subtract(yv1, yv0)

        if yvecs2.shape[1] == len(curveSet.curvesData.all()):
            for i, cd in enumerate(curveSet.curvesData.all()):
                newcd = cd.getCopy()
                newcdConc = curveSet.getCurveConcDict(cd)
                newy = np.array(yvecs2[:, i].T).squeeze()  # change to array to remove dimension
                newcd.yVector = newy
                newcd.date = timezone.now()
                newcd.save()
                curveSet.removeCurve(cd)
                curveSet.addCurve(newcd, newcdConc)
            curveSet.save()
        else:
            raise VoltPyFailed('Computation error.')

    def finalize(self, user):
        self.__perform(self.model.curveSet)
        self.model.step = None
        self.model.completed = True
        self.model.save()

    def apply(self, user, curveSet):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(curveSet)


main_class = ASDDecomposition
