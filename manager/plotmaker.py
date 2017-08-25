from django.db.models import Q
from .models import *
import io
import numpy as np
from bokeh.plotting import figure
from bokeh.embed import components

class PlotMaker:
    _scatter = [] # list to be plotted of dictionaries containing 'x' and 'y' vectors
    _line = []    # list to be plotted of dictionaries containing 'x' and 'y' vectors
    title = None
    xlabel = "x"
    ylabel = "y"
    plot_width = 850
    plot_height = 700
    required_scripts = """
    <link href="http://cdn.pydata.org/bokeh/release/bokeh-0.12.6.min.css" rel="stylesheet" type="text/css"> 
    <link href="http://cdn.pydata.org/bokeh/release/bokeh-widgets-0.12.6.min.css" rel="stylesheet" type="text/css"> 
    <script src="http://cdn.pydata.org/bokeh/release/bokeh-0.12.6.min.js"></script> 
    <script src="http://cdn.pydata.org/bokeh/release/bokeh-widgets-0.12.6.min.js"></script>
    """
    def __init__(self):
        self._line = []
        self._scatter = []
        self.xlabel = "x"
        self.ylabel = "y"
        self.plot_width = 850
        self.plot_height = 700
    

    def processFile(self, user, value_id):
        curvefile_id = value_id
        cf = CurveFile.objects.get(id=curvefile_id)
        if not cf.canBeReadBy(user):
            raise 3
        cbs = Curve.objects.filter(curveFile=cf, deleted=False)
        self._processCurveArray(user, cbs)
    

    def processCurves(self, user, curve_ids_comma_separated):
        cids = curve_ids_comma_separated.split(",")
        curves_filter_qs = Q()
        for i in cids:
            i = int(i)
            curves_filter_qs = curves_filter_qs | Q(id=i)
        cbs = Curve.objects.filter(curves_filter_qs)
        for c in cbs:
            if not c.canBeReadBy(user):
                raise 3
        self._processCurveArray(user, cbs)


    def processCurveSet(self, user, curveset_id):
        try:
            onxs = OnXAxis.objects.get(user=user)
            onx = onxs.selected
        except:
            onxs = OnXAxis(selected='P',user=user)
            onxs.save()
            onx = onxs.selected

        self.xlabel = self._generateXLabel(onx)
        self.ylabel = 'i / µA'
        cs = CurveSet.objects.get(id=curveset_id)

        if onx == 'S':
            for cv in cs.usedCurveData.all():
                self._line.append(
                        dict(
                            x=range(1, len(cv.probingData)+1),
                            y=cv.probingData
                        )
                    )

        elif onx == 'T':
            for cv in cs.usedCurveData.all():
                self._line.append(
                        dict(
                            x=cv.time,
                            y=cv.current
                        )
                    )

        else:
            for cv in cs.usedCurveData.all():
                self._line.append(
                        dict(
                            x=cv.potential,
                            y=cv.current
                        )
                    )


    def _processCurveArray(self, user, curves):
        try:
            onxs = OnXAxis.objects.get(user=user)
            onx = onxs.selected
        except:
            onxs = OnXAxis(selected='P',user=user)
            onxs.save()
            onx = onxs.selected

        self.xlabel = self._generateXLabel(onx)
        self.ylabel = 'i / µA'

        if onx == 'S':
            for cb in curves:
                cvs = CurveData.objects.filter(curve=cb)
                for cv in cvs:
                    self._line.append(
                            dict(
                                x=range(1, len(cv.probingData)+1),
                                y=cv.probingData
                            )
                        )

        elif onx == 'T':
            for cb in curves:
                cvs = CurveData.objects.filter(curve=cb)
                for cv in cvs:
                    self._line.append(
                            dict(
                                x=cv.time,
                                y=cv.current
                            )
                        )

        else:
            for cb in curves:
                cvs = CurveData.objects.filter(curve=cb)
                for cv in cvs:
                    self._line.append(
                            dict(
                                x=cv.potential,
                                y=cv.current
                            )
                        )


    def _generateXLabel(self, onx):
        if ( onx == 'S' ):
            return "Sample no."
        elif ( onx == 'T' ):
            return "t / ms"
        else:
            return "E / mV"


    def processAnalysis(self, user, value_id):
        analysis = Analysis.objects.get(id=value_id)
        if not analysis.canBeReadBy(user):
            raise 3
        if not analysis.complete:
            return
        self.xlabel = 'concentration'
        self.ylabel = 'i / µA'
        # prepare data points
        self._scatter.append(
                dict( 
                    x=analysis.dataMatrix['x'], 
                    y=analysis.dataMatrix['y'] 
                )
            )

        #prepare calibration line
        xs = list(analysis.dataMatrix['x'])
        xs.append(-analysis.result)
        x = min(xs) # x variable is used by the fitEquation
        y1=eval(analysis.fitEquation) #should set y if not the equation is wrong
        x1=x

        x = max(xs)
        y2=eval(analysis.fitEquation) #should set y if not the equation is wrong
        x2=x
        if y1:
            vx = []
            vx.append(x1)
            vx.append(x2)
            vy = []
            vy.append(y1)
            vy.append(y2)
            self._line.append( 
                    dict( 
                        x=vx, 
                        y=vy 
                    )
                )



    def processXY(self, x, y, line=True):
        if line:
            self._line.append(
                    dict(
                        x=x,
                        y=y
                    )
                )
        else:
            self._scatter.append(
                    dict(
                        x=x,
                        y=y
                    )
                )


    def _prepareFigure(self):
        p = figure(
                title=self.title, 
                x_axis_label=self.xlabel,
                y_axis_label=self.ylabel,
                height=self.plot_height-10,
                width=self.plot_width-20
            )
        return p


    def getEmbeded(self):
        p = self._prepareFigure()

        for l in self._line:
            p.line(l['x'], l['y'], color="blue", line_width=2)

        for s in self._scatter:
            p.scatter(s['x'], s['y'], color="red", size=8)

        return components(p) 


    def getPage(self):
        scr,div = self.getEmbeded()
        strr = "<html><head>" + self.required_scripts + scr + "</head><body>" + div + "</body></html>"        
        return strr

