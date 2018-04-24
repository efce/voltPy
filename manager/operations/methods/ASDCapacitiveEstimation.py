import numpy as np
# import matplotlib.pyplot as plt
from scipy.stats import t
from manager.operations.methodsteps.confirmation import Confirmation
import manager.operations.method as method
import manager.models as mmodels
from manager.exceptions import VoltPyFailed
from manager.exceptions import VoltPyNotAllowed
from manager.helpers.fithelpers import fit_capacitive_eq
from manager.helpers.fithelpers import fit_faradaic_eq


class ASDCapacitiveEstimation(method.AnalysisMethod):
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
and cell resistance based on the capacitive factor.
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

        def best_fit_factor(SamplingPred, PotentialPred, ConcentrationPred):
            cov_to_beat = 0
            best_factor = None
            for i, sp in enumerate(SamplingPred.T):
                x = np.array(range(sp.shape[0]-1))
                if sp[1] > 0:
                    yvec = sp[1:]
                else:
                    yvec = np.dot(sp[1:], -1)
                farad_fit, farad_cov = fit_faradaic_eq(xvec=x, yvec=yvec)
                capac_fit, capac_cov = fit_capacitive_eq(xvec=x, yvec=yvec, dE=dE)

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
                    if sampling_recovered[1] > 0:
                        yvec = sampling_recovered
                    else:
                        yvec = np.dot(sampling_recovered, -1)
                    capac_fit, capac_cov = fit_capacitive_eq(
                        xvec=xv,
                        yvec=yvec,
                        dE=dE
                    )
                    cfits.append(capac_fit)
        cfits = np.matrix(cfits)
        fit_mean = np.mean(cfits, axis=0)
        fit_std = np.std(cfits, axis=0)
        self.model.customData['Tau'] = fit_mean[0, 2]
        self.model.customData['TauStdDev'] = fit_std[0, 2]
        self.model.customData['Romega'] = fit_mean[0, 0]
        self.model.customData['RomegaStdDev'] = fit_std[0, 0]
        self.model.customData['BestFitData'] = {}
        self.model.customData['BestFitData'][0] = bfd0
        self.model.customData['BestFitData'][1] = bfd1
        self.model.save()

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
        from manager.helpers.fithelpers import significant_digit
        n = len(self.model.customData['BestFitData'][0]['z'])
        ta = t.ppf(0.975, n)
        tau_ci = self.model.customData['TauStdDev'] * ta / np.sqrt(n)
        rom_ci = self.model.customData['RomegaStdDev'] * ta / np.sqrt(n)
        sigtau = significant_digit(tau_ci)
        sigrom = significant_digit(rom_ci)
        return {
            'head': '',
            'body': """<p>Estimates for &alpha;=0.05:<br />
                        Tau: {tau}&plusmn;{tauci}&nbsp;ms(?)<br />
                        Romega: {rom}&plusmn;{romci}&nbsp;Ohm</p>
                    """.format(
                tau='%.*f' % (sigtau, self.model.customData['Tau']),
                tauci='%.*f' % (sigtau, tau_ci),
                rom='%.*f' % (sigrom, self.model.customData['Romega']),
                romci='%.*f' % (sigrom, rom_ci)
            )
        }


main_class = ASDCapacitiveEstimation
