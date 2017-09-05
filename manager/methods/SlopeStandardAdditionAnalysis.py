from numpy import polyfit, corrcoef
from manager.methodmanager import *
from manager.models import *
import manager.plotmaker as pm

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
        data['selectedIndex'] = self.model.curveSet.usedCurveData.all()[0].xvalueToIndex(user, data['point'])
        print('process step: %i' % stepNum)
        print(data)
        self.model.params = data
        self.model.step += 1
        self.model.save
        return True

    def finalize(self, *args, **kwargs):
        from manager.helpers.slopeStandardAdditionAnalysis import slopeStandardAdditionAnalysis
        from manager.helpers.prepareStructForSSAA import prepareStructForSSAA
        from manager.curveea import Param
        peak = self.model.params.get('selectedIndex', 0)
        X = []
        Conc = []
        tptw = 0
        for cd in self.model.curveSet.usedCurveData.all():
            X.append(cd.probingData)
            a = AnalyteInCurve.objects.get(curve=cd.curve)
            Conc.append(a.concentration)
            tptw = cd.curve.params[Param.tp] + cd.curve.params[Param.tw]

        #TODO: proper selection of values
        prepare = prepareStructForSSAA(X,Conc, tptw, 3,[3,7,13],'dp') 
        result = slopeStandardAdditionAnalysis(prepare, peak, {'forceSamePoints': True})
        self.model.dataMatrix = [ 
                result['CONC'], 
                [ x for x in result['Slopes'].items() ]
            ]
        self.model.fitEquation = result['Fit']
        self.model.result = result['Mean']
        self.model.resultStdDev = result['STD']
        self.model.corrCoeff = result['R']
        self.model.completed = True
        self.model.step = 0
        self.model.save()

    def printInfo(self):
        p=pm.PlotMaker()
        p.plot_width = 500
        p.plot_height = 400
        xvec = self.model.dataMatrix[0]
        yvec = self.model.dataMatrix[1]
        for sens,yrow in yvec:
            p.processXY(
                    xvec,
                    yrow,
                    False)
        xvec2 = list(xvec)
        xvec2.append(-self.model.result)
        for k,fe in self.model.fitEquation.items():
            Y = [ fe['slope']*x+fe['intercept'] for x in xvec2 ]
            p.processXY(xvec2,Y,True)

        scripts,div = p.getEmbeded()
        ret = { 
            'head': ''.join([p.required_scripts,scripts]),
            'body': ''.join([div, '<p>Result: {0}<br />STD: {1}</p>'.format(self.model.result, self.model.resultStdDev) ])
            }

        return ret

def newInstance(*args, **kwargs):
    return SlopeStandardAdditionAnalysis(*args, **kwargs)
