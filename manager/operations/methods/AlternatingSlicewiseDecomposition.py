import numpy as np
from scipy.optimize import curve_fit
from manager.operations.methodsteps.selectanalyte import SelectAnalyte
import manager.operations.method as method
import manager.models as mmodels
import manager.plotmanager as pm
from manager.exceptions import VoltPyFailed


class AlternatingSlicewiseDecomposition(method.AnalysisMethod):
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
the one which is correlated to the selected analytes and
tries to calculate final result with standard addition method.
It uses ASD, which is implemented based on:

N. M. Faber, R. Bro, and P. K. Hopke, 
“Recent developments in CANDECOMP/PARAFAC algorithms:A critical review,”
Chemom. Intell. Lab. Syst., vol. 65, no. 1, pp. 119–137, 2003.

    """

    @classmethod
    def __str__(cls):
        return "Alternating Slice-wise Decomposition"

    def finalize(self, user):
        import manager.helpers.alternatingSlicewiseDiagonalization as asd
        Param = mmodels.Curve.Param
        cs = self.model.curveSet
        cd1 = cs.curvesData.all()[0]
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
        for cd in cs.curvesData.all():
            for p in needSame:
                if cd.curve.params[p] != cd1.curve.params[p]:
                    raise VoltPyFailed('All curves in curveSet have to be similar.')
        
        self.model.customData['tp'] = cd1.curve.params[Param.tp]
        self.model.customData['tw'] = cd1.curve.params[Param.tw]
        tptw = cd1.curve.params[Param.tp] + cd1.curve.params[Param.tw]
        analyte = cs.analytes.all()[0]
        concs = []
        for cd in cs.curvesData.all():
            concs.append(cs.analytesConc[analyte.id].get(cd.id, 0))
        self.model.customData['analyte'] = analyte.name
        self.model.customData['units'] = cs.analytesConcUnits[analyte.id]
        main_data = np.zeros((tptw, int(len(cd1.currentSamples)/tptw), len(cs.curvesData.all())))
        for i in np.arange(0, len(cd1.currentSamples), tptw):
            i = int(i)
            for ii, cd in enumerate(cs.curvesData.all()):
                pos = int(i/tptw)
                main_data[:, pos, ii] = cd.currentSamples[i:i+tptw]
        an_num = len(cs.analytes.all())
        factors = an_num + 2

        X0 = []
        Y0 = []
        for i in range(factors):
            X0.append([x for x in np.random.rand(main_data.shape[0], 1)])
            Y0.append([x for x in np.random.rand(main_data.shape[1], 1)])

        SamplingPred, PotentialPred, ConcentrationPred, errflag, iter_num, cnv = asd.asd(
            main_data,
            X0,
            Y0,
            main_data.shape[0],
            main_data.shape[1],
            main_data.shape[2],
            factors,
            1,
            0.000001,
            250
        )

        dE = cd1.curve.params[Param.dE]

        def capacitive(t, R, eps, tau):
            return dE/R * np.exp(-(t+eps)/tau)
        capacitive_bounds = ((0, 0, 0), (10**10, 1000, 10000))

        def faradaic(t, a, eps):
            return np.dot(a, np.sqrt(np.add(t, eps)))
        faradaic_bounds = ((-10**7, 0), (10**7, 1000))
        
        is_farad = []
        #import pdb; pdb.set_trace()
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
            raise VoltPyFailed
        
        self.model.customData['matrix'] = [concs, factor_conc]
        self.model.customData['bestFactorData'] = {
            'x': SamplingPred[:, best_factor],
            'y': PotentialPred[:, best_factor],
            'z': ConcentrationPred[:, best_factor]
        }
        self.model.customData['RegressionLine'] = np.polyfit(concs, factor_conc, 1)
        self.model.save()

    def exportableData(self):
        raise NotImplementedError

    def apply(self, user, curveSet):
        """
        This procedure cannot be applied to other data.
        """
        raise VoltPyFailed('Slope Standard Addition does not supports apply function.')

    def getFinalContent(self, request, user):
        p = pm.PlotManager()
        p.plot_width = 500
        p.plot_height = 400
        unitsTrans = dict(mmodels.CurveSet.CONC_UNITS)
        p.xlabel = 'c_({analyte}) / {units}'.format(
            analyte=self.model.customData['analyte'],
            units=unitsTrans.get(self.model.customData['units'], 'M')
        )
        p.ylabel = 'a.u.'
        xvec = self.model.customData['matrix'][0]
        yvec = self.model.customData['matrix'][1]

        p.add(
            x=xvec,
            y=yvec,
            plottype='scatter',
            color='red',
            size=7
        )

        x = [0, xvec[-1]]
        eq = self.model.customData['RegressionLine']
        if eq[0] != 0:
            x[0] = -eq[1]/eq[0]
        y = np.polyval(eq, x)
        p.add(
            x=x,
            y=y,
            plottype='line',
            color='blue',
        )
        scripts, div = p.getEmbeded(request, user, 'analysis', self.model.id)

        bfd = self.model.customData['bestFactorData']
        mult = np.mean(bfd['x'][self.model.customData['tw']:])
        yvecs = np.dot(np.matrix(bfd['y']).T, np.matrix(bfd['z']))
        yvecs = np.dot(yvecs, mult)
        yvecs2 = np.zeros((int(yvecs.shape[0]/2),yvecs.shape[1]))
        for i in np.arange(0, yvecs.shape[0]-1, 2):
            i = int(i)
            yvecs2[int(i/2), :] = yvecs[i+1, :] - yvecs[i, :]
        p2 = pm.PlotManager()
        p2.plot_width = 500
        p2.plot_height = 400
        cs = self.model.curveSet
        for yv in yvecs2.T:
            yvf = [x for x in yv.T]
            p2.add(
                y=yvf,
                x=cs.curvesData.all()[0].potential,
                plottype='line'
            )
        scripts2, div2 = p2.getEmbeded(request, user, 'curveset', self.model.id)
        ret = {
            'head': '\n'.join([scripts, scripts2]),
            'body': ''.join([
                div,
                '<p>Analyte: {0}<br />Result: {1} {3}<br />STD: {2} {3}</p>'.format(
                    self.model.customData['analyte'],
                    -x[0],
                    0,
                    unitsTrans.get(self.model.customData['units'], 'M')
                ),
                div2
            ])
        }
        return ret

main_class = AlternatingSlicewiseDecomposition
