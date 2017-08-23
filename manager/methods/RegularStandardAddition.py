from manager.method_manager import *
from numpy import polyfit, corrcoef

class RegularStandardAddition(AnalysisMethod):
    def __init__(self):
        pass

    def __str__(self):
        return "Regular Standard Addition"

    def nextStep(self, stepNum):
        if ( stepNum == 0 ):
            return MethodStep.selectRange
        else:
            return MethodStep.end

    def askAdditionalData(self, cal):
        pass

    def process(self, cal):
        data = cal.dataMatrix
        if not data:
            return
        p = polyfit(data['x'], data['y'], 1)
        cal.method = "normal"
        cal.fitEquation = '%f*x+%f' % (p[0],p[1])
        cal.result = p[1]/p[0]
        cal.complete = True
        cal.corrCoeff = corrcoef(data['x'], data['y'])[0,1]
        cal.save()

def newInstance(*args, **kwargs):
    return RegularStandardAddition(*args, **kwargs)
