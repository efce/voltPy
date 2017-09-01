from manager.method_manager import *
from numpy import polyfit, corrcoef
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

    def processStep(self, user, stepNum, data):
        print('process step: %i' % stepNum)
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
        self.model.fitEquation = {'slope': p[0], 'intercept': p[1] }
        self.model.result = p[1]/p[0]
        self.model.resultStdDev = self.__Sx0(p[0],p[1],data[0],data[1])
        self.model.corrCoef = corrcoef(data[0], data[1])[0,1]
        self.model.completed = True
        self.model.step = 0
        self.model.save()


    def __Sx0(self, slope, intercept, xvec, yvec):
        yevec = [ slope*x+intercept for x in xvec ]
        xmean = np.average(xvec)
        sr = np.sqrt(1/(len(xvec)-2) * np.sum((yi-ye)**2 for yi,ye in zip(yvec, yevec)))
        sx0 = (sr/slope) * np.sqrt(1 + 1/len(xvec) + (yvec[0]-np.average(yvec))**2/(slope**2*np.sum((xi-xmean)**2 for xi in xvec)))
        return sx0

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
    return RegularStandardAddition(*args, **kwargs)
