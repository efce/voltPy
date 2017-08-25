from manager.method_manager import *
from numpy import polyfit, corrcoef

class RegularStandardAddition(AnalysisMethod):
    steps = ( 
                { 
                    'step': MethodManager.Step.selectRange, 
                    'title': 'Select range',
                    'desc': 'Select range containing peak.'
                },
                {
                    'step': MethodManager.Step.end,
                    'title': 'End',
                    'desc': 'No more steps.'
                }
            )
    analysis = None

    def __init__(self):
        pass

    def __str__(self):
        return "Regular Standard Addition"

    def setModel(self, model):
        self.analysis = model

    def getStep(self, stepNum):
        if ( stepNum >= len(self.steps) ):
            return None
        return self.steps[stepNum]

    def processStep(self, stepNum, data):
        print('process step: %i' % stepNum)
        print(data)
        self.analysis.paraters = data
        yvalues = []
        xvalues = []
        for c in self.analysis.curveSet.usedCurveData.all():
            #TODO: co na X
            diffStart = [ abs(x-data[0]) for x in c.potential ]
            startIndex, startValue = min(enumerate(diffStart), key=lambda p: p[1])
            diffEnd = [ abs(x-data[1]) for x in c.potential ]
            endIndex, endValue = min(enumerate(diffEnd), key=lambda p: p[1])
            if endIndex < startIndex:
                endIndex,startIndex = startIndex,endIndex
            yvalues.append(max(c.current[startIndex:endIndex])-min(c.current[startIndex:endIndex]))
            from manager.models import AnalyteInCurve
            conc = AnalyteInCurve.objects.filter(curve=c.curve)[0]
            xvalues.append(conc.concentration)

        dm = {
                'x': xvalues,
                'y': yvalues
            }
        self.analysis.dataMatrix = dm
        self.analysis.step += 1
        self.analysis.save()
        return True

    def finalize(self, *args, **kwargs):
        data = self.analysis.dataMatrix
        if not data:
            return
        p = polyfit(data['x'], data['y'], 1)
        self.analysis.fitEquation = '%f*x+%f' % (p[0],p[1])
        self.analysis.result = p[1]/p[0]
        self.analysis.corrCoeff = corrcoef(data['x'], data['y'])[0,1]
        self.analysis.complete = True
        self.analysis.step = MethodManager.Step.end
        self.analysis.save()

def newInstance(*args, **kwargs):
    return RegularStandardAddition(*args, **kwargs)
