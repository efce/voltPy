import numpy as np
from scipy.stats import t
import manager.operations.method as method
from manager.operations.methodsteps.selectanalyte import SelectAnalyte
from manager.operations.methodsteps.selectrange import SelectRange
import manager.plotmanager as pm
import manager.models as mmodels
from manager.helpers.fithelpers import calc_normal_equation_fit
from manager.helpers.fithelpers import calc_sx0
from manager.helpers.fithelpers import significant_digit
from manager.exceptions import VoltPyFailed


class RegularStandardAddition(method.AnalysisMethod):
    can_be_applied = True
    _steps = [
        {
            'class': SelectAnalyte,
            'title': 'Select analyte',
            'desc': """Select analyte.""",
        },
        {
            'class': SelectRange,
            'title': 'Select range',
            'desc': 'Select range containing peak and press Forward, or press Back to change the selection.',
        },
    ]
    description = """
This is standard addition method, where the height of the signal is
calculated as a difference between max and min signal in the given range.
""".replace('\n', ' ')

    @classmethod
    def __str__(cls):
        return "Regular Standard Addition"

    def exportableData(self):
        if not self.model.completed:
            raise VoltPyFailed('Incomplete data')
        return np.matrix(self.model.customData['matrix']).T

    def apply(self, user, curveSet):
        an = self.model.getCopy()
        an.curveSet = curveSet
        an.appliesModel = self.model
        an.save()
        self.model = an
    #try:
        self.finalize(user)
    #except:
        #an.deleted = True
        #an.save()
        #raise VoltPyFailed('Could not apply model.')
        return an.id

    def finalize(self, user):
        xvalues = []
        yvalues = []
        selRange = self.model.stepsData['SelectRange']
        analyte = self.model.curveSet.analytes.all()[0]
        self.model.customData['analyte'] = analyte.name
        unitsTrans = dict(mmodels.CurveSet.CONC_UNITS)
        self.model.customData['units'] = unitsTrans[self.model.curveSet.analytesConcUnits[analyte.id]]
        for cd in self.model.curveSet.curvesData.all():
            startIndex = cd.xValue2Index(selRange[0])
            endIndex = cd.xValue2Index(selRange[1])
            if endIndex < startIndex:
                endIndex, startIndex = startIndex, endIndex
            yvalues.append(max(cd.yVector[startIndex:endIndex])-min(cd.yVector[startIndex:endIndex]))
            xvalues.append(self.model.curveSet.analytesConc.get(analyte.id, {}).get(cd.id, 0))

        data = [
            [float(b) for b in xvalues],
            [float(b) for b in yvalues]
        ]
        self.model.customData['matrix'] = data
        p = calc_normal_equation_fit(data[0], data[1])
        sx0, sslope, sintercept = calc_sx0(p['slope'], p['intercept'], data[0], data[1])
        if p['slope'] != 0:
            self.model.customData['fitEquation'] = p
            self.model.customData['slopeStdDev'] = sslope
            self.model.customData['interceptStdDev'] = sintercept
            self.model.customData['result'] = p['intercept']/p['slope']
            self.model.customData['resultStdDev'] = sx0,
            self.model.customData['corrCoef'] = np.corrcoef(data[0], data[1])[0, 1]
        else:
            self.model.customData['fitEquation'] = p
            self.model.customData['result'] = None
            self.model.customData['resultStdDev'] = None
            self.model.customData['corrCoef'] = None
        self.model.completed = True
        self.model.step = 0
        self.model.save()

    def getFinalContent(self, request, user):
        p = pm.PlotManager()
        data = p.analysisHelper(self.model.owner, self.model.id)
        for d in data:
            p.add(**d)
        p.plot_width = 500
        p.plot_height = 400
        p.xlabel = 'c_({analyte}) / {units}'.format(
            analyte=self.model.customData['analyte'],
            units=self.model.customData['units']
        )
        p.ylabel = 'i / µA'
        scr, div = p.getEmbeded(request, user, 'analysis', self.model.id)
        n = len(self.model.customData['matrix'][0])
        talpha = t.ppf(0.975, n-2)
        conf_interval = np.multiply(self.model.customData['resultStdDev'], talpha)
        sd = significant_digit(conf_interval, 2)
        slope_interval = np.multiply(self.model.customData['slopeStdDev'], talpha)
        slopesd = significant_digit(slope_interval, 2)
        int_interval = np.multiply(self.model.customData['interceptStdDev'], talpha)
        intsd = significant_digit(int_interval, 2)
        return {
            'head': scr,
            'body': ''.join([
                div,
                """
                    Analyte: {an}<br />
                    Equation: y = {slope}(&plusmn;{sci}) &middot; x + {int}(&plusmn;{ici})<br />
                    r = {corrcoef}<br />
                    Result: {res}&plusmn;{ci} {anu}
                """.format(
                    res='%.*f' % (sd, self.model.customData['result']),
                    ci='%.*f' % (sd, conf_interval),
                    corrcoef='%.4f' % self.model.customData['corrCoef'],
                    slope='%.*f' % (slopesd, self.model.customData['fitEquation']['slope']),
                    sci='%.*f' % (slopesd, slope_interval),
                    int='%.*f' % (intsd, self.model.customData['fitEquation']['intercept']),
                    ici='%.*f' % (intsd, int_interval),
                    an=self.model.customData['analyte'],
                    anu=self.model.customData['units']
                )
            ])
        }

main_class = RegularStandardAddition 
