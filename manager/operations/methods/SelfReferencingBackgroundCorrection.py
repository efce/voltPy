import numpy as np
from scipy.stats import t
import manager.operations.method as method
from manager.operations.methodsteps.selectanalyte import SelectAnalyte
from manager.operations.methodsteps.selectrange import SelectRange
from manager.operations.methodsteps.tagcurves import TagCurves
from manager.exceptions import VoltPyFailed
import manager.models as mmodels
import manager.helpers.selfReferencingBackgroundCorrection as sbcm
from manager.operations.checks.check_datalenuniform import check_datalenuniform
from manager.operations.checks.check_analyte import check_analyte
from manager.helpers.fithelpers import significant_digit


class SelfReferencingBackgroundCorrection(method.AnalysisMethod):
    can_be_applied = False
    _steps = [
        {
            'class': SelectAnalyte,
            'title': 'Select analyte',
            'desc': """Select analyte.""",
        },
        {
            'class': TagCurves,
            'title': 'Describe sensitivities.',
            'desc': """
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

    checks = (check_datalenuniform, check_analyte)

    description = """
[1] Ciepiela, F., Lisak, G., & Jakubowska, M. (2013). Self-referencing
background correction method for voltammetric investigation of reversible
redox reaction. Electroanalysis, 25(9), 2054–2059.
https://doi.org/10.1002/elan.201300181"""

    @classmethod
    def __str__(cls):
        return "Self-referencing Background Correction"

    def exportableData(self):
        if not self.model.completed:
            raise VoltPyFailed("Data incomplete")
        raise ValueError("Not implemented")

    def apply(self, user, curveSet):
        """
        This procedure cannot be applied to other data.
        """
        raise VoltPyFailed('Self Referencing Background Correction does not support apply function.')

    def finalize(self, user):
        Y = []
        CONC = []
        SENS = []
        RANGES = []
        analyte = self.model.curveSet.analytes.all()[0]
        self.model.customData['analyte'] = analyte.name
        unitsTrans = dict(mmodels.CurveSet.CONC_UNITS)
        self.model.customData['units'] = unitsTrans[self.model.curveSet.analytesConcUnits[analyte.id]]
        if len(set(self.model.stepsData['TagCurves'].keys())) <= 2:
            raise VoltPyFailed('Not enough sensitivities to analyze the data.')
        for name, cds in self.model.stepsData['TagCurves'].items():
            for cid in cds:
                SENS.append(name)
                cd = self.model.curveSet.curvesData.get(id=cid)
                Y.append([])
                Y[-1] = cd.yVector
                CONC.append(self.model.curveSet.analytesConc.get(analyte.id, {}).get(cd.id, 0))
                rng = [
                    cd.xValue2Index(self.model.stepsData['SelectRange'][0]),
                    cd.xValue2Index(self.model.stepsData['SelectRange'][1])
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

    def getFinalContent(self, request, user):
        cs = self.model.curveSet
        unitsTrans = dict(mmodels.CurveSet.CONC_UNITS)
        if self.model.customData['result'] is None:
            info = """
            <p> Could not calculate the final result. Please check your dataset and/or choose diffrent intervals.</p>
            """
        else:
            res = self.model.customData['result']
            n = len(self.model.customData['fitEquations'])
            tval = t.ppf(0.975, n-1)
            ci = self.model.customData['resultStdDev'] * tval / np.sqrt(n-1)
            sdig = significant_digit(ci)
            info = [
                '<p>Analyte: {analyte}<br />Final result: {res}&plusmn;{ci} {unit}</p>'.format(
                    res='%.*f' % (sdig, res),
                    ci='%.*f' % (sdig, ci),
                    analyte=self.model.customData['analyte'],
                    unit=self.model.customData['units']
                ),
                '<p>Equations:<br />',
                '<br />'.join([
                    'Sens "{k}": y = {slope}x + {int}; r<sup>2</sup> = {rsq}'.format(
                        slope=v['fit']['slope'],
                        int=v['fit']['intercept'],
                        rsq=v['rsq'],
                        k=k
                    ) for k, v in self.model.customData['fitEquations'].items()
                ])
            ]
        return {
            'head': '',
            'body': ''.join(info),
        }

main_class = SelfReferencingBackgroundCorrection
