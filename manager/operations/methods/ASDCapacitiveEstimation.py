import numpy as np
# import matplotlib.pyplot as plt
from scipy.stats import t
from manager.operations.methodsteps.confirmation import Confirmation
import manager.operations.method as method
import manager.models as mmodels
import manager.helpers.alternatingSlicewiseDiagonalization as asd
import manager.helpers.prepareDataForASD as prepare
from manager.exceptions import VoltPyFailed
from manager.exceptions import VoltPyNotAllowed
from manager.helpers.fithelpers import fit_capacitive_eq
from manager.helpers.fithelpers import fit_faradaic_eq
from manager.helpers.fithelpers import calc_capacitive
from manager.helpers.fithelpers import calc_faradaic
from manager.operations.checks.check_sampling import check_sampling


class ASDCapacitiveEstimation(method.AnalysisMethod):
    can_be_applied = False
    _steps = (
        {
            'class': Confirmation,
            'title': 'Confirm',
            'desc': """Confirm start of ASD cell time estimation.""",
        },
    )
    checks = (check_sampling, )
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
        return "ASD capacitive estimators"

    def __perform(self, dataset):
        if dataset.curves_data.all().count() == 0:
            raise VoltPyFailed('Dataset error.')
        Param = mmodels.Curve.Param

        cd1 = dataset.curves_data.all()[0]
        self.model.custom_data['tp'] = cd1.curve.params[Param.tp]
        self.model.custom_data['tw'] = cd1.curve.params[Param.tw]

        tptw = cd1.curve.params[Param.tp] + cd1.curve.params[Param.tw]
        dE = cd1.curve.params[Param.dE]

        an_num = dataset.analytes.all().count()
        factors = (an_num + 1) if an_num > 0 else 2

        main_data_1, main_data_2 = prepare.prepareDataForASD(
            dataset=dataset,
            start_index=0,
            end_index=len(cd1.xVector),
            tptw=tptw,
            method_type=prepare.TYPE_TOGETHER,
            centering=False,
        )
        X0 = np.random.rand(factors, main_data_1.shape[0])
        Y0 = np.random.rand(factors, main_data_1.shape[1])

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
        """
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
        """

        def best_fit_factor(SamplingPred, PotentialPred, ConcentrationPred):
            capac_r2 = 0
            capac_index = None
            for i, sp in enumerate(SamplingPred.T):
                x = np.array(range(sp.shape[0]-1))
                if sp[1] > 0:
                    yvec = sp[1:]
                else:
                    yvec = np.dot(sp[1:], -1)
                capac_fit, capac_cov = fit_capacitive_eq(xvec=x, yvec=yvec, dE=dE)
                yc_pred = calc_capacitive(x, dE, *capac_fit)
                r2c = np.power(np.corrcoef(yc_pred, yvec)[0, 1], 2)

                if r2c > capac_r2:
                    capac_r2 = r2c
                    capac_index = i

            if capac_index is None:
                raise VoltPyFailed('Could not determine the capacitive factor.')

            chosen = {}
            chosen['x'] = SamplingPred[:, capac_index]
            chosen['y'] = PotentialPred[:, capac_index]
            chosen['z'] = ConcentrationPred[:, capac_index]
            return chosen

        bfd0 = best_fit_factor(SamplingPred1, PotentialPred1, ConcentrationPred1)
        # bfd1 = best_fit_factor(SamplingPred2, PotentialPred2, ConcentrationPred2)
        randnum = np.random.randint(0, len(bfd0['y']), size=10)

        # Calculate tau in 10 random points for both best factors and all curves:
        cfits = []
        for bfd in [bfd0]:  # (bfd0, bfd1):
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
        self.model.custom_data['Tau'] = fit_mean[0, 2]
        self.model.custom_data['TauStdDev'] = fit_std[0, 2]
        self.model.custom_data['Romega'] = fit_mean[0, 0]
        self.model.custom_data['RomegaStdDev'] = fit_std[0, 0]
        self.model.custom_data['BestFitData'] = {}
        self.model.custom_data['BestFitData'][0] = bfd0
        # self.model.custom_data['BestFitData'][1] = bfd1
        self.model.save()

    def finalize(self, user):
        self.__perform(self.model.dataset)
        self.model.step = None
        self.model.completed = True
        self.model.save()

    def apply(self, user, dataset):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(dataset)
    
    def exportableData(self):
        return None

    def getFinalContent(self, request, user):
        from manager.helpers.fithelpers import significant_digit
        n = len(self.model.custom_data['BestFitData'][0]['z'])
        ta = t.ppf(0.975, n)
        tau_ci = self.model.custom_data['TauStdDev'] * ta / np.sqrt(n)
        rom_ci = self.model.custom_data['RomegaStdDev'] * ta / np.sqrt(n)
        sigtau = significant_digit(tau_ci)
        sigrom = significant_digit(rom_ci)
        return {
            'head': '',
            'body': """<p>Estimates for &alpha;=0.05:<br />
                        Tau: {tau}&plusmn;{tauci}&nbsp;ms(?)<br />
                        Romega: {rom}&plusmn;{romci}&nbsp;Ohm</p>
                    """.format(
                tau='%.*f' % (sigtau, self.model.custom_data['Tau']),
                tauci='%.*f' % (sigtau, tau_ci),
                rom='%.*f' % (sigrom, self.model.custom_data['Romega']),
                romci='%.*f' % (sigrom, rom_ci)
            )
        }


main_class = ASDCapacitiveEstimation
