import numpy as np
from manager.operations.methodsteps.selectanalyte import SelectAnalyte
from manager.operations.methodsteps.selectpoint import SelectPoint
import manager.operations.method as method
import manager.models as mmodels
import manager.plotmanager as pm
from manager.exceptions import VoltPyFailed


class SlopeStandardAdditionAnalysis(method.AnalysisMethod):
    _steps = (
        {
            'class': SelectAnalyte,
            'title': 'Select analyte',
            'desc': """Select analyte.""",
        },
        {
            'class': SelectPoint,
            'title': 'Select peak',
            'desc': 'Enter approx. X value of peak of interest and press Forward, or press back to change the selection.',
        },
    )
    description = """
Slope Standard Addition Analysis is advanced signal analysis method, 
which requires that the data was registerd without current sample averaging
(called also multisampling). The method performs then analysis of the slope
of the peaks of interest in the inflection point, for a few different
measurement intervals. The method is descibed in [1], however, this is more
advanced implementation which chooses ever paramter automatically, and
requires only general position of peak of interest.

[1] Ciepiela, F., & Węgiel, K. (2017). Novel method for standard addition
signal analysis in voltammetry. The Analyst, 142(10), 1729–1734.
https://doi.org/10.1039/C7AN00185A
    """

    @classmethod
    def __str__(cls):
        return "Slope Standard Addition Analysis"

    def finalize(self, user):
        from manager.helpers.slopeStandardAdditionAnalysis import slopeStandardAdditionAnalysis
        from manager.helpers.prepareStructForSSAA import prepareStructForSSAA
        Param = mmodels.Curve.Param
        self.model.customData['selectedIndex'] = \
            self.model.curveSet.curvesData.all()[0].xvalueToIndex(user, self.model.stepsData['SelectPoint'])
        peak = self.model.customData.get('selectedIndex', 0)
        X = []
        Conc = []
        tptw = 0
        analyte = self.model.curveSet.analytes.all()[0]
        self.model.customData['analyte'] = analyte.name
        unitsTrans = dict(mmodels.CurveSet.CONC_UNITS)
        self.model.customData['units'] = unitsTrans[self.model.curveSet.analytesConcUnits[analyte.id]]
        for cd in self.model.curveSet.curvesData.all():
            X.append(cd.currentSamples)
            Conc.append(self.model.curveSet.analytesConc.get(analyte.id, {}).get(cd.id, 0))
            tptw = cd.curve.params[Param.tp] + cd.curve.params[Param.tw]

        tp = 3
        twvec = self.__chooseTw(tptw)
        if not twvec:
            raise VoltPyFailed('Could not select tp and tw, too little samples per point.')
        numM = self.model.curveSet.curvesData.all()[0].curve.params[Param.method]
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
            raise TypeError('Method numer %i not supported' % numM)

        prepare = prepareStructForSSAA(X, Conc, tptw, 3, twvec, ctype)
                
        result = slopeStandardAdditionAnalysis(prepare, peak, {'forceSamePoints': True})
        self.model.customData['matrix'] = [ 
            result['CONC'], 
            [x for x in result['Slopes'].items()]
        ]
        self.model.customData['fitEquation'] = result['Fit']
        self.model.customData['result'] = result['Mean']
        self.model.customData['resultStdDev'] = result['STD']
        self.model.customData['corrCoeff'] = result['R']
        self.model.completed = True
        self.model.step = None
        self.model.save()

    def exportableData(self):
        if not self.model.completed:
            raise VoltPyFailed('Incomplete data for export.')
        arrexp = np.array(self.model.customData['matrix'])
        return arrexp

    def getFinalContent(self, request, user):
        p = pm.PlotManager()
        p.plot_width = 500
        p.plot_height = 400
        p.xlabel = 'c_({analyte}) / {units}'.format(
            analyte=self.model.customData['analyte'],
            units=self.model.customData['units']
        )
        p.ylabel = 'i / µA'
        xvec = self.model.customData['matrix'][0]
        yvec = self.model.customData['matrix'][1]
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
        xvec2.append(-self.model.customData['result'])
        col_cnt = 0
        for k, fe in self.model.customData['fitEquation'].items():
            Y = [fe['slope']*x+fe['intercept'] for x in xvec2]
            p.add(
                x=xvec2,
                y=Y,
                plottype='line',
                color=getColor(col_cnt),
                line_width=2
            )
            col_cnt += 1

        scripts, div = p.getEmbeded(request, user, 'analysis', self.model.id)
        unitsTrans = dict(mmodels.CurveSet.CONC_UNITS)
        ret = { 
            'head': scripts,
            'body': ''.join([
                                div, 
                                '<p>Analyte: {0}<br />Result: {1} {3}<br />STD: {2} {3}</p>'.format(
                                    self.model.customData['analyte'],
                                    self.model.customData['result'],
                                    self.model.customData['resultStdDev'],
                                    self.model.customData['units'] 
                                )
                            ])
        }
        return ret

    def __chooseTw(self, tptw):
        if (tptw < 9):
            return None
        elif (tptw < 20):
            return [tptw-3, tptw-6, tptw-9]
        if (tptw < 40):
            return [tptw-3, tptw-7, tptw-11]
        else:
            n = np.floor(tptw/12)
            d = np.floor(np.sqrt(n))
            return [tptw-((x*d)-3) for x in range(n)]

main_class = SlopeStandardAdditionAnalysis