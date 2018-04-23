import numpy as np
from scipy.optimize import curve_fit
from django.utils import timezone
# import matplotlib.pyplot as plt
from manager.operations.methodsteps.confirmation import Confirmation
import manager.operations.method as method
import manager.models as mmodels
from manager.exceptions import VoltPyFailed, VoltPyNotAllowed


class ASDCellTime(method.AnalysisMethod):
    can_be_applied = False
    _steps = (
        {
            'class': Confirmation,
            'title': 'Confirm',
            'desc': """Confirm start of ASD cell time estimation.""",
        },
    )
    description = """
Decomposes the data into factors with ASD, and tries to estimate the cell time costant
based on the capacitive factor.
Uses implementation of ASD based on:

N. M. Faber, R. Bro, and P. K. Hopke, 
“Recent developments in CANDECOMP/PARAFAC algorithms:A critical review,”
Chemom. Intell. Lab. Syst., vol. 65, no. 1, pp. 119–137, 2003.

    """

    @classmethod
    def __str__(cls):
        return "ASD Cell Time Est."

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

        def capacitive(t, R, eps, tau):
            return np.dot(np.divide(dE, R), np.exp(-np.divide(np.add(t, eps), tau)))
        capacitive_bounds = ((0, 0, 0), (10**10, 1000, 10000))

        def faradaic(t, a, eps):
            return np.dot(a, np.sqrt(np.add(t, eps)))
        faradaic_bounds = ((-10**7, 0), (10**7, 1000))

        def best_fit_factor(SamplingPred, PotentialPred, ConcentrationPred):
            cov_to_beat = 0
            best_factor = None
            import pdb; pdb.set_trace()
            for i, sp in enumerate(SamplingPred.T):
                x = np.array(range(sp.shape[0]-1))
                farad_fit, farad_cov = curve_fit(
                    f=faradaic,
                    xdata=x,
                    ydata=sp[1:],
                    bounds=faradaic_bounds
                )
                capac_fit, capac_cov = curve_fit(
                    f=capacitive,
                    xdata=x,
                    ydata=sp[1:],
                    bounds=capacitive_bounds
                )

                if capac_cov[0, 1] > farad_cov[0, 1]:
                    if capac_cov[0, 1] > cov_to_beat:
                        cov_to_beat = capac_cov[0, 1]
                        best_factor = i

            if best_factor is None:
                raise VoltPyFailed('Could not determine the capacitive factor.')

            chosen = {}
            chosen['x'] = SamplingPred[:, best_factor]
            chosen['y'] = PotentialPred[:, best_factor]
            chosen['z'] = ConcentrationPred[:, best_factor]
            return chosen

        bfd0 = best_fit_factor(SamplingPred1, PotentialPred1, ConcentrationPred1)
        bfd1 = best_fit_factor(SamplingPred2, PotentialPred2, ConcentrationPred2)
        randnum = np.random.randint(0, len(bfd0['y']), size=10)

        # Calculate tau in 10 random points for both best factors and all curves:
        cfits = []
        for bfd in (bfd0, bfd1):
            xv = np.array(range(len(bfd['x'])))
            for ri in randnum:
                for cp in bfd['z']:
                    sampling_recovered = np.dot(bfd['x'], cp).dot(bfd['y'][ri])
                    capac_fit, capac_cov = curve_fit(
                        f=capacitive,
                        xdata=xv,
                        ydata=sampling_recovered,
                        bounds=capacitive_bounds
                    )
                    cfits.append(capac_fit)
        import pdb; pdb.set_trace()
        cfits = np.array(cfits)

    def finalize(self, user):
        self.__perform(self.model.curveSet)
        self.model.step = None
        self.model.completed = True
        self.model.save()

    def apply(self, user, curveSet):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(curveSet)
    
    def exportableData(self):
        return None

    def getFinalContent(self, request, user):
        return None


main_class = ASDCellTime
