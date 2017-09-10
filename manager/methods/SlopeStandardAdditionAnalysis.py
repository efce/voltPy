from numpy import polyfit, corrcoef
from manager.methodmanager import *
from manager.models import *
import manager.plotmanager as pm

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
            'data': None
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

    def processStep(self, user, stepNum):
        self.model.customData['selectedIndex'] = self.model.curveSet.usedCurveData.all()[0].xvalueToIndex(user, self.model.customData['point'][0])
        self.model.step += 1
        self.model.save
        return True

    def finalize(self, *args, **kwargs):
        from manager.helpers.slopeStandardAdditionAnalysis import slopeStandardAdditionAnalysis
        from manager.helpers.prepareStructForSSAA import prepareStructForSSAA
        from manager.curveea import Param
        peak = self.model.customData.get('selectedIndex', 0)
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
        self.model.customData['matrix'] = [ 
            result['CONC'], 
            [ x for x in result['Slopes'].items() ]
        ]
        self.model.customData['fitEquation'] = result['Fit']
        self.model.customData['result'] = result['Mean']
        self.model.customData['resultStdDev'] = result['STD']
        self.model.customData['corrCoeff'] = result['R']
        self.model.completed = True
        self.model.step = 0
        self.model.save()

    def printInfo(self, request, user):
        p=pm.PlotManager()
        p.plot_width = 500
        p.plot_height = 400
        xvec = self.model.customData['matrix'][0]
        yvec = self.model.customData['matrix'][1]
        for sens,yrow in yvec:
            p.add(
                x=xvec,
                y=yrow,
                isLine=False,
                color='red',
                size=7
            )
        xvec2 = list(xvec)
        xvec2.append(-self.model.customData['result'])
        for k,fe in self.model.customData['fitEquation'].items():
            Y = [ fe['slope']*x+fe['intercept'] for x in xvec2 ]
            p.add(
                x=xvec2,
                y=Y,
                isLine=True,
                color='blue',
                line_width=2
            )

        scripts,div = p.getEmbeded(request, user, 'analysis', self.model.id)
        ret = { 
            'head': ''.join([p.required_scripts,scripts]),
            'body': ''.join([div, '<p>Result: {0}<br />STD: {1}</p>'.format(
                                self.model.customData['result'],
                                self.model.customData['resultStdDev']) 
                            ])
            }
        return ret

def newInstance(*args, **kwargs):
    return SlopeStandardAdditionAnalysis(*args, **kwargs)
