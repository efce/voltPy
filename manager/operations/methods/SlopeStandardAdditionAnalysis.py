import numpy as np
from manager.operations.methodsteps.selectanalyte import SelectAnalyte
from manager.operations.methodsteps.selectpoint import SelectPoint
import manager.operations.method as method
import manager.models as mmodels
import manager.plotmanager as pm
from manager.exceptions import VoltPyFailed
from manager.operations.checks.check_sampling import check_sampling
from manager.operations.checks.check_analyte import check_analyte


class SlopeStandardAdditionAnalysis(method.AnalysisMethod):
    can_be_applied = False
    _steps = (
        {
            'class': SelectAnalyte,
            'title': 'Select analyte',
            'desc': 'Select analyte.',
        },
        {
            'class': SelectPoint,
            'title': 'Select peak',
            'desc': """Enter approx. X value of peak of interest
            and press Forward, or press back to change the selection.""",
        },
    )
    checks = (check_sampling, check_analyte)
    description = """
Slope Standard Addition Analysis is advanced signal analysis method, 
which requires that the data was registered without current sample averaging
(also called multisampling). The method performs then analysis of the slope
of the peaks of interest in the inflection point, for a few different
measurement intervals. The method is described in [1], however, this is more
advanced implementation which chooses ever parameter automatically, and
requires only general position of peak of interest.<br />
<br />
[1] F. Ciepiela, K. Węgiel, "Novel method for standard addition
signal analysis in voltammetry" The Analyst, 2017, 142(10), 1729–1734.
<br />doi: 10.1039/C7AN00185A
    """

    @classmethod
    def __str__(cls):
        return "Slope Standard Addition Analysis"

    def finalize(self, user):
        from manager.helpers.slopeStandardAdditionAnalysis import slopeStandardAdditionAnalysis
        from manager.helpers.prepareStructForSSAA import prepareStructForSSAA
        Param = mmodels.Curve.Param
        self.model.custom_data['selectedIndex'] = \
            self.model.dataset.curves_data.all()[0].xValue2Index(SelectPoint.getData(self.model))
        peak = self.model.custom_data.get('selectedIndex', 0)
        X = []
        Conc = []
        tptw = 0
        analyte = self.model.dataset.analytes.all()[0]
        self.model.custom_data['analyte'] = analyte.name
        unitsTrans = dict(mmodels.Dataset.CONC_UNITS)
        self.model.custom_data['units'] = unitsTrans[self.model.dataset.analytes_conc_unit[analyte.id]]
        for cd in self.model.dataset.curves_data.all():
            X.append(cd.current_samples)
            Conc.append(self.model.dataset.analytes_conc.get(analyte.id, {}).get(cd.id, 0))
            tptw = cd.curve.params[Param.tp] + cd.curve.params[Param.tw]

        tp = 3
        twvec = self.__chooseTw(tptw)
        # TODO:Test if all curves are registered with the same method ?
        # have the same number of points ?
        numM = self.model.dataset.curves_data.all()[0].curve.params[Param.method]
        ctype = 'dp'
        if numM == Param.method_dpv:
            ctype = 'dp'
        elif numM == Param.method_npv:
            ctype = 'np'
        elif numM == Param.method_sqw:
            ctype = 'sqw'
        elif numM == Param.method_scv:
            ctype = 'sc'
        else:
            raise TypeError('Method number %i not supported' % numM)

        prepare = prepareStructForSSAA(X, Conc, tptw, 3, twvec, ctype)
                
        result = slopeStandardAdditionAnalysis(prepare, peak, {'forceSamePoints': True})
        self.model.custom_data['matrix'] = [
            result['CONC'],
            [x for x in result['Slopes'].items()]
        ]
        self.model.custom_data['fitEquation'] = result['Fit']
        self.model.custom_data['result'] = result['Mean']
        self.model.custom_data['resultStdDev'] = result['STD']
        self.model.custom_data['corrCoeff'] = result['R']
        self.model.completed = True
        self.model.step = None
        self.model.save()

    def exportableData(self):
        if not self.model.completed:
            raise VoltPyFailed('Incomplete data for export.')
        arrexp = np.array(self.model.custom_data['matrix'])
        return arrexp

    def apply(self, user, dataset):
        """
        This procedure cannot be applied to other data.
        """
        raise VoltPyFailed('Slope Standard Addition does not supports apply function.')

    def getFinalContent(self, request, user):
        p = pm.PlotManager()
        p.plot_width = 500
        p.plot_height = 400
        p.sizing_mode = 'fixed'
        p.xlabel = 'c_({analyte}) / {units}'.format(
            analyte=self.model.custom_data['analyte'],
            units=self.model.custom_data['units']
        )
        p.ylabel = 'i / µA'
        xvec = self.model.custom_data['matrix'][0]
        yvec = self.model.custom_data['matrix'][1]
        colors = ['blue', 'red', 'green', 'gray', 'cyan', 'yellow', 'magenta', 'orange']

        def getColor(x):
            return colors[x] if len(colors) > x else 'black'

        col_cnt = 0
        for sens, yrow in yvec:
            p.add(
                x=xvec,
                y=yrow,
                plottype='scatter',
                color=getColor(col_cnt),
                size=7
            )
            col_cnt += 1
        xvec2 = list(xvec)
        xvec2.append(-self.model.custom_data['result'])
        col_cnt = 0
        for k, fe in self.model.custom_data['fitEquation'].items():
            Y = [fe['slope'] * x + fe['intercept'] for x in xvec2]
            p.add(
                x=xvec2,
                y=Y,
                plottype='line',
                color=getColor(col_cnt),
                line_width=2
            )
            col_cnt += 1

        scripts, div, buttons = p.getEmbeded(request, user, 'analysis', self.model.id)
        unitsTrans = dict(mmodels.Dataset.CONC_UNITS)
        ret = {
            'head': scripts,
            'body': ''.join([
                '<table><tr><td style="width: 500px; height: 400px">',
                div,
                '</td></tr><tr><td>',
                '<p>Analyte: {0}<br />Result: {1} {3}<br />STD: {2} {3}</p>'.format(
                    self.model.custom_data['analyte'],
                    self.model.custom_data['result'],
                    self.model.custom_data['resultStdDev'],
                    self.model.custom_data['units'] 
                ),
                '</td></tr></table>'
            ])
        }
        return ret

    def __chooseTw(self, tptw):
        if tptw < 10:
            raise VoltPyFailed('Could not select tp and tw, too little samples per point.')
        elif tptw < 20:
            return [tptw-3, tptw-6, tptw-9]
        elif tptw < 32:
            return [tptw-4, tptw-10, tptw-15]
        else:
            n = int(np.floor(np.log2(tptw))) - 1
            dist = [(x**1.7 + 2) for x in range(n)]
            expmax = tptw - 5
            maxdist = np.max(dist)
            ok_dist = np.floor(np.multiply(dist, np.divide(expmax, maxdist)))
            ret_dist = [int(x) for x in ok_dist]
            return ret_dist

main_class = SlopeStandardAdditionAnalysis
