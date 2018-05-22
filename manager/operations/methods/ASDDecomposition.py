import numpy as np
import matplotlib.pyplot as plt
from django.utils import timezone
from overrides import overrides
import manager.models as mmodels
import manager.helpers.alternatingSlicewiseDiagonalization as asd
import manager.operations.method as method
from manager.operations.methodsteps.selectanalyte import SelectAnalyte
from manager.operations.methodsteps.selectrange import SelectRange
from manager.operations.methodsteps.settings import Settings
from manager.exceptions import VoltPyNotAllowed
from manager.exceptions import VoltPyFailed
from manager.helpers.functions import check_dataset_integrity
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
Decomposes the data into factor, for which automatically selects,
the one which is correlated to the selected analyte.
It uses ASD, which is implemented based on:

N. M. Faber, R. Bro, and P. K. Hopke, 
“Recent developments in CANDECOMP/PARAFAC algorithms:A critical review,”
Chemom. Intell. Lab. Syst., vol. 65, no. 1, pp. 119–137, 2003.

    """

    type_separate = 0
    type_together = 1
    type_combined = 2
    _allowed_types = (type_combined, type_separate, type_together)

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
                    'default': 'Pulse separate',
                },
                'Data centering': {
                    'type': 'select',
                    'options': ['no', 'yes'],
                    'default': 'yes',
                }
            }

    def __perform(self, dataset):
        method_type = self.model.custom_data['MethodType']
        centering = self.model.custom_data['Centering']
        if method_type not in self._allowed_types:
            raise VoltPyFailed('Not allowed type.')

        Param = mmodels.Curve.Param

        cd1 = dataset.curves_data.all()[0]
        self.model.custom_data['tp'] = cd1.curve.params[Param.tp]
        self.model.custom_data['tw'] = cd1.curve.params[Param.tw]
        tptw = cd1.curve.params[Param.tp] + cd1.curve.params[Param.tw]
        dE = cd1.curve.params[Param.dE]
        dec_start = cd1.xValue2Index(self.model.custom_data['DecomposeRange'][0])
        dec_end = cd1.xValue2Index(self.model.custom_data['DecomposeRange'][1])
        if dec_start > dec_end:
            dec_start, dec_end = dec_end, dec_start

        if all([
                cd1.curve.params[Param.method] != Param.method_dpv,
                cd1.curve.params[Param.method] != Param.method_sqw
        ]):
            raise VoltPyFailed('Method works only for DP/SQW data.')

        params_to_check = [
            Param.tp,
            Param.tw,
            Param.ptnr,
            Param.nonaveragedsampling,
            Param.Ep,
            Param.Ek,
            Param.Estep
        ]
        check_dataset_integrity(self.model.dataset, params_to_check)

        an_selected = self.model.analytes.all()[0]
        concs_different = dataset.getUncorrelatedConcs()
        an_selected_conc = dataset.getConc(an_selected.id)
        self.model.custom_data['analyte'] = an_selected.name

        if not an_selected_conc:
            raise VoltPyFailed('Wrong analyte selected.')

        an_num = len(concs_different)
        factors = an_num + 2  # if interested in faradaic +2 if in capac +1

        if method_type == self.type_separate:
            main_data_1 = np.zeros(
                (tptw, int(len(cd1.current_samples)/tptw/2), len(dataset.curves_data.all()))
            )
            main_data_2 = np.zeros(
                (tptw, int(len(cd1.current_samples)/tptw/2), len(dataset.curves_data.all()))
            )
            for cnum, cd in enumerate(dataset.curves_data.all()):
                pos = 0
                for i in np.arange(0, len(cd1.current_samples), 2*tptw):
                    pos = int(i/(2*tptw))
                    main_data_1[:, pos, cnum] = cd.current_samples[i:(i+tptw)]
                    main_data_2[:, pos, cnum] = cd.current_samples[(i+tptw):(i+(2*tptw))]
            main_data_1 = main_data_1[:, dec_start:dec_end, :]
            main_data_2 = main_data_2[:, dec_start:dec_end, :]

        elif method_type == self.type_together:
            main_data_1 = np.zeros(
                (tptw, int(len(cd1.current_samples)/tptw), len(dataset.curves_data.all()))
            )
            for cnum, cd in enumerate(dataset.curves_data.all()):
                pos = 0
                for i in np.arange(0, len(cd1.current_samples), tptw):
                    pos = int(i/tptw)
                    main_data_1[:, pos, cnum] = cd.current_samples[i:(i+tptw)]
            main_data_1 = main_data_1[:, 2*dec_start:2*dec_end, :]
            main_data_1 = self.remove_bkg_current(main_data_1)

        elif method_type == self.type_combined:
            main_data_1 = np.zeros(
                (2*tptw, int(len(cd1.current_samples)/tptw/2), len(dataset.curves_data.all()))
            )
            for cnum, cd in enumerate(dataset.curves_data.all()):
                pos = 0
                for i in np.arange(0, len(cd1.current_samples), 2*tptw):
                    pos = int(i/(2*tptw))
                    main_data_1[:, pos, cnum] = cd.current_samples[i:(i+2*tptw)]
            main_data_1 = main_data_1[:, dec_start:dec_end, :]
        
        if centering:
            main_mean = np.mean(main_data_1, axis=0)
            for i in range(main_data_1.shape[1]):
                for ii in range(main_data_1.shape[2]):
                    main_data_1[:, i, ii] = main_data_1[:, i, ii] - main_mean[i, ii]
            if method_type == self.type_separate:
                main_mean2 = np.mean(main_data_2, axis=0)
                for i in range(main_data_2.shape[1]):
                    for ii in range(main_data_2.shape[2]):
                        main_data_2[:, i, ii] = main_data_2[:, i, ii] - main_mean2[i, ii]

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
        plt.subplot(311)
        plt.plot(SamplingPred1)
        plt.subplot(312)
        plt.plot(PotentialPred1)
        plt.subplot(313)
        plt.plot(ConcentrationPred1)
        plt.show()

        if method_type == self.type_separate:
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
            if method_type != self.type_combined:
                mult = np.mean(bfd['x'][self.model.custom_data['tw']:])
                yvecs = np.dot(np.matrix(bfd['y']).T, np.matrix(bfd['z']))
                yvecs = np.dot(yvecs, mult)
            else:
                mult1 = np.mean(bfd['x'][self.model.custom_data['tw']:self.model.custom_data['tw'] + self.model.custom_data['tp']])
                mult2 = np.mean(bfd['x'][(2*self.model.custom_data['tw']+self.model.custom_data['tp']):])
                yvecs1 = np.dot(np.matrix(bfd['y']).T, np.matrix(bfd['z'])).dot(mult1)
                yvecs2 = np.dot(np.matrix(bfd['y']).T, np.matrix(bfd['z'])).dot(mult2)
                yvecs = np.zeros((yvecs1.shape[0]*2, yvecs1.shape[1]))
                yvecs[0::2] = yvecs1
                yvecs[1::2] = yvecs2
            return yvecs

        if method_type == self.type_separate:
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

        elif method_type == self.type_together:
            bfd0 = self._best_fit_factor(
                dE=dE,
                concs=an_selected_conc,
                SamplingPred=SamplingPred1,
                PotentialPred=PotentialPred1,
                ConcentrationPred=ConcentrationPred1
            )
            yv0 = recompose(bfd0, method_type)
            yvecs2 = np.subtract(yv0[1::2], yv0[0::2])

        elif method_type == self.type_combined:
            bfd0 = self._best_fit_factor(
                dE=dE,
                concs=an_selected_conc,
                SamplingPred=SamplingPred1,
                PotentialPred=PotentialPred1,
                ConcentrationPred=ConcentrationPred1
            )
            yv0 = recompose(bfd0, method_type)
            yvecs2 = np.subtract(yv0[1::2], yv0[0::2])

        if yvecs2.shape[1] == len(dataset.curves_data.all()):
            for i, cd in enumerate(dataset.curves_data.all()):
                newcd = cd.getCopy()
                newcdConc = dataset.getCurveConcDict(cd)
                newy = np.array(yvecs2[:, i].T).squeeze()  # change to array to remove dimension
                newcd.yVector = newy
                newcd.xVector = newcd.xVector[dec_start:dec_end]
                newcd.date = timezone.now()
                newcd.save()
                dataset.removeCurve(cd)
                dataset.addCurve(newcd, newcdConc)
            dataset.save()
        else:
            raise VoltPyFailed('Computation error.')

    def finalize(self, user):
        self.model.custom_data['DecomposeRange'] = self.model.steps_data['SelectRange']
        self.model.custom_data['MethodType'] = int(self.model.steps_data['Settings'].get('Pulse and stair', 0))
        self.model.custom_data['Centering'] = int(self.model.steps_data['Settings'].get('Data centering', 1))
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


main_class = ASDDecomposition
