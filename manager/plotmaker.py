from django.db.models import Q
from .models import *
import io
import numpy as np
import json 
from bokeh.plotting import figure, ColumnDataSource
from bokeh.embed import components
from bokeh.models.callbacks import CustomJS
from bokeh.models import Span
from bokeh.layouts import widgetbox, column
from bokeh.models.widgets import RadioButtonGroup

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
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
    <script type="text/javascript">
    function processData (plot,lineData,cursors,jdata) {
        var data = JSON.parse(jdata);
        switch (data.command) {
        case 'reload':
            location.reload();
            break;
        case 'setCursor':
            cursors[data.number].location = parseFloat(data.x);
            cursors[data.number].line_alpha = 1;
            show(cursors[data.number]);
            break;
        case 'setLineData':
            var xv = lineData.data['x'];
            var yv = lineData.data['y'];
            for (i = 0; i < data.x.length; i++) {
                xv[i] = data.x[i];
                yv[i] = data.y[i];
            }
            xv.length = data.x.length;
            yv.length = data.x.length;
            lineData.trigger('change');
            break;
        case 'removeLine':
            lineData.x = [];
            lineData.y = [];
            lineData.trigger('change');
            break;
        case 'removeCursor':
            cursors[data.number].line_alpha = 0;
            show(cursors[data.number]);
            break;
        case 'changeColor':
        default:
            alert('Not implemented...');
        }
    }
    </script>
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
                cvs = CurveData.objects.filter(curve=cb, processing=None)
                for cv in cvs:
                    self._line.append(
                            dict(
                                x=range(1, len(cv.probingData)+1),
                                y=cv.probingData
                            )
                        )

        elif onx == 'T':
            for cb in curves:
                cvs = CurveData.objects.filter(curve=cb, processing=None)
                for cv in cvs:
                    self._line.append(
                            dict(
                                x=cv.time,
                                y=cv.current
                            )
                        )

        else:
            for cb in curves:
                cvs = CurveData.objects.filter(curve=cb, processing=None)
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
        if not analysis.completed:
            return
        self.xlabel = 'concentration'
        self.ylabel = 'i / µA'
        # prepare data points
        self.processXY( 
                    analysis.dataMatrix[0], 
                    analysis.dataMatrix[1],
                    False
                )
        #prepare calibration line
        xs = analysis.dataMatrix[0]
        xs.append(-analysis.result)
        vx= [ min(xs), max(xs) ] # x variable is used by the fitEquation
        FofX = lambda xo: analysis.fitEquation['slope'] * xo + analysis.fitEquation['intercept']
        vy = [FofX(xi) for xi in vx ]
        self.processXY(vx,vy,True)


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


    def _prepareFigure(self, user):
        p = figure(
                title=self.title, 
                x_axis_label=self.xlabel,
                y_axis_label=self.ylabel,
                height=self.plot_height-10,
                width=self.plot_width-20
            )
        labels = []
        onx = OnXAxis.objects.get(user=user).selected
        for k,l in dict(OnXAxis.AVAILABLE).items():
            labels.append(l)
        active = -1
        for i,k in enumerate(dict(OnXAxis.AVAILABLE).keys()):
            if k==onx:
                active = i

        radio_button_group = RadioButtonGroup(
                labels=labels, 
                active=active,
                callback=CustomJS(args={}, code=
                    """
                    var act = cb_obj.active;
                    alert('not implemented: '+ act);
                    """)
                )
        w=widgetbox(radio_button_group)
        layout = column([ p, w ])
        return layout, p

    def plotInteract(self, intercation, data):
        if ( interaction == 'add' ):
            pass
        elif ( interaction == 'remove' ):
            pass
        elif ( interaction == 'change' ):
            pass
        elif ( interaction == 'reloadPage' ):
            pass



    def getEmbeded(self, user_id, plot_type, vid):
        try:
            user=User.objects.get(id=user_id)
        except:
            user=None
        layout, p = self._prepareFigure(user)

        for l in self._line:
            p.line(l['x'], l['y'], color="blue", line_width=2)

        for s in self._scatter:
            p.scatter(s['x'], s['y'], color="red", size=8)

        srcEmpty = ColumnDataSource(data = dict( x=[], y=[]))
        p.line(x='x',y='y',source=srcEmpty, color='red', line_dash='dashed')

        cursors = []
        for i in range(4):
            C= Span(location=0,
                        dimension='height', 
                        line_color='green',
                        line_dash='dashed', 
                        line_width=2,
                        line_alpha=0
                       )
            p.add_layout(C)
            cursors.append(C)

        args = dict(
                lineSrc=srcEmpty,
                plot=p,
                cursor1=cursors[0],
                cursor2=cursors[1],
                cursor3=cursors[2],
                cursor4=cursors[3]
                )
        #        callback = CustomJS(args=args, code=
        #        "var type = '" + plot_type + "'; var vid = '" + vid + "'; var uid = '" +
        #        str(user_id) + "';" + """
        #        var cursors = [cursor1, cursor2, cursor3, cursor4];
        #        var x_data = cb_obj.x; // current mouse x position in plot coordinates
        #        var y_data = cb_obj.y; // current mouse y position in plot coordinates
        #        console.log("(x,y)=" + x_data+","+y_data); //monitors values in Javascript console
        #        var geturl = window.location.href + "?query=json&plot_type=" + type +"&vid=" + vid + "&x=" + x_data +"&y=" + y_data;
        #        $.get( geturl, function(data, status){
        #                alert("Data: " + data);
        #                if (status == 'success')
        #                    processData(plot,lineSrc,cursors,data);
        #            });
        #        """)
        #
        #        p.js_on_event('tap', callback)
        return components(layout) 


    def getPage(self):
        scr,div = self.getEmbeded()
        strr = "<html><head>" + self.required_scripts+ "</head><body>"  + scr + div + "</body></html>"        
        return strr

