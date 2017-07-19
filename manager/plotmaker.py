import matplotlib.pyplot as plt
from .models import *
import io

class PlotMaker:

    def __init__(self):
        plt.switch_backend("gtk3agg")
        plt.clf()

    def getImageFromFile(self, request, user_id, curvefile_id):
        plt.figure()
        cf = CurveFile.objects.get(pk=curvefile_id)
        cbs = CurveBasic.objects.filter(curveFile=cf)

        onxs = OnXAxis.objects.get(user=user_id)
        onx = onxs.selected

        if onx == 'S':
            for cb in cbs:
                cvs = CurveVectors.objects.filter(curve=cb)
                for cv in cvs:
                    rangepb =range(1,len(cv.probingData)+1 )
                    plt.plot( rangepb, cv.probingData)

        elif onx == 'T':
            for cb in cbs:
                cvs = CurveVectors.objects.filter(curve=cb)
                for cv in cvs:
                    plt.plot(cv.time, cv.current)

        else:
            for cb in cbs:
                cvs = CurveVectors.objects.filter(curve=cb)
                for cv in cvs:
                    plt.plot(cv.potential, cv.current)

        #TODO: buffer the image in database ?
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.clf()
        buf.seek(0)
        image = buf.read()
        buf.truncate(0)
        buf.close()
        return image
