import numpy as np
import matplotlib.pyplot as plt
from django.utils import timezone
import manager.models as mmodels
import manager.helpers.alternatingSlicewiseDiagonalization as asd
import manager.operations.method as method
from manager.operations.methodsteps.selectanalyte import SelectAnalyte
from manager.exceptions import VoltPyNotAllowed
from manager.exceptions import VoltPyFailed
from manager.helpers.functions import check_curveset_integrity
from manager.helpers.fithelpers import fit_capacitive_eq
from manager.helpers.fithelpers import calc_capacitive


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

    type_seperate = 0
    type_together = 1
    type_combined = 2
    _allowed_types = (type_combined, type_seperate, type_together)

    @classmethod
    def __str__(cls):
        return "ASD Decomposition"

    def __perform(self, curveSet):
        method_type = self.type_together
        if method_type not in self._allowed_types:
            raise VoltPyFailed('Not allowed type.')

        Param = mmodels.Curve.Param

        cd1 = curveSet.curvesData.all()[0]
        self.model.customData['tp'] = cd1.curve.params[Param.tp]
        self.model.customData['tw'] = cd1.curve.params[Param.tw]
        tptw = cd1.curve.params[Param.tp] + cd1.curve.params[Param.tw]
        dE = cd1.curve.params[Param.dE]

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
        check_curveset_integrity(self.model.curveSet, params_to_check)

        analyte = curveSet.analytes.all()[0]
        self.model.customData['analyte'] = analyte.name
        an_num = len(curveSet.analytes.all())
        factors = an_num + 5  # if interested in faradaic +2 if in capac +1

        concs = []
        for cd in curveSet.curvesData.all():
            concs.append(curveSet.analytesConc[analyte.id].get(cd.id, 0))

        if method_type == self.type_seperate:
            main_data_1 = np.zeros(
                (tptw, int(len(cd1.currentSamples)/tptw/2), len(curveSet.curvesData.all()))
            )
            main_data_2 = np.zeros(
                (tptw, int(len(cd1.currentSamples)/tptw/2), len(curveSet.curvesData.all()))
            )
            for cnum, cd in enumerate(curveSet.curvesData.all()):
                pos = 0
                for i in np.arange(0, len(cd1.currentSamples), 2*tptw):
                    pos = int(i/(2*tptw))
                    main_data_1[:, pos, cnum] = cd.currentSamples[i:(i+tptw)]
                    main_data_2[:, pos, cnum] = cd.currentSamples[(i+tptw):(i+(2*tptw))]

        elif method_type == self.type_together:
            main_data_1 = np.zeros(
                (tptw, int(len(cd1.currentSamples)/tptw), len(curveSet.curvesData.all()))
            )
            for cnum, cd in enumerate(curveSet.curvesData.all()):
                pos = 0
                for i in np.arange(0, len(cd1.currentSamples), tptw):
                    pos = int(i/tptw)
                    main_data_1[:, pos, cnum] = cd.currentSamples[i:(i+tptw)]
            plt.plot(main_data_1[-1, :, :])
            plt.title('przed')
            plt.show()
            main_data_1 = self.remove_bkg_current(main_data_1)

        elif method_type == self.type_combined:
            main_data_1 = np.zeros(
                (2*tptw, int(len(cd1.currentSamples)/tptw/2), len(curveSet.curvesData.all()))
            )
            for cnum, cd in enumerate(curveSet.curvesData.all()):
                pos = 0
                for i in np.arange(0, len(cd1.currentSamples), 2*tptw):
                    pos = int(i/(2*tptw))
                    main_data_1[:, pos, cnum] = cd.currentSamples[i:(i+2*tptw)]

        X0 = np.random.rand(factors, main_data_1.shape[0])
        Y0 = np.random.rand(factors, main_data_1.shape[1])

        plt.plot(main_data_1[-1, :, :])
        plt.show()

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
        plt.subplot(131)
        plt.plot(SamplingPred1)
        plt.subplot(132)
        plt.plot(PotentialPred1)
        plt.subplot(133)
        plt.plot(ConcentrationPred1)
        plt.show()


        if method_type == self.type_seperate:
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
                mult = np.mean(bfd['x'][self.model.customData['tw']:])
                yvecs = np.dot(np.matrix(bfd['y']).T, np.matrix(bfd['z']))
                yvecs = np.dot(yvecs, mult)
            else:
                mult1 = np.mean(bfd['x'][self.model.customData['tw']:self.model.customData['tp']])
                mult2 = np.mean(bfd['x'][(2*self.model.customData['tw']+self.model.customData['tp']):])
                yvecs1 = np.dot(np.matrix(bfd['y']).T, np.matrix(bfd['z'])).dot(mult1)
                yvecs2 = np.dot(np.matrix(bfd['y']).T, np.matrix(bfd['z'])).dot(mult2)
                yvecs = np.zeros((yvecs1.shape[0]*2, yvecs1.shape[1]))
                yvecs[0::2] = yvecs1
                yvecs[1::2] = yvecs2
            return yvecs

        if method_type == self.type_seperate:
            bfd0 = self._best_fit_factor(
                dE=dE,
                concs=concs,
                SamplingPred=SamplingPred1,
                PotentialPred=PotentialPred1,
                ConcentrationPred=ConcentrationPred1
            )
            bfd1 = self._best_fit_factor(
                dE=dE,
                concs=concs,
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
                concs=concs,
                SamplingPred=SamplingPred1,
                PotentialPred=PotentialPred1,
                ConcentrationPred=ConcentrationPred1
            )
            yv0 = recompose(bfd0, method_type)
            yvecs2 = np.subtract(yv0[1::2], yv0[0::2])

        elif method_type == self.type_combined:
            pass

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

    def _best_fit_factor(self, dE, concs, SamplingPred, PotentialPred, ConcentrationPred):
        capac_index = -1
        capac_r2 = 0
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
                # Prefer lower index because it has higher total variance
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
