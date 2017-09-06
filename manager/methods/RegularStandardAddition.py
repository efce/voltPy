from manager.methodmanager import *
import manager.plotmanager as pm
from numpy import corrcoef
from manager.helpers.fithelpers import calc_normal_equation_fit, calc_sx0
import numpy as np

class RegularStandardAddition(AnalysisMethod):
    steps = ( 
                { 
                    'step': MethodManager.Step.selectRange, 
                    'title': 'Select range',
                    'data': { 
                        'starting': (0,0),
                        'desc': 'Select range containing peak.',
                        }
                },
                {
                    'step': MethodManager.Step.end,
                    'title': 'End',
                    'data': ''
                }
            )
    model = None

    def __init__(self):
        pass

    def __str__(self):
        return "Regular Standard Addition"

    def getStep(self, stepNum):
        if ( stepNum >= len(self.steps) ):
            return None
        return self.steps[stepNum]

    def processStep(self, user, stepNum):
        yvalues = []
        xvalues = []
        selRange = self.model.customData['range1']
        for c in self.model.curveSet.usedCurveData.all():
            startIndex = c.xvalueToIndex(user, selRange[0])
            endIndex = c.xvalueToIndex(user, selRange[1])
            if endIndex < startIndex:
                endIndex,startIndex = startIndex,endIndex
            yvalues.append(max(c.current[startIndex:endIndex])-min(c.current[startIndex:endIndex]))
            from manager.models import AnalyteInCurve
            conc = AnalyteInCurve.objects.filter(curve=c.curve)[0]
            xvalues.append(conc.concentration)

        dm = [
                [ int(b) for b in xvalues ],
                [ int(b) for b in yvalues ]
            ]
        self.model.customData['matrix'] = dm
        self.model.step += 1
        self.model.save()
        return True

    def finalize(self, *args, **kwargs):
        data = self.model.customData['matrix']
        if not data:
            return
        p = calc_normal_equation_fit(data[0], data[1])
        self.model.customData['fitEquation'] = p
        self.model.customData['result'] = p['intercept']/p['slope']
        self.model.customData['resultStdDev'] = calc_sx0(p['slope'],p['intercept'],data[0],data[1])
        self.model.customData['corrCoef'] = corrcoef(data[0], data[1])[0,1]
        self.model.completed = True
        self.model.step = 0
        self.model.save()

    def printInfo(self, user):
        p = pm.PlotManager()
        p.processAnalysis(self.model.owner, self.model.id)
        p.plot_width = 500
        p.plot_height = 500
        scr,div = p.getEmbeded(user, 'analysis', self.model.id)
        return {
                'head': ''.join([p.required_scripts,scr]),
                'body': ''.join([
                            div,
                            'Equation: y={2}*x+{3}<br />Result: {0}, STD: {1}'.format(
                                self.model.customData['result'],
                                self.model.customData['resultStdDev'],
                                self.model.customData['fitEquation']['slope'],
                                self.model.customData['fitEquation']['intercept'])
                            ])
                }

def newInstance(*args, **kwargs):
    return RegularStandardAddition(*args, **kwargs)
