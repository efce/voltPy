from overrides import overrides
import numpy as np
from manager.exceptions import VoltPyFailed
import manager.operations.method as method
from manager.operations.methodsteps.tagcurves import TagCurves


class AverageCurves(method.ProcessingMethod):
    can_be_applied = False
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

    @overrides
    def initialForStep(self, step_num):
        if step_num == 0:
            if len(self.model.curveSet.analytesConc) > 0:
                v = next(iter(self.model.curveSet.analytesConc.values()))
                return v

    def apply(self, user, curveSet):
        """
        This does not support appliyng existing
        """
        raise VoltPyFailed('Average curve does not support apply function.')

    def finalize(self, user):
        cs = self.model.curveSet
        for k, f in self.model.stepsData['TagCurves'].items():
            if (len(f) > 1):
                cid = f[0]
                orgcd = cs.curvesData.get(id=cid)
                newcd = orgcd.getCopy()
                newcdConc = cs.getCurveConcDict(orgcd)
                cs.removeCurve(orgcd)
                yvecs = []
                for cid in f[1:]:
                    cd = self.model.curveSet.curvesData.get(id=cid)
                    yvecs.append(cd.yVector)
                    cs.removeCurve(cd)
                newcd.yVector = np.mean(yvecs, axis=0)
                newcd.save()
                cs.addCurve(newcd, newcdConc)
        cs.save()
        self.model.step = None
        self.model.completed = True
        self.model.save()
        return True

main_class = AverageCurves
