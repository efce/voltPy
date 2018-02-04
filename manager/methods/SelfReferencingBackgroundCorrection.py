import manager.methodmanager as mm
import manager.plotmanager as pm
import manager.models as mmodels
import manager.helpers.selfReferencingBackgroundCorrection as sbcm
import numpy as np
from django import forms

class OperationSelectSensitivities(mm.Operation):
    plot_interaction='none'

    class SelectSens(forms.Form):
        def __init__(self, *args, **kwargs):
            self.model = kwargs.pop('model')
            super(OperationSelectSensitivities.SelectSens, self).__init__(*args, **kwargs)
            for cd in self.model.curveSet.usedCurveData.all():
                self.fields['curve' + str(cd.id)] = forms.CharField(
                    max_length = 16,
                    initial = "",
                    required = True,
                    label = cd.curve.name
                )

    def process(self, user, request, model):
        if ( request.method == 'POST' ):
            form = self.SelectSens(request.POST, model=model)
            if ( form.is_valid() ):
                sens = {}
                for k,v in form.cleaned_data.items():
                    if k[:5] != 'curve':
                        continue
                    s = sens.get(v, [])
                    cdid = int(k[5:])
                    s.append(cdid)
                    sens[v] = s
                if len(sens) < 2:
                    return False
                model.customData['Sens'] = sens
                model.save()
                return True
        return False

    def getHTML(self, user, request, model):
        from django.template.loader import get_template
        form = self.SelectSens(model=model)
        template = get_template('manager/form.html')
        body = template.render({'form': form}, request)
        return { 'head': '', 'body' : body }

class SelfReferencingBackgroundCorrection(mm.AnalysisMethod):
    _operations = [ 
        {
            'class': OperationSelectSensitivities,
            'title': 'Describe sensitivities.',
            'desc': \
"""
Mark with the same alphanumeric string, which curves are
registered with the same sensitivity (the method requires at least
three different).""",
        },
        { 
            'class': mm.OperationSelectRange,
            'title': 'Select range',
            'desc': 'Select range containing peak. WARMING, the data processing can take up to 10 min, please be patient.',
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
        for name,cds in self.model.customData['Sens'].items():
            for cid in cds:
                SENS.append(name)
                cd = self.model.curveSet.usedCurveData.get(id=cid)
                Y.append([])
                Y[-1] = cd.yVector
                cdconc = mmodels.AnalyteInCurve.objects.get(curve=cd.curve)
                CONC.append(cdconc.concentration)
                rng = [
                    cd.xvalueToIndex(user,self.model.customData['range1'][0]),
                    cd.xvalueToIndex(user,self.model.customData['range1'][1])
                ]
                RANGES.append([])
                RANGES[-1] = rng
        result = sbcm.selfReferencingBackgroundCorrection(Y, CONC, SENS, RANGES)
        self.model.customData['result'] = result['__AVG__']
        self.model.customData['resultStdDev'] = result['__STD__']
        self.model.customData['fitEquations'] = {}
        for k, v in result.items():
            if isinstance(k, str):
                if k.startswith('_'):
                    continue
            self.model.customData['fitEquations'][k] = v
        self.model.save()
        return True

    def getInfo(self, request, user):
        info = """
        <p>Final result: {res}</br>Std dev: {stddev}</p>
        <p>Equations:<br>{eqs}</p>
        """.format(
            res=self.model.customData['result'],
            stddev=self.model.customData['resultStdDev'],
            eqs=self.model.customData['fitEquations']
        )
        return {
            'head': '',
            'body': info,
        }

main_class = SelfReferencingBackgroundCorrection
