import numpy as np
import django.forms as forms
from django.utils import timezone
import manager.operations.methodmanager as mm
from manager.operations.methodsteps.tagcurves import TagCurves

class AverageCurves(mm.ProcessingMethod):
    _steps = [ 
        {
            'class': TagCurves,
            'title': 'Averaging',
            'desc': 'Tag the curves you want to average with the same alphanumeric value.',
        },
    ]
    description = """
This is simple averaging method which allow to calculate the average from
given number of plots.
    """

    @classmethod
    def __str__(cls):
        return "Average Curves"

    def finalize(self, user):
        for k,f in self.model.stepsData['TagCurves'].items():
            if ( len(f) > 1 ):
                cid = f[0]
                orgcd = self.model.curveSet.curvesData.get(id=cid)
                newcd = orgcd.getCopy()
                self.model.curveSet.curvesData.remove(orgcd)
                cnt = 1
                yvecs = []
                for cid in f[1:]:
                    cd = self.model.curveSet.curvesData.get(id=cid)
                    yvecs.append(cd.yVector)
                    self.model.curveSet.curvesData.remove(cd)
                newcd.yVector = np.mean(yvecs, axis=0).tolist()
                newcd.save()
                #TODO: move removal to model ?:
                for a in self.model.curveSet.analytes.all():
                    self.model.curveSet.analytesConc[a.id] = self.model.curveSet.analytesConc.get(a.id,{})
                    self.model.curveSet.analytesConc[a.id][newcd.id] = \
                        self.model.curveSet.analytesConc[a.id].get(orgcd.id, 0)
                for cid in f[1:]:
                    for a in self.model.curveSet.analytes.all():
                        self.model.curveSet.analytesConc[a.id].pop(cid, 0)

                self.model.curveSet.curvesData.add(newcd)
                self.model.curveSet.save()
        self.model.step = None
        self.model.completed = True
        self.model.save()
        return True

    def getInfo(self, request, user):
        return {
            'head': '',
            'body': ''
        }

main_class = AverageCurves
