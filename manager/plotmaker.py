from django.db.models import Q
from .models import *
import io
import numpy as np
from bokeh.plotting import figure
from bokeh.embed import components

class PlotMaker:
    plot_width = 850
    plot_height = 700
    required_scripts = '<link href="http://cdn.pydata.org/bokeh/release/bokeh-0.12.6.min.css" rel="stylesheet" type="text/css"> <link href="http://cdn.pydata.org/bokeh/release/bokeh-widgets-0.12.6.min.css" rel="stylesheet" type="text/css"> <script src="http://cdn.pydata.org/bokeh/release/bokeh-0.12.6.min.js"></script> <script src="http://cdn.pydata.org/bokeh/release/bokeh-widgets-0.12.6.min.js"></script> '

    def getEmbeded(self, request, user, plot_type, value_id):
        cbs = []

        if ( plot_type == "File" ):
            curvefile_id = value_id
            cf = CurveFile.objects.get(id=curvefile_id)
            if not cf.canBeReadBy(user):
                raise 3
            cbs = Curve.objects.filter(curveFile=cf, deleted=False)
            p=self.preparePlot(cbs, user)

        elif ( plot_type == "Curves" ):
            ids = value_id.split(",")
            curves_filter_qs = Q()
            for i in ids:
                i = int(i)
                curves_filter_qs = curves_filter_qs | Q(id=i)

            cbs = Curve.objects.filter(curves_filter_qs)
            for c in cbs:
                if not c.canBeReadBy(user):
                    raise 3
            p=self.preparePlot(cbs, user)

        elif ( plot_type == "Calibration"):
            cal = Calibration.objects.get(id=value_id)
            if not cal.canBeReadBy(user):
                raise 3
            p=self.prepareCalibration(cal)

        else:
            return

        return components(p) #script, div = components(p)

    def prepareCalibration(self, cal):
        p = figure(
                title=None, 
                x_axis_label='concentration',
                y_axis_label='i / µA',
                height=self.plot_height-10,
                width=self.plot_width-20)

        if not cal.complete:
            return p

        p.circle(cal.dataMatrix['x'], cal.dataMatrix['y'], size=5, color="navy")
        x=max(cal.dataMatrix['x'])
        print(cal.fitEquation)
        y=eval(cal.fitEquation) #should result set y if not the equation is wrong
        if y:
            vx = []
            vx.append(-cal.result)
            vx.append(max(cal.dataMatrix['x']))
            vy = []
            vy.append(0)
            vy.append(y)
            p.line(vx,vy, line_width=2, color="red")
        else:
            return
        return p

    def preparePlot(self, cbs, user):
        # create a new plot with a title and axis labels

        try:
            onxs = OnXAxis.objects.get(user=user)
            onx = onxs.selected
        except:
            onxs = OnXAxis(selected='P',user=user)
            onxs.save()
            onx = onxs.selected

        p = figure(
                title=None, 
                x_axis_label=dict(OnXAxis.AVAILABLE)[onx],
                y_axis_label='i / µA',
                height=self.plot_height-10,
                width=self.plot_width-20)

        if onx == 'S':
            for cb in cbs:
                cvs = CurveData.objects.filter(curve=cb)
                for cv in cvs:
                    rangepb =range(1,len(cv.probingData)+1 )
                    p.line(rangepb, cv.probingData, line_width=2)

        elif onx == 'T':
            for cb in cbs:
                cvs = CurveData.objects.filter(curve=cb)
                for cv in cvs:
                    p.line(cv.time, cv.current, line_width=2)

        else:
            for cb in cbs:
                cvs = CurveData.objects.filter(curve=cb)
                for cv in cvs:
                    p.line(cv.potential, cv.current, line_width=2)

        return p


    def getPage(self, request, user_id, plot_type, value_id):
        scr,div = self.getEmbeded(request, user_id, plot_type, value_id)
        strr = "<html><head>" + self.required_scripts + scr + "</head><body>" + div + "</body></html>"        
        return strr
