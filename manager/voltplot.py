import matplotlib.pyplot as plt
from .models import *
import io

class VoltPlot:

    def __init__(self):
        print(plt.get_backend())
        plt.switch_backend("gtk3agg")
        plt.clf()

    def getImageFromFile(self, user_id, curvefile_id):
        plt.figure()
        cf = CurveFile.objects.get(pk=curvefile_id)
        cbs = CurveBasic.objects.filter(curveFile=cf)
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
