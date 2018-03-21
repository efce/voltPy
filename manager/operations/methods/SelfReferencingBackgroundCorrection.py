import manager.operations.method as method
from manager.operations.methodsteps.selectanalyte import SelectAnalyte
from manager.operations.methodsteps.selectrange import SelectRange
from manager.operations.methodsteps.tagcurves import TagCurves
import manager.plotmanager as pm
import manager.models as mmodels
import manager.helpers.selfReferencingBackgroundCorrection as sbcm
import numpy as np
from django import forms

class SelfReferencingBackgroundCorrection(method.AnalysisMethod):
    _steps = [ 
        { 
            'class': SelectAnalyte,
            'title': 'Select analyte',
            'desc': """Select analyte.""",
        },
        {
            'class': TagCurves,
            'title': 'Describe sensitivities.',
            'desc': \
"""
Tag curves registered with the same sensitivity
with the same alphanumeric string (the method 
requires at least three different).
""",
        },
        { 
            'class': SelectRange,
            'title': 'Select range',
            'desc': """
Select range containing peak and press Forward, or press Back to change the selection.
<br />WARNING, the data processing can take up to 5 min, please be patient.
""",
        },
    ]
    description = \
"""
[1] Ciepiela, F., Lisak, G., & Jakubowska, M. (2013). Self-referencing
background correction method for voltammetric investigation of reversible
redox reaction. Electroanalysis, 25(9), 2054–2059.
https://doi.org/10.1002/elan.201300181"""

    @classmethod
    def __str__(cls):
        return "Self-referencing Background Correction"

    def finalize(self, user):
        Y = []
        CONC = []
        SENS = []
        RANGES = []
        analyte = self.model.curveSet.analytes.all()[0]
        self.model.customData['analyte'] = analyte.name
        unitsTrans = dict(mmodels.CurveSet.CONC_UNITS)
        self.model.customData['units'] = unitsTrans[self.model.curveSet.analytesConcUnits[analyte.id]]
        for name,cds in self.model.stepsData['TagCurves'].items():
            for cid in cds:
                SENS.append(name)
                cd = self.model.curveSet.curvesData.get(id=cid)
                Y.append([])
                Y[-1] = cd.yVector
                CONC.append(self.model.curveSet.analytesConc.get(analyte.id,{}).get(cd.id,0))
                rng = [
                    cd.xvalueToIndex(user,self.model.stepsData['SelectRange'][0]),
                    cd.xvalueToIndex(user,self.model.stepsData['SelectRange'][1])
                ]
                RANGES.append([])
                RANGES[-1] = rng
        result = sbcm.selfReferencingBackgroundCorrection(Y, CONC, SENS, RANGES)
        self.model.customData['result'] = result.get('__AVG__', None)
        self.model.customData['resultStdDev'] = result.get('__STD__', None)
        self.model.customData['fitEquations'] = {}
        for k, v in result.items():
            if isinstance(k, str):
                if k.startswith('_'):
                    continue
            self.model.customData['fitEquations'][k] = v
        self.model.save()
        return True

    def getInfo(self, request, user):
        cs = self.model.curveSet
        unitsTrans = dict(mmodels.CurveSet.CONC_UNITS)
        if self.model.customData['result'] is None:
            info = """
            <p> Could not calculate the final result. Please check your dataset and/or choose diffrent intervals.</p>
            """

        else:
            info = """
            <p>Analyte: {analyte}<br />Final result: {res} {unit}<br />Std dev: {stddev} {unit}</p>
            <p>Equations:<br>{eqs}</p>
            """.format(
                res=self.model.customData['result'],
                stddev=self.model.customData['resultStdDev'],
                eqs=self.model.customData['fitEquations'],
                analyte=self.model.customData['analyte'],
                unit=self.model.customData['units']
            )
        return {
            'head': '',
            'body': info,
        }

main_class = SelfReferencingBackgroundCorrection
