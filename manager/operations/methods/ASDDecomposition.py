import numpy as np
# import matplotlib.pyplot as plt
from django.utils import timezone
from overrides import overrides
import manager.models as mmodels
import manager.helpers.alternatingSlicewiseDiagonalization as asd
import manager.helpers.prepareDataForASD as prepare
import manager.operations.method as method
from manager.operations.methodsteps.selectanalyte import SelectAnalyte
from manager.operations.methodsteps.selectrange import SelectRange
from manager.operations.methodsteps.settings import Settings
from manager.exceptions import VoltPyNotAllowed
from manager.exceptions import VoltPyFailed
from manager.helpers.fithelpers import fit_capacitive_eq
from manager.helpers.fithelpers import calc_capacitive
from manager.operations.checks.check_sampling import check_sampling


class ASDDecomposition(method.ProcessingMethod):
    can_be_applied = False
    _steps = (
        {
            'class': SelectAnalyte,
            'title': 'Select analyte',
            'desc': """Select analyte.""",
        },
        {
            'class': SelectRange,
            'title': 'Select range',
            'desc': """
Select range for decomposition.
Range should extend about two width of the peak either way from it.
            """,
        },
        {
            'class': Settings,
            'title': 'Method settings',
            'desc': """
            Advanced settings, leave defaults if unsure.
            """

        }
    )

    checks = (check_sampling, )

    description = """
Decomposes the data into factors by the mean of trilinear decomposition,
and automatically selects, the one which is correlated to the selected analyte.
The methodology is based on [1] and ASD algorithm implementation
is based on [2].<br />
<br />
[1] F. Ciepiela, and M. Jakubowska, "Faradaic and Capacitive Current 
Estimation by DPV-ATLD", J. Electrochem. Soc., 2017, 164, 760-769.<br />
doi: 10.1149/2.0881712jes<br />
[2] N. M. Faber, R. Bro, and P. K. Hopke, "Recent developments in CANDECOMP/PARAFAC 
algorithms: A critical review", Chemom. Intell. Lab. Syst., 2003, 65, 119–137.<br />
doi: 10.1016/S0169-7439(02)00089-8

    """

    _allowed_types = (prepare.TYPE_SEPARATE, prepare.TYPE_TOGETHER, prepare.TYPE_COMBINED)

    @classmethod
    def __str__(cls):
        return "ASD Decomposition"

    @overrides
    def initialForStep(self, step_num):
        if step_num == 2:
            return {
                'Pulse and stair': {
                    'type': 'select',
                    'options': ['Pulse separate', 'Pulse together', 'Pulse combined'],
                    'default': 'Pulse combined',
                },
                'Data centering': {
                    'type': 'select',
                    'options': ['no', 'yes'],
                    'default': 'yes',
                }
            }

    def __perform(self, dataset: mmodels.Dataset):
        method_type = self.model.custom_data['MethodType']
        centering = self.model.custom_data['Centering']
        if method_type not in self._allowed_types:
            raise VoltPyFailed('Not allowed type.')

        Param = mmodels.Curve.Param

        cd1 = dataset.curves_data.all()[0]
        self.model.custom_data['tp'] = cd1.curve.params[Param.tp]
        self.model.custom_data['tw'] = cd1.curve.params[Param.tw]
        tptw = self.model.custom_data['tp'] + self.model.custom_data['tw']
        dE = cd1.curve.params[Param.dE]

        dec_start = cd1.xValue2Index(self.model.custom_data['DecomposeRange'][0])
        dec_end = cd1.xValue2Index(self.model.custom_data['DecomposeRange'][1])
        if dec_start > dec_end:
            dec_start, dec_end = dec_end, dec_start

        an_selected = self.model.analytes.all()[0]
        concs_different = dataset.getUncorrelatedConcs()
        an_selected_conc = dataset.getConc(an_selected.id)
        self.model.custom_data['analyte'] = an_selected.name

        if not an_selected_conc:
            raise VoltPyFailed('Wrong analyte selected.')

        an_num = len(concs_different)
        factors = an_num + 2

        main_data_1, main_data_2 = prepare.prepareDataForASD(
            dataset=dataset,
            start_index=dec_start,
            end_index=dec_end,
            tptw=tptw,
            method_type=method_type,
            centering=centering
        )

        if any([
            main_data_1.shape[0] < factors,
            main_data_1.shape[1] < factors,
            main_data_1.shape[2] < factors,
        ]):
            factors = np.min(main_data_1.shape)

        X0 = np.random.rand(factors, main_data_1.shape[0])
        Y0 = np.random.rand(factors, main_data_1.shape[1])

        # TODO: fit one combined array (step and pulse), check correlation for all analytes before selection.
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
        plt.subplot(311)
        plt.plot(SamplingPred1)
        plt.subplot(312)
        plt.plot(PotentialPred1)
        plt.subplot(313)
        plt.plot(ConcentrationPred1)
        plt.show()
        """
        if method_type == prepare.TYPE_SEPARATE:
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

        def recompose(bfd, method_type):
            if method_type != prepare.TYPE_COMBINED:
                mult = np.mean(bfd['x'][self.model.custom_data['tw']:])
                yvecs = np.dot(np.matrix(bfd['y']).T, np.matrix(bfd['z']))
                yvecs = np.dot(yvecs, mult)
            else:
                mult1 = np.mean(bfd['x'][self.model.custom_data['tw']:self.model.custom_data['tw'] + self.model.custom_data['tp']])
                mult2 = np.mean(bfd['x'][(2 * self.model.custom_data['tw'] + self.model.custom_data['tp']):])
                yvecs1 = np.dot(np.matrix(bfd['y']).T, np.matrix(bfd['z'])).dot(mult1)
                yvecs2 = np.dot(np.matrix(bfd['y']).T, np.matrix(bfd['z'])).dot(mult2)
                yvecs = np.zeros((yvecs1.shape[0] * 2, yvecs1.shape[1]))
                yvecs[0::2] = yvecs1
                yvecs[1::2] = yvecs2
            return yvecs

        if method_type == prepare.TYPE_SEPARATE:
            bfd0 = self._best_fit_factor(
                dE=dE,
                concs=an_selected_conc,
                SamplingPred=SamplingPred1,
                PotentialPred=PotentialPred1,
                ConcentrationPred=ConcentrationPred1
            )
            bfd1 = self._best_fit_factor(
                dE=dE,
                concs=an_selected_conc,
                SamplingPred=SamplingPred2,
                PotentialPred=PotentialPred2,
                ConcentrationPred=ConcentrationPred2
            )
            yv0 = recompose(bfd0, method_type)
            yv1 = recompose(bfd1, method_type)
            yvecs2 = np.subtract(yv1, yv0)

        elif method_type == prepare.TYPE_TOGETHER:
            bfd0 = self._best_fit_factor(
                dE=dE,
                concs=an_selected_conc,
                SamplingPred=SamplingPred1,
                PotentialPred=PotentialPred1,
                ConcentrationPred=ConcentrationPred1
            )
            yv0 = recompose(bfd0, method_type)
            yvecs2 = np.subtract(yv0[1::2], yv0[0::2])

        elif method_type == prepare.TYPE_COMBINED:
            bfd0 = self._best_fit_factor(
                dE=dE,
                concs=an_selected_conc,
                SamplingPred=SamplingPred1,
                PotentialPred=PotentialPred1,
                ConcentrationPred=ConcentrationPred1
            )
            yv0 = recompose(bfd0, method_type)
            yvecs2 = np.subtract(yv0[1::2], yv0[0::2])

        if yvecs2.shape[1] == dataset.curves_data.all().count():
            for i, cd in enumerate(dataset.curves_data.all()):
                newcd = cd.getCopy()
                newcd.setCrop(dec_start, dec_end)
                newcdConc = dataset.getCurveConcDict(cd)
                newy = np.array(yvecs2[:, i].T).squeeze()  # change to array to remove dimension
                newcd.yVector = newy
                newcd.date = timezone.now()
                newcd.save()
                dataset.removeCurve(cd)
                dataset.addCurve(newcd, newcdConc)
            dataset.save()
        else:
            raise VoltPyFailed('Computation error.')

    def finalize(self, user):
        settings = Settings.getData(self.model)
        self.model.custom_data['DecomposeRange'] = SelectRange.getData(self.model)
        self.model.custom_data['MethodType'] = int(settings.get('Pulse and stair', 0))
        self.model.custom_data['Centering'] = int(settings.get('Data centering', 1))
        self.__perform(self.model.dataset)
        self.model.step = None
        self.model.completed = True
        self.model.save()

    def apply(self, user, dataset):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(dataset)

    def _best_fit_factor(self, dE, concs, SamplingPred, PotentialPred, ConcentrationPred):
        capac_index = -1
        capac_r2 = 0
        if False:
            for i, sp in enumerate(SamplingPred.T):
                if sp[1] > 0:
                    yvec = sp
                else:
                    yvec = np.dot(sp, -1)
                x = np.arange(0, len(yvec))

                capac_fit, capac_cov = fit_capacitive_eq(
                    xvec=x,
                    yvec=yvec,
                    dE=dE
                )
                yc_pred = calc_capacitive(x, dE, *capac_fit)
                r2c = np.power(np.corrcoef(yc_pred, yvec)[0, 1], 2)
                """
                import matplotlib.pyplot as plt
                print(i, ':', r2c)
                plt.plot(sp, 'g')
                plt.plot(yc_pred, 'r')
                plt.show()
                """

                """
                farad_fit, farad_cov = fit_faradaic_eq(
                    xvec=x,
                    yvec=yvec
                )
                yf_pred = calc_faradaic(x, *farad_fit)
                r2f = np.power(np.corrcoef(yf_pred, yvec)[0, 1], 2)
                """

                if r2c > capac_r2:
                    capac_r2 = r2c
                    capac_index = i

        tobeat = 0
        best_factor = -1
        for i, cp in enumerate(ConcentrationPred.T):
            if i == capac_index:
                continue
            rr = np.corrcoef(cp, concs)
            if np.abs(rr[0, 1]) > tobeat:
                best_factor = i
                tobeat = np.abs(rr[0, 1])

        if best_factor == -1:
            raise VoltPyFailed('Decomposed factors do not meet the requirements.')

        chosen = {}
        chosen['x'] = SamplingPred[:, best_factor]
        chosen['y'] = PotentialPred[:, best_factor]
        chosen['z'] = ConcentrationPred[:, best_factor]
        return chosen

    def remove_bkg_current(self, data):
        t1 = data[-1, 0::2, :].squeeze()
        t2 = data[-1, 1::2, :].squeeze()
        data[:, 0::2, :] = np.subtract(data[:, 0::2, :], np.median(t1))
        data[:, 1::2, :] = np.subtract(data[:, 1::2, :], np.median(t2))
        return data
