from django.db.models import Q
from .models import *
import io
import numpy as np
import json 
import django
import random
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from bokeh.plotting import figure, ColumnDataSource
from bokeh.embed import components
from bokeh.models.callbacks import CustomJS
from bokeh.models import Span
from bokeh.layouts import widgetbox, column, row
from bokeh.models.widgets import RadioButtonGroup, Button, Paragraph
import bokeh

class PlotManager:
    methodmanager = None
    interaction = 'none'
    include_x_switch = False
    title = ''
    xlabel = "x"
    ylabel = "y"
    bver = bokeh.__version__
    plot_width = 850
    plot_height = 700
    required_scripts = ''.join([
    """
    <link href="http://cdn.pydata.org/bokeh/release/bokeh-%(bver)s.min.css" rel="stylesheet" type="text/css"> 
    <link href="http://cdn.pydata.org/bokeh/release/bokeh-widgets-%(bver)s.min.css" rel="stylesheet" type="text/css"> 
    <script src="http://cdn.pydata.org/bokeh/release/bokeh-%(bver)s.min.js"></script> 
    <script src="http://cdn.pydata.org/bokeh/release/bokeh-widgets-%(bver)s.min.js"></script>
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
    <script type="text/javascript">
    """ % { 'bver': bver },
    """
    function sleep (time) {
        return new Promise((resolve) => setTimeout(resolve, time));
    }
    function processJSONReply (data, plot='',lineData='',cursors='') {
        switch (data.command) {
        case 'none':
            return;
        case 'reload':
            sleep(500).then(()=>{location.reload();});
            break;
        case 'redirect':
            location = data.location;
            break;
        case 'setCursor':
            cursors[data.number].location = parseFloat(data.x);
            cursors[data.number].line_alpha = 1;
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
            break;
        case 'changeColor':
        default:
            alert('Not implemented...');
        }
    }
    function queryServer(url, object, plot=null, lineData=null, cursors=null) {
    alert('querying server');
            window.scrollTo(0, 0);
            $('body').css('overflow','hidden');
            $('#voltpy-loading').css('position', 'absolute');
            $('#voltpy-loading').css('top','0px');
            $('#voltpy-loading').css('left','0px');
            $('#voltpy-loading').css('width','100%');
            $('#voltpy-loading').css('font-size','large');
            $('#voltpy-loading').css('height','100%');
            $('#voltpy-loading').css('z-index','999');
            $('#voltpy-loading').css('background-color','white');
            $('#voltpy-loading').css('color','black');
            $('#voltpy-loading').css('display','block');
            $('#voltpy-loading').css('text-align','center');
            $('#voltpy-loading').css('vertical-align','middle');
            $('#voltpy-loading').css('opacity','0.9');
            $('#voltpy-loading').css('line-height',$('#voltpy-loading').css('height'));
            $('#voltpy-loading').text('Loading ...');
            $.post(url, object).done(
                function(data) {
                    processJSONReply(data, plot, lineData, cursors);
                    $('#voltpy-loading').css('display','none');
                    $('body').css('overflow','scroll');
                }
            );
    };
    </script>
    """
    ])
    def __init__(self):
        self.__random = str(random.random()).replace(".","")
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
        self.required_scripts = self.required_scripts
    

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
        except ObjectDoesNotExist:
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
                        plottype='line',
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
                        plottype='line',
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
                        plottype='line',
                        name = '',
                        color='blue',
                    )
                )

        return ret


    def _processCurveArray(self, user, curves):
        try:
            onxs = OnXAxis.objects.get(user=user)
            onx = onxs.selected
        except ObjectDoesNotExist:
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
                            plottype='line',
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
                            plottype='line',
                            name = '',
                            color='blue',
                        )
                    )
        else:
            for cb in curves:
                cvs = CurveData.objects.filter(curve=cb, processing=None)
                for cv in cvs:
                    ret.append(
                        dict(
                            x=cv.potential,
                            y=cv.current,
                            plottype='line',
                            name = '',
                            color='blue',
                        )
                    )

        return ret


    def xLabelHelper(self, user):
        try:
            onxs = OnXAxis.objects.get(user=user)
            onx = onxs.selected
        except ObjectDoesNotExist:
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
        # prepare data points
        ret = []
        ret.append( {
            'x': analysis.customData['matrix'][0], 
            'y': analysis.customData['matrix'][1],
            'plottype':'scatter',
            'color': 'red',
            'size': 8
        })
        #prepare calibration line
        xs = analysis.customData['matrix'][0]
        xs.append(-analysis.customData['result'])
        vx= [ min(xs), max(xs) ] # x variable is used by the fitEquation
        FofX = lambda xo: analysis.customData['fitEquation']['slope'] * xo + analysis.customData['fitEquation']['intercept']
        vy = [FofX(xi) for xi in vx ]
        ret.append({
            'x': vx,
            'y': vy,
            'plottype':'line',
            'color': 'blue',
            'line_width': 2
        })
        return ret

    def add(self, x=[], y=[], name='', plottype='line', color="blue", **kwargs):
        allowedtyped = [ 'line', 'scatter', 'cursor' ];
        if plottype == 'line':
            self.p.line(
                x=x,
                y=y,
                name=name,
                color=color,
                line_width=kwargs.get('line_width',2),
            )
        elif plottype == 'scatter':
            self.p.scatter(
                x=x,
                y=y,
                name=name,
                color=color,
                size=kwargs.get('size',8)
            )
        elif plottype == 'cursor':
            if ( len(x) > 1 ):
                ValueError('When adding cursor only one x value is allowed')
            C= Span(
                location=x[0],
                dimension='height', 
                line_color=color,
                line_dash='dashed', 
                line_width=2,
                line_alpha=1
            )
            self.p.add_layout(C)

    def _prepareFigure(self, request, user, vtype, vid):
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

        funmaster = """
        switch (window.voltPy1.command) {
        case 'set1cursor':
            if (cursors[0].location == null) {
                cursors[0].location = cb_obj.x;
                cursors[0].line_alpha = 1;
            } else {
                //cursor is set, do nothing.
                return;
            }
            break;
        case 'set2cursors':
            if (cursors[0].location == null) {
                cursors[0].location = cb_obj.x;
                cursors[0].line_alpha = 1;
            } else if (cursors[1].location == null) {
                cursors[1].location = cb_obj.x;
                cursors[1].line_alpha = 1;
            } else {
                //cursors are set, do nothing.
                return;
            }
            break;
        case 'set4cursors':
            if (cursors[0].location == null) {
                cursors[0].location = cb_obj.x;
                cursors[0].line_alpha = 1;
            } else if (cursors[1].location == null) {
                cursors[1].location = cb_obj.x;
                cursors[1].line_alpha = 1;
            } else if (cursors[2].location == null) {
                cursors[2].location = cb_obj.x;
                cursors[2].line_alpha = 1;
            } else if (cursors[3].location == null) {
                cursors[3].location = cb_obj.x;
                cursors[3].line_alpha = 1;
            } else {
                //cursors are set, do nothing.
                return;
            }
            break;
        default:
            return;
        }
        """
        js_globalBase = "var cursors = [cursor1, cursor2, cursor3, cursor4];"
        jsonurl = reverse('plotInteraction', args=[ user.id ])

        js_postRequired = '\n'.join([
            js_globalBase,
            "var jsonurl = '" + jsonurl + "';",
            "var vtype = '" + vtype + "';",
            "var vid = '" + str(vid) + "';",
            "var uid = '" + str(user.id) + "';",
            "var token = '" + django.middleware.csrf.get_token(request) + "';",
        ])
        js_plot = '\n'.join([
            js_globalBase,
            funmaster
        ])
        srcEmpty = ColumnDataSource(data = dict( x=[], y=[]))
        self.p.line(x='x',y='y',source=srcEmpty, color='red', line_dash='dashed')
        cursors = []
        for i in range(4):
            C= Span(
                location=None,
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
        js_plot = '\n'.join([
            js_globalBase,
            funmaster
        ])
        callback = CustomJS(args=args, code=js_plot)
        self.p.js_on_event('tap', callback)
        js_axisSub = """
        var object = { 
            'query': 'plotmanager', 
            'onx': cb_obj.active,
            'csrfmiddlewaretoken': token, 
        };
        queryServer(jsonurl, object);
        """

        js_xaxis = '\n'.join([
            js_postRequired,
            js_axisSub
        ])

        radio_button_group = RadioButtonGroup(
            labels=labels, 
            active=active,
            callback=CustomJS(args=args, code=js_xaxis)
        )

        js_backSub = """
        var coma = window.voltPy1.command;
        if ( coma == 'set1cursor'
        || coma == 'set2cursors'
        || coma == 'set4cursors' ) {
            for (i=cursors.length-1; i>=0; i--) {
                if ( cursors[i].location != null ) {
                    cursors[i].location = null;
                    cursors[i].line_alpha = 0;
                    break;
                }
            }
        } else if ( coma == 'confirm' ) {
            var object = { 
                'query': 'methodmanager',
                'command': 'cancel',
                'csrfmiddlewaretoken': token, 
                'vtype': vtype, 
                'vid': vid
            }
            queryServer(jsonurl, object, plot, lineSrc, cursors);
        }

        """
        js_back = '\n'.join([
            js_postRequired,
            js_backSub
        ])

        js_forwardSub = """
        switch ( window.voltPy1.command ) {
        case 'set1cursor':
            if ( cursors[0].location == null ) {
                alert('Please set one curosor on the plot');
                return;
            } 
            break;
        case 'set2cursors':
            if ( ( cursors[0].location == null )
            || ( cursors[1].location == null ) ) {
                alert('Please set two cursors on the plot');
                return;
            }
            break;
        case 'set4cursors':
            if ( ( cursors[0].location == null )
            || ( cursors[1].location == null )
            || ( cursors[2].location == null )
            || ( cursors[3].location == null ) ) {
                alert('Please set four cursors on the plot');
                return;
            }
            break;
        case 'confirm':
            break;
        default:
            return;
        }
        var object = { 
            'query': 'methodmanager',
            'command': window.voltPy1.command,
            'cursor1': cursors[0].location, 
            'cursor2': cursors[1].location, 
            'cursor3': cursors[2].location, 
            'cursor4': cursors[3].location, 
            'csrfmiddlewaretoken': token, 
            'vtype': vtype, 
            'vid': vid
        }
        queryServer(jsonurl, object, plot, lineSrc, cursors);
        """
        js_forward = '\n'.join([
            js_postRequired,
            js_forwardSub
        ])


        bforward = Button(
            label="Forward", 
            width=250,
            callback=CustomJS(args=args, code=js_forward)
        )
        bback = Button(
            label="Back", 
            width=250, 
            callback=CustomJS(args=args, code=js_back)
        )
        p = Paragraph(text="""X axis:""", width=50)
        if not self.interaction or self.interaction == 'none':
            w=widgetbox(radio_button_group)
            actionbar = row([p, w], width=self.plot_width)
        else:
            w=widgetbox(radio_button_group)
            actionbar = row([p, w, bback, bforward], width=self.plot_width)
        if self.include_x_switch:
            layout = column([self.p, actionbar])
        else:
            layout = column([self.p])
        return layout


    def plotInteraction(self, request, user):
        self.request = request
        data = getattr(request, 'POST', None)
        if ( data ):
            query = data.get('query', '')  
            if ( query == 'plotmanager' ):
                onx = data.get('onx', None)
                if ( onx ):
                    try:
                        onx=int(onx)
                    except ValueError:
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
                    return { 'command': 'reload' }


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

    def setInteraction(self, name):
        self.interaction = name

    def getEmbeded(self, request, user, vtype, vid):
        layout = self._prepareFigure(request, user, vtype, vid)
        src,div = components(layout) 
        src = '\n'.join([
            src,
            "<script type='text/javascript'>(function(){window.voltPy1 = { 'command': '" + \
                    self.interaction + "' };})();</script>"
        ])
        return src,div
