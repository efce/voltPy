from manager.method_manager import *
from numpy import polyfit, corrcoef

class RegularStandardAddition(AnalysisMethod):
    steps = ( 
                MethodManager.Step.selectRange, 
                MethodManager.Step.end
            )
    analysis = None

    def __init__(self):
        pass

    def __str__(self):
        return "Regular Standard Addition"

    def setModel(self, model):
        self.analysis = model

    def nextStep(self, stepNum):
        return self.steps[stepNum]

    def processStep(self, stepNum, data):
        pass

    def finalize(self, *args, **kwargs):
        data = self.analysis.dataMatrix
        if not data:
            return
        p = polyfit(data['x'], data['y'], 1)
        self.analysis.method = "normal"
        self.analysis.fitEquation = '%f*x+%f' % (p[0],p[1])
        self.analysis.result = p[1]/p[0]
        self.analysis.complete = True
        self.analysis.corrCoeff = corrcoef(data['x'], data['y'])[0,1]
        self.analysis.save()

def newInstance(*args, **kwargs):
    return RegularStandardAddition(*args, **kwargs)
