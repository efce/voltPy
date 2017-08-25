from manager.method_manager import *
from numpy import polyfit, corrcoef

class RegularStandardAddition2(AnalysisMethod):
    def __init__(self):
        pass

    def __str__(self):
        return "Regular Standard Addition 2"

    def getStep(self, stepNum):
        if ( stepNum == 0 ):
            return MethodStep.selectRange
        else:
            return MethodStep.end

    def processStep(self, stepnum, data):
        pass

    def setModel(self, model):
        pass

    def askAdditionalData(self, cal):
        pass

    def finalize(self, cal):
        data = cal.dataMatrix
        if not data:
            return
        p = polyfit(data['x'], data['y'], 1)
        cal.method = self
        cal.fitEquation = '%f*x+%f' % (p[0],p[1])
        cal.result = p[1]/p[0]
        cal.complete = True
        cal.corrCoeff = corrcoef(data['x'], data['y'])[0,1]
        cal.save()

def newInstance(*args, **kwargs):
    return RegularStandardAddition2(*args, **kwargs)
