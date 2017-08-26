from manager.method_manager import *
from numpy import polyfit, corrcoef
import json

class RegularStandardAddition(AnalysisMethod):
    steps = ( 
                { 
                    'step': MethodManager.Step.selectRange, 
                    'title': 'Select range',
                    'desc': 'Select range containing peak.',
                    'data': { 'starting': (0,0) }
                },
                {
                    'step': MethodManager.Step.end,
                    'title': 'End',
                    'desc': 'No more steps.',
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

    def processStep(self, user, stepNum, data):
        print('process step: %i' % stepNum)
        print(data)
        self.model.paraters = data
        yvalues = []
        xvalues = []
        selRange = data['range1']
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
        self.model.dataMatrix = dm
        self.model.step += 1
        self.model.save()
        return True

    def finalize(self, *args, **kwargs):
        data = self.model.dataMatrix
        if not data:
            return
        p = polyfit(data[0], data[1], 1)
        self.model.fitEquation = '%f*x+%f' % (p[0],p[1])
        self.model.result = p[1]/p[0]
        self.model.corrCoeff = corrcoef(data[0], data[1])[0,1]
        self.model.completed = True
        self.model.step = 0
        self.model.save()

def newInstance(*args, **kwargs):
    return RegularStandardAddition(*args, **kwargs)
