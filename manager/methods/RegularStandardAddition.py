from manager.method_manager import *
from numpy import polyfit, corrcoef

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
        self.model.fitEquation = '%f*x+%f' % (p[0],p[1])
        self.model.result = p[1]/p[0]
        self.model.corrCoef = corrcoef(data[0], data[1])[0,1]
        self.model.completed = True
        self.model.step = 0
        self.model.save()

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
                            'Equation: y={2}<br />Result: {0}, STD: {1}'.format(
                                self.model.result,
                                self.model.resultStdDev,
                                self.model.fitEquation)
                            ])
                }

def newInstance(*args, **kwargs):
    return RegularStandardAddition(*args, **kwargs)
