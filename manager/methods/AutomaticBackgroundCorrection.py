from manager.method_manager import *
from numpy import polyfit, corrcoef
import numpy as np

class AutomaticBackgroundCorrection(AnalysisMethod):
    steps = ( 
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
        return "Automatic Background Correction"

    def getStep(self, stepNum):
        if ( stepNum >= len(self.steps) ):
            return None
        return self.steps[stepNum]

    def processStep(self, user, stepNum, data):
        pass

    def finalize(self, *args, **kwargs):
        pass



    def printInfo(self):
        import manager.plotmaker as pm
        p = pm.PlotMaker()
        p.processAnalysis(self.model.owner, self.model.id)
        p.plot_width = 500
        p.plot_height = 500
        scr,div = p.getEmbeded()
        return {
                'head': ''.join([p.required_scripts,scr]),
                'body': ''.join([
                            div,
                            'Equation: y={2}*x+{3}<br />Result: {0}, STD: {1}'.format(
                                self.model.result,
                                self.model.resultStdDev,
                                self.model.fitEquation['slope'],
                                self.model.fitEquation['intercept'])
                            ])
                }

def newInstance(*args, **kwargs):
    return AutomaticBackgroundCorrection(*args, **kwargs)
