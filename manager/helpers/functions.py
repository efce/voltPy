import numpy as np
import datetime
import base64 as b64
from typing import List
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import loader
from manager.exceptions import VoltPyNotAllowed
from manager.exceptions import VoltPyFailed
import manager.plotmanager as mpm
import manager.forms as mforms
import manager.models as mmodels
from manager.helpers.decorators import with_user


def voltpy_render(*args, **kwargs):
    """
    This is proxy function which sets usually needed context elemenets.
    It is very much prefered over django default.
    """
    request = kwargs['request']
    context = kwargs.pop('context', {})
    con_scr = context.get('scripts', '')
    scr = ''.join([
        "\n",
        con_scr,
    ])
    context['bokeh_scripts'] = scr
    #context['plot_width'] = mpm.PlotManager.plot_width
    #context['plot_height'] = mpm.PlotManager.plot_height
    notifications = request.session.pop('VOLTPY_notification', [])
    if len(notifications) > 0:
        con_note = context.get('notifications', [])
        con_note.extend(notifications)
        context['notifications'] = con_note
        return render(*args, **kwargs, context=context)
    else:
        return render(*args, **kwargs, context=context)


def voltpy_serve_csv(request, filedata, filename):
    from django.utils.encoding import smart_str
    response = render(
        request=request,
        template_name='manager/export.html',
        context={'data': filedata.getvalue()}
    )
    filename = filename.strip()
    filename = filename.replace(' ', '_')
    filename = "".join(x for x in filename if (x.isalnum() or x in ('_', '+', '-', '.', ',')))
    response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(filename)
    return response


def add_notification(request, text, severity=0):
    now = datetime.datetime.now().strftime('%H:%M:%S')
    notifications = request.session.get('VOLTPY_notification', [])
    notifications.append({'text': ''.join([now, ': ', text]), 'severity': severity})
    request.session['VOLTPY_notification'] = notifications


def delete_helper(request, user, item, delete_fun=None, onSuccessRedirect=None):
    """
    The generic function to which offers ability to delete
    model instance with user confirmation.
    """
    if item is None:
        return HttpResponseRedirect(
            reverse('index')
        )

    if request.method == 'POST':
        form = mforms.DeleteForm(item, request.POST)
        if form.is_valid():
            a = form.process(item, delete_fun)
            if a:
                if onSuccessRedirect is not None:
                    return HttpResponseRedirect(
                        onSuccessRedirect
                    )
                return HttpResponseRedirect(
                    reverse('index')
                )
    else:
        form = mforms.DeleteForm(item)

    context = {
        'form': form,
        'item': item,
        'user': user
    }
    return voltpy_render(
        request=request,
        template_name='manager/deleteGeneric.html',
        context=context
    )


def generate_plot(request, user, plot_type, value_id, **kwargs):
    allowedTypes = [
        'file',
        'analysis',
        'curveset',
        'fileset',
    ]
    if plot_type not in allowedTypes:
        raise VoltPyNotAllowed('Operation not allowed.')
    vtype = kwargs.get('vtype', plot_type)
    vid = kwargs.get('vid', value_id)
    addTo = kwargs.get('add', None)

    pm = mpm.PlotManager()
    data = []
    if plot_type == 'file':
        cf = mmodels.FileCurveSet.get(id=value_id)
        data = pm.curveSetHelper(user, cf)
        pm.xlabel = pm.xLabelHelper(user)
        pm.include_x_switch = True
    elif (plot_type == 'curveset'):
        cs = mmodels.CurveSet.get(id=value_id)
        data = pm.curveSetHelper(user, cs)
        pm.xlabel = pm.xLabelHelper(user)
        pm.include_x_switch = True
    elif (plot_type == 'analysis'):
        data = pm.analysisHelper(user, value_id)
        pm.xlabel = pm.xLabelHelper(user)
        pm.include_x_switch = False
    elif (plot_type == 'fileset'):
        fs = mmodels.FileSet.get(id=value_id)
        data = []
        for f in fs.files.all():
            data.extend(pm.curveSetHelper(user, f))
        pm.xlabel = pm.xLabelHelper(user)
        pm.include_x_switch = True

    pm.ylabel = 'i / µA'
    pm.setInteraction(kwargs.get('interactionName', 'none'))

    for d in data:
        pm.add(**d)

    if addTo:
        for a in addTo:
            pm.add(**a)

    return pm.getEmbeded(request, user, vtype, vid)


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass
    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass
    return False


def form_helper(
        user,
        request,
        formClass, 
        submitName='formSubmit', 
        submitText='Submit', 
        formExtraData={}, 
        formTemplate='manager/form_inline.html'
):
    if request.method == 'POST':
        if submitName in request.POST:
            formInstance = formClass(request.POST, **formExtraData)
            if formInstance.is_valid():
                formInstance.process(user, request)
        else:
            formInstance = formClass(**formExtraData)
    else:
        formInstance = formClass(**formExtraData)

    loadedTemplate = loader.get_template(formTemplate)
    form_context = { 
        'form': formInstance, 
        'submit': submitName,
        'submit_text': submitText,
    }
    form_txt = loadedTemplate.render(
        context=form_context,
        request=request
    )
    return {'html': form_txt, 'instance': formInstance}


def get_redirect_class(redirectUrl):
    ret = '_voltJS_urlChanger _voltJS_url@%s'
    return ret % b64.b64encode(redirectUrl.encode()).decode('UTF-8')


def check_curveset_integrity(curveSet, params_to_check: List):
    if len(curveSet.curvesData.all()) < 2:
        return
    cd1 = curveSet.curvesData.all()[0]
    for cd in curveSet.curvesData.all():
        for p in params_to_check:
            if cd.curve.params[p] != cd1.curve.params[p]:
                raise VoltPyFailed('All curves in curveSet have to be similar.')


def generate_share_link(user, perm, obj):
    import manager.models
    import random
    import string
    if obj.owner != user:
        raise VoltPyNotAllowed()
    try:
        old = manager.models.SharedLink.get(
            object_type=obj.__class__.__name__,
            object_id=obj.id,
            permissions=perm
        )
        return old.getLink()
    except:
        pass
    gen_string = ''.join([
        random.choice(string.ascii_letters + string.digits) for _ in range(32)
    ])
    while manager.models.SharedLink.objects.filter(link=gen_string).exists():
        gen_string = ''.join([
            random.choice(string.ascii_letters + string.digits) for _ in range(32)
        ])

    sl = manager.models.SharedLink(
        object_type=obj.__class__.__name__,
        object_id=obj.id,
        permissions=perm,
        link=gen_string
    )
    sl.save()
    return sl.getLink()


def paginate(queryset, current_page: int, path: str):
    splpath = path.split('/')
    if is_number(splpath[-2]):
        path = '/'.join(splpath[:-2])
        path += '/'
    ret = {}
    page_size = 30
    elements = len(queryset)
    ret['number_of_pages'] = int(np.ceil(elements/page_size))
    if current_page <= 0 or current_page > ret['number_of_pages']:
        # TODO: Log wrong page number
        current_page = 1
    start = (current_page - 1) * page_size
    end = start + page_size
    ret['current_page_content'] = queryset[start:end:1]
    ret['paginator'] = ''
    ret['paginator'] = ''.join([
        '<div class="paginator">',
        '<a href="%s1/">[&lt;&lt;]</a>&nbsp' % path,
        '<a href="%s%s/">[&lt;]</a>&nbsp;' % (path, str(current_page - 1) if (current_page > 1) else "1"),
    ])
    for i in range(ret['number_of_pages']):
        p = str(i+1)
        if int(p) == current_page:
            ret['paginator'] += '[{num}]&nbsp;'.format(num=p)
        else: 
            ret['paginator'] += '<a href="{path}{num}/">[{num}]</a>&nbsp;'.format(path=path, num=p)
    ret['paginator'] += ''.join([
        '<a href="%s%s/">[&gt;]</a>&nbsp;' % (path, str(current_page+1) if (current_page < ret['number_of_pages']) else str(ret['number_of_pages'])),
        '<a href="%s%s/">[&gt;&gt;]</a>' % (path, str(ret['number_of_pages'])),
        '&nbsp; %d items per page' % page_size,
        '</div>'
    ])
    return ret


def getUser():
    return with_user._user
