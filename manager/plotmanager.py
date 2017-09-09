from django.db.models import Q
from .models import *
import io
import numpy as np
import json 
import django
from bokeh.plotting import figure, ColumnDataSource
from bokeh.embed import components
from bokeh.models.callbacks import CustomJS
from bokeh.models import Span
from bokeh.layouts import widgetbox, column
from bokeh.models.widgets import RadioButtonGroup

class PlotManager:
    include_x_switch = False
    title = ''
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
        case 'redirect':
            location = data.location;
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
        self.__line = []
        self.__scatter = []
        self.xlabel = "x"
        self.ylabel = "y"
        self.plot_width = 850
        self.plot_height = 700
        self.p = figure(
            title=self.title, 
            x_axis_label=self.xlabel,
            y_axis_label=self.ylabel,
            height=self.plot_height-10,
            width=self.plot_width-20
        )
    

    def fileHelper(self, user, value_id):
        curvefile_id = value_id
        cf = CurveFile.objects.get(id=curvefile_id)
        if not cf.canBeReadBy(user):
            raise 3
        cbs = Curve.objects.filter(curveFile=cf, deleted=False)
        return self._processCurveArray(user, cbs)
    

    def curvesHelper(self, user, curve_ids_comma_separated):
        cids = curve_ids_comma_separated.split(",")
        curves_filter_qs = Q()
        for i in cids:
            i = int(i)
            curves_filter_qs = curves_filter_qs | Q(id=i)
        cbs = Curve.objects.filter(curves_filter_qs)
        for c in cbs:
            if not c.canBeReadBy(user):
                raise 3
        return self._processCurveArray(user, cbs)


    def curveSetHelper(self, user, curveset_id):
        try:
            onxs = OnXAxis.objects.get(user=user)
            onx = onxs.selected
        except:
            onxs = OnXAxis(selected='P',user=user)
            onxs.save()
            onx = onxs.selected
        cs = CurveSet.objects.get(id=curveset_id)
        ret = []

        if onx == 'S':
            for cv in cs.usedCurveData.all():
                ret.append(
                        dict(
                            x=range(1, len(cv.probingData)+1),
                            y=cv.probingData,
                            isLine=True,
                            name = '',
                            color='blue',
                        )
                    )

        elif onx == 'T':
            for cv in cs.usedCurveData.all():
                ret.append(
                        dict(
                            x=cv.time,
                            y=cv.current,
                            isLine=True,
                            name = '',
                            color='blue',
                        )
                    )

        else:
            for cv in cs.usedCurveData.all():
                ret.append(
                        dict(
                            x=cv.potential,
                            y=cv.current,
                            isLine=True,
                            name = '',
                            color='blue',
                        )
                    )

        return ret


    def _processCurveArray(self, user, curves):
        try:
            onxs = OnXAxis.objects.get(user=user)
            onx = onxs.selected
        except:
            onxs = OnXAxis(selected='P',user=user)
            onxs.save()
            onx = onxs.selected

        ret = []

        if onx == 'S':
            for cb in curves:
                cvs = CurveData.objects.filter(curve=cb, processing=None)
                for cv in cvs:
                    ret.append(
                            dict(
                                x=range(1, len(cv.probingData)+1),
                                y=cv.probingData,
                                isLine=True,
                                name = '',
                                color='blue',
                            )
                        )

        elif onx == 'T':
            for cb in curves:
                cvs = CurveData.objects.filter(curve=cb, processing=None)
                for cv in cvs:
                    ret.append(
                            dict(
                                x=cv.time,
                                y=cv.current,
                                isLine=True,
                                name = '',
                                color='blue',
                            )
                        )

        else:
            for cb in curves:
                cvs = CurveData.objects.filter(curve=cb, processing=None)
                for cv in cvs:
                    self._line.append(
                            dict(
                                x=cv.potential,
                                y=cv.current,
                                isLine=True,
                                name = '',
                                color='blue',
                            )
                        )

        return ret


    def xLabelHelper(self, user):
        try:
            onxs = OnXAxis.objects.get(user=user)
            onx = onxs.selected
        except:
            onxs = OnXAxis(selected='P',user=user)
            onxs.save()
            onx = onxs.selected
        if ( onx == 'S' ):
            return "Sample no."
        elif ( onx == 'T' ):
            return "t / ms"
        else:
            return "E / mV"


    def analysisHelper(self, user, value_id):
        # TODO: makeover :)
        analysis = Analysis.objects.get(id=value_id)
        if not analysis.canBeReadBy(user):
            raise 3
        if not analysis.completed:
            return
        self.xlabel = 'concentration'
        self.ylabel = 'i / µA'
        # prepare data points
        self.processXY( 
                    analysis.customData['matrix'][0], 
                    analysis.customData['matrix'][1],
                    False
                )
        #prepare calibration line
        xs = analysis.customData['matrix'][0]
        xs.append(-analysis.customData['result'])
        vx= [ min(xs), max(xs) ] # x variable is used by the fitEquation
        FofX = lambda xo: analysis.customData['fitEquation']['slope'] * xo + analysis.customData['fitEquation']['intercept']
        vy = [FofX(xi) for xi in vx ]
        self.processXY(vx,vy,True)


    def add(self, x=[], y=[], name='', isLine=True, color="blue", **kwargs):
        if isLine:
            self.p.line(
                x=x,
                y=y,
                name=name,
                color=color,
                line_width=kwargs.get('line_width',2),
            )
        else:
            self.p.scatter(
                x=x,
                y=y,
                name=name,
                color=color,
                size=kwargs.get('size',8)
            )


    def _prepareFigure(self, user):
        labels = []
        onx = OnXAxis.objects.get(user=user)
        onx = onx.selected
        self.p.xaxis.axis_label = self.xlabel
        self.p.yaxis.axis_label = self.ylabel
        for k,l in dict(OnXAxis.AVAILABLE).items():
            labels.append(l)
        active = -1
        for i,k in enumerate(dict(OnXAxis.AVAILABLE).keys()):
            if k==onx:
                active = i

        if ( getattr(self, 'request',False) and self._include_x_switch ):
            jsfun= """
                function sleep (time) {
                  return new Promise((resolve) => setTimeout(resolve, time));
                }
                var act = cb_obj.active;
                var geturl = window.location.href;
                $.post( geturl, {'query': 'plotmanager', 'onx': act,
                'csrfmiddlewaretoken': '""" +\
                django.middleware.csrf.get_token(getattr(self,'request',''))\
                + """' }).done(sleep(500).then(()=>{location=window.location.href}));
                """
        else:
            jsfun = ''
        radio_button_group = RadioButtonGroup(
                labels=labels, 
                active=active,
                callback=CustomJS(args={}, code=jsfun))
        w=widgetbox(radio_button_group)
        if self.include_x_switch:
            layout = column([ self.p, w ])
        else:
            layout = column([ self.p ])
        return layout, self.p

    def process(self, request, user):
        self.request = request
        data = getattr(request, 'POST', None)
        if ( data ):
            if ( data.get('query', '') == 'plotmanager' ):
                onx =  data.get('onx', None)
                if ( onx ):
                    try:
                        onx=int(onx)
                    except:
                        return
                    ONX = OnXAxis.objects.get(user=user)
                    i=0
                    for k,v in OnXAxis.AVAILABLE:
                        if onx == i:
                            newkey=k
                            break
                        else:
                            i+=1
                    else:
                        return
                    ONX.selected = newkey
                    ONX.save()


    def __operation(self, data):
        switch = {
            'addLine': self.__addLine,
            'addCursor': self.__addCursor,
            'addPoint': self.__addPoint,
            'removeLine': self.__removeLine,
            'removeCursor': self.__removeCursor,
            'removePoint': self.__removePoint
        }
        operation = switch.get(data['operation'], 'None')
        if not operation:
            return
        else:
            return operation(data)

    def __addLine(self):
        if not data['operation'] == 'addLine':
            return
        if ( self.isJson ):
            ret = {
                    'command': 'addLine',
                    'yvec': data['yvec'],
                    'xvec': data['xvec']
            }
            return ret
        else:
            srcEmpty = ColumnDataSource(data = dict( x=[], y=[]))
            self.p.line(x='xvec',y='yvec',source=data, color='red', line_dash='dashed')
            return


    def getEmbeded(self, user, plot_type, vid):

        layout, self.p = self._prepareFigure(user)

        for l in self.__line:
            self.p.line(l['x'], l['y'], color="blue", line_width=2)

        for s in self.__scatter:
            self.p.scatter(s['x'], s['y'], color="red", size=8)

        srcEmpty = ColumnDataSource(data = dict( x=[], y=[]))
        self.p.line(x='x',y='y',source=srcEmpty, color='red', line_dash='dashed')

        cursors = []
        for i in range(4):
            C= Span(location=0,
                        dimension='height', 
                        line_color='green',
                        line_dash='dashed', 
                        line_width=2,
                        line_alpha=0
                       )
            self.p.add_layout(C)
            cursors.append(C)

        args = dict(
                    lineSrc=srcEmpty,
                    plot=self.p,
                    cursor1=cursors[0],
                    cursor2=cursors[1],
                    cursor3=cursors[2],
                    cursor4=cursors[3]
                )

        jsfun = "var type = '" + plot_type + "'; var vid = '" + str(vid) + "'; var uid = '" + str(user.id) + "';" +\
        """
                var cursors = [cursor1, cursor2, cursor3, cursor4];
                var x_data = cb_obj.x; // current mouse x position in plot coordinates
                var y_data = cb_obj.y; // current mouse y position in plot coordinates
                console.log("(x,y)=" + x_data+","+y_data); //monitors values in Javascript console
                var geturl = window.location.href + "?query=json&plot_type=" + type +"&vid=" + vid + "&x=" + x_data +"&y=" + y_data;
                $.get( geturl, function(data, status){
                        alert("Data: " + data);
                        if (status == 'success')
                            processData(plot,lineSrc,cursors,data);
                    });
        """
        callback = CustomJS(args=args, code=jsfun)
        self.p.js_on_event('tap', callback)
        return components(layout) 
