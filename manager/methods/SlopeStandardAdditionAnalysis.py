from numpy import polyfit, corrcoef
import manager.methodmanager as mm
import manager.models as models
import manager.plotmanager as pm

class SlopeStandardAdditionAnalysis(mm.AnalysisMethod):
    _operations = ( 
        { 
            'class': mm.OperationSelectPoint,
            'title': 'Select peak',
            'desc': 'Enter approx. X value of peak of interest.',
        },
    )

    @classmethod
    def __str__(cls):
        return "Slope Standard Addition Analysis"

    def finalize(self, user):
        from manager.helpers.slopeStandardAdditionAnalysis import slopeStandardAdditionAnalysis
        from manager.helpers.prepareStructForSSAA import prepareStructForSSAA
        from manager.curveea import Param
        self.model.customData['selectedIndex'] = \
            self.model.curveSet.usedCurveData.all()[0].xvalueToIndex(user, self.model.customData['pointX'])
        peak = self.model.customData.get('selectedIndex', 0)
        X = []
        Conc = []
        tptw = 0
        for cd in self.model.curveSet.usedCurveData.all():
            X.append(cd.probingData)
            a = models.AnalyteInCurve.objects.get(curve=cd.curve)
            Conc.append(a.concentration)
            tptw = cd.curve.params[Param.tp] + cd.curve.params[Param.tw]

        tp = 3
        twvec = self.__chooseTw(tptw)
        if not twvec:
            raise 3
        numM = self.model.curveSet.usedCurveData.all()[0].curve.params[Param.method]
        ctype = 'dp'
        if numM == Param.method_dpv:
            ctype='dp'
        elif numM == Param.method_npv:
            ctype='np'
        elif numM == Param.method_sqw:
            ctype = 'sqw'
        elif numM == Param.method_scv:
            ctype = 'sc'
        else:
            raise TypeError('Method numer %i not supported' % numM)

        prepare = prepareStructForSSAA(X,Conc, tptw, 3,twvec,ctype)
                
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
        self.model.step = None
        self.model.save()

    def getInfo(self, request, user):
        p=pm.PlotManager()
        p.plot_width = 500
        p.plot_height = 400
        xvec = self.model.customData['matrix'][0]
        yvec = self.model.customData['matrix'][1]
        for sens,yrow in yvec:
            p.add(
                x=xvec,
                y=yrow,
                plottype='scatter',
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
                plottype='line',
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

    def __chooseTw(self, tptw):
        if ( tptw < 9 ):
            return None
        elif ( tptw < 20 ):
            return [ tptw-3, tptw-6, tptw-9 ]
        if ( tptw < 40 ):
            return [ tptw-3, tptw-7, tptw-11 ]
        else:
            n = floor(n/12)
            d = floor(sqrt(n))
            return [ tptw-((x*d)-3) for x in range(n) ]

main_class = SlopeStandardAdditionAnalysis
