from manager.method_manager import *
from numpy import polyfit, corrcoef
import json

class SlopeStandardAdditionAnalysis(AnalysisMethod):
    steps = ( 
                { 
                    'step': MethodManager.Step.selectPoint, 
                    'title': 'Select peak',
                    'data': { 
                        'starting': 0,
                        'desc': 'Enter approx. X value of peak of interest.',
                        }
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
        return "Slope Standard Addition Analysis"

    def getStep(self, stepNum):
        if ( stepNum >= len(self.steps) ):
            return None
        return self.steps[stepNum]

    def processStep(self, user, stepNum, data):
        print('process step: %i' % stepNum)
        print(data)
        self.model.paraters = data
        self.model.step += 1
        self.model.save()
        return True

    def finalize(self, *args, **kwargs):
        #TODO: impletement SSAA
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
    return SlopeStandardAdditionAnalysis(*args, **kwargs)
