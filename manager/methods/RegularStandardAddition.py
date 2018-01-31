import manager.methodmanager as mm
import manager.plotmanager as pm
from numpy import corrcoef
from manager.helpers.fithelpers import calc_normal_equation_fit, calc_sx0
import numpy as np

class RegularStandardAddition(mm.AnalysisMethod):
    _operations = [
        { 
            'class': mm.OperationSelectRange,
            'title': 'Select range',
            'desc': 'Select range containing peak.',
        },
    ]
    description = """
    This is standard addition method, where the height of the signal is
    calculated as a difference between max and min signal in the given range.
    """

    @classmethod
    def __str__(cls):
        return "Regular Standard Addition"

    def finalize(self, user):
        xvalues = []
        yvalues = []
        selRange = self.model.customData['range1']
        for c in self.model.curveSet.usedCurveData.all():
            startIndex = c.xvalueToIndex(user, selRange[0])
            endIndex = c.xvalueToIndex(user, selRange[1])
            if endIndex < startIndex:
                endIndex,startIndex = startIndex,endIndex
            yvalues.append(max(c.yVector[startIndex:endIndex])-min(c.yVector[startIndex:endIndex]))
            from manager.models import AnalyteInCurve
            conc = AnalyteInCurve.objects.filter(curve=c.curve)[0]
            xvalues.append(conc.concentration)

        data = [
            [ float(b) for b in xvalues ],
            [ float(b) for b in yvalues ]
        ]
        self.model.customData['matrix'] = data
        p = calc_normal_equation_fit(data[0], data[1])
        self.model.customData['fitEquation'] = p
        self.model.customData['result'] = p['intercept']/p['slope']
        self.model.customData['resultStdDev'] = calc_sx0(p['slope'],p['intercept'],data[0],data[1])
        self.model.customData['corrCoef'] = corrcoef(data[0], data[1])[0,1]
        self.model.completed = True
        self.model.step = 0
        self.model.save()

    def getInfo(self, request, user):
        p = pm.PlotManager()
        data = p.analysisHelper(self.model.owner, self.model.id)
        for d in data:
            p.add(**d)
        p.plot_width = 500
        p.plot_height = 500
        scr,div = p.getEmbeded(request, user, 'analysis', self.model.id)
        return {
            'head': scr,
            'body': ''.join([
                                div,
                                'Equation: y={2}*x+{3}<br />Result: {0}, STD: {1}'.format(
                                    self.model.customData['result'],
                                    self.model.customData['resultStdDev'],
                                    self.model.customData['fitEquation']['slope'],
                                    self.model.customData['fitEquation']['intercept']
                                )
                            ])
        }

main_class = RegularStandardAddition 
