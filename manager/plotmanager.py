import io
import numpy as np
import json
import django
import random
from copy import copy
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
import bokeh
from bokeh.plotting import figure, ColumnDataSource
from bokeh.embed import components
from bokeh.models.callbacks import CustomJS
from bokeh.models import Span
from bokeh.layouts import widgetbox, column, row
from bokeh.models.widgets import RadioButtonGroup, Button, Paragraph
import manager.models as mmodels
from manager.exceptions import VoltPyNotAllowed


class PlotManager:
    methodmanager = None
    interaction = 'none'
    include_x_switch = False
    title = ''
    xlabel = "x"
    ylabel = "y"
    plot_width = 700
    plot_height = 600
    interactions = [
        'set1cursor',
        'set2cursors',
        'set4cursors',
        'confirm',
        'none'
    ]

    def __init__(self):
        self.__random = str(random.random()).replace(".", "")
        self.__line = []
        self.__scatter = []
        self.p = figure(
            title=self.title, 
            name='voltpy_plot',
            x_axis_label=self.xlabel,
            y_axis_label=self.ylabel,
            height=self.plot_height-10,
            width=self.plot_width-20
        )

    def curveSetHelper(self, user, cs):
        if not cs.canBeReadBy(user):
            raise VoltPyNotAllowed

        ret = []
        for cd in cs.curvesData.all():
            ret.append({
                'x': cd.xVector,
                'y': cd.yVector,
                'plottype': 'line',
                'name': 'curve_%i' % cd.id,
                'color': 'blue',
            })
        return ret

    def xLabelHelper(self, user):
        onx = user.profile.show_on_x
        if onx == 'S':
            return "Sample no."
        elif onx == 'T':
            return "t / ms"
        else:
            return "E / mV"

    def analysisHelper(self, user, value_id):
        # TODO: makeover :)
        analysis = mmodels.Analysis.objects.get(id=value_id)
        if not analysis.canBeReadBy(user):
            raise 3
        if not analysis.completed:
            return
        # prepare data points
        ret = []
        ret.append({
            'x': analysis.customData['matrix'][0],
            'y': analysis.customData['matrix'][1],
            'plottype': 'scatter',
            'color': 'red',
            'size': 8
        })
        # prepare calibration line
        xs = copy(analysis.customData['matrix'][0])
        if analysis.customData['result'] is not None:
            xs.append(-analysis.customData['result'])
        vx = [min(xs), max(xs)]  # x variable is used by the fitEquation

        def FofX(xo):
            return (
                analysis.customData['fitEquation']['slope']
                * xo
                + analysis.customData['fitEquation']['intercept']
            )

        vy = [FofX(xi) for xi in vx]
        ret.append({
            'x': vx,
            'y': vy,
            'plottype': 'line',
            'color': 'blue',
            'line_width': 2
        })
        return ret

    def add(self, x=[], y=[], name='', plottype='line', color="blue", **kwargs):
        allowedtyped = ['line', 'scatter', 'cursor']
        if plottype == 'line':
            self.p.line(
                x=x,
                y=y,
                name=name,
                color=color,
                line_width=kwargs.get('line_width', 2),
            )
        elif plottype == 'scatter':
            self.p.scatter(
                x=x,
                y=y,
                name=name,
                color=color,
                size=kwargs.get('size', 8)
            )
        elif plottype == 'cursor':
            if (len(x) > 1):
                ValueError('When adding cursor only one x value is allowed')
            C = Span(
                location=x[0],
                dimension='height', 
                line_color=color,
                line_dash='dashed', 
                line_width=2,
                line_alpha=1
            )
            self.p.add_layout(C)

    def _prepareFigure(self, request, user, vtype, vid):
        self.p.height = self.plot_height
        self.p.width = self.plot_width
        labels = []
        onx = user.profile.show_on_x
        self.p.xaxis.axis_label = self.xlabel
        self.p.yaxis.axis_label = self.ylabel
        vline = Span(
            location=0,
            dimension='height',
            line_color='black',
            line_width=1,
            level='underlay'
        )
        hline = Span(
            location=0,
            dimension='width',
            line_color='black',
            line_width=1,
            level='underlay'
        )
        self.p.renderers.extend([vline, hline])
        dict_onx = dict(mmodels.Profile.ONX_OPTIONS)
        for k, l in dict_onx.items():
            labels.append(l)
        active = -1
        for i, k in enumerate(dict_onx.keys()):
            if k == onx:
                active = i

        funmaster = """
        switch (window.voltPy1.command) {
        case 'set1cursor':
            if (cursors[0].location == null) {
                cursors[0].location = cb_obj.x;
                cursors[0].line_alpha = 1;
                $('#id_val_cursor_0').val(cb_obj.x);
            } else {
                //cursor is set, do nothing.
                return;
            }
            break;
        case 'set2cursors':
            if (cursors[0].location == null) {
                cursors[0].location = cb_obj.x;
                cursors[0].line_alpha = 1;
                $('#id_val_cursor_0').val(cb_obj.x);
            } else if (cursors[1].location == null) {
                cursors[1].location = cb_obj.x;
                cursors[1].line_alpha = 1;
                $('#id_val_cursor_1').val(cb_obj.x);
            } else {
                //cursors are set, do nothing.
                return;
            }
            break;
        case 'set4cursors':
            if (cursors[0].location == null) {
                cursors[0].location = cb_obj.x;
                cursors[0].line_alpha = 1;
                $('#id_val_cursor_0').val(cb_obj.x);
            } else if (cursors[1].location == null) {
                cursors[1].location = cb_obj.x;
                cursors[1].line_alpha = 1;
                $('#id_val_cursor_1').val(cb_obj.x);
            } else if (cursors[2].location == null) {
                cursors[2].location = cb_obj.x;
                cursors[2].line_alpha = 1;
                $('#id_val_cursor_2').val(cb_obj.x);
            } else if (cursors[3].location == null) {
                cursors[3].location = cb_obj.x;
                cursors[3].line_alpha = 1;
                $('#id_val_cursor_3').val(cb_obj.x);
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
        jsonurl = reverse('plotInteraction')

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
        srcEmpty = ColumnDataSource(data = dict(x=[], y=[]))
        self.p.line(x='x', y='y', source=srcEmpty, color='red', line_dash='dashed')
        cursors = []
        for i in range(4):
            C = Span(
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
        # SUPER HACK -- COVER PLOT UNTIL NEW IS READY:
        js_axisSub = """
        var yheight = (plot.y_range.end - plot.y_range.start);
        var yavg = yheight/2 + plot.y_range.start;
        var source = new Bokeh.ColumnDataSource({ data: { 
                x: [plot.x_range.start, plot.x_range.end],
                y: [yavg, yavg] 
            } 
        });
        var cover = new Bokeh.Line({
            x: { field: "x" }, 
            y: { field: "y"}, 
            line_color: "#FFFFFF", 
            line_width: plot.plot_height,
        }); 
        plot.add_glyph(cover, source);
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
                    $('#id_val_cursor_' + i).val('');
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


        #bforward = Button(
        #    label="Forward", 
        #    width=250,
        #    callback=CustomJS(args=args, code=js_forward)
        #)
        #bback = Button(
        #    label="Back", 
        #    width=250, 
        #    callback=CustomJS(args=args, code=js_back)
        #)
        bunselect = Button(
            label="Unselect", 
            width=250, 
            callback=CustomJS(args=args, code=js_back)
        )
        px = Paragraph(text="""X axis:""", width=50)
        if not self.interaction or self.interaction == 'none':
            w=widgetbox(radio_button_group)
            actionbar = row([px, w], width=self.plot_width)
        else:
            w=widgetbox(radio_button_group)
            #actionbar = row([px, w, bback, bforward], width=self.plot_width)
            actionbar = row([px, w, bunselect], width=self.plot_width-50)

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
                if ( onx is not None ):
                    try:
                        onx = int(onx)
                    except ValueError:
                        raise
                    ONX = user.profile.show_on_x
                    for k,v in enumerate(dict(mmodels.Profile.ONX_OPTIONS).keys()):
                        if onx == k:
                            newkey = v
                            break
                    else:
                        return
                    user.profile.show_on_x = newkey
                    user.profile.save()
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
        assert name in self.interactions
        self.interaction = name

    def getEmbeded(self, request, user, vtype, vid):
        layout = self._prepareFigure(request, user, vtype, vid)
        src,div = components(layout) 
        src = '\n'.join([
            src,
            "<script type='text/javascript'>$(function(){window.voltPy1 = { 'command': '" + \
                    self.interaction + "' };});</script>"
        ])
        return src,div
