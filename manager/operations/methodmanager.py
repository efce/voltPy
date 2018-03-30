import sys
import os
import io
import numpy as np
import base64 as b64
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.http import HttpResponseRedirect
import manager.models as mmodels
from manager.exceptions import VoltPyFailed
from manager.helpers.functions import generate_plot
from manager.helpers.functions import voltpy_render
from manager.helpers.functions import add_notification
from manager.exceptions import VoltPyDoesNotExists


class MethodManager:
    """
    MethodManager loads and manages the data processing
    and analysis procedures. Each procedure should be 
    placed in "./methods/" directory and it should contain
    variable main_class = <Class Object>.
    The main class object should inherit
    either from AnalysisMethod or ProcessingMethod. 
    If procedure meets the requirements it should be immedietly
    avaiable for usage.
    """

    def __init__(self, user, **kwargs):
        self.methods = {
            'processing': dict(),
            'analysis': dict()
        }
        self.__type = None
        self.__method = None
        self.__model = None

        self.__loadMethods()

        if 'curveset_id' in kwargs:
            self.__type = 'other'
            self.__curveset_id = int(kwargs.get('curveset_id', None))
            return
        elif 'processing_id' in kwargs or 'processing' in kwargs:
            self.__type = 'processing'
            _id = int(kwargs.get('processing_id', kwargs.get('processing')))
            try:
                self.__model = mmodels.Processing.objects.get(id=_id)
                self.__curveset_id = self.__model.curveSet.id
            except ObjectDoesNotExist:
                raise VoltPyDoesNotExists
        elif 'analysis_id' in kwargs or 'analysis' in kwargs:
            self.__type = 'analysis'
            _id = int(kwargs.get('analysis_id', kwargs.get('analysis')))
            try:
                self.__model = mmodels.Analysis.objects.get(id=_id)
            except ObjectDoesNotExist:
                raise VoltPyDoesNotExists
        else:
            raise NameError('Unknown type')
        self.__activateMethod()

    def __loadMethods(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        methodspath = dir_path + "/methods/"
        onlyfiles = [
            f for f in os.listdir(methodspath) if os.path.isfile(os.path.join(methodspath, f)) and f.endswith('.py')
        ]
        sys.path.append(methodspath)
        for fm in onlyfiles:
            if not fm == '__init__.py':
                fname = fm[:-3]
                fimp = __import__(fname)
                class_object = fimp.main_class
                self.__registerMethod(class_object)

    def __registerMethod(self, mclass):
        if str(mclass.__name__) == self.methods[mclass.type()]:
            raise NameError("Name " + repr(mclass) + " already exists in " + mclass.type())
        self.methods[mclass.type()][str(mclass.__name__)] = mclass

    def __activateMethod(self):
        mclass = self.methods[self.__type].get(self.__model.method, None)
        if mclass:
            self.__method = mclass(self.__model)

    def process(self, request, user):
        if any([
            request.method != 'POST',
            request.POST.get('query') != 'methodmanager'
        ]):
            return
        if self.__method:
            try:
                self.__method.process(user=user, request=request)
            except VoltPyFailed as e:
                self.__model.deleted = True
                self.__model.save()
                add_notification(request, 'Procedure failed. The data may be incompatible with the processing method. Please verify and try again.')
                add_notification(request, 'Fail reason: %s' % e)

    def exportFile(self):
        memoryFile = io.StringIO()
        numpyarr = self.__method.exportableData()
        np.savetxt(memoryFile, numpyarr, delimiter=",", newline="\r\n", fmt='%s')
        return memoryFile, self.__model.name

    def getJSON(self, user):
        if not self.__method.has_next:
            return {'command': 'redirect', 'location': self.__model.getUrl(user)}
        else:
            return {'command': 'reload'}

    def getContent(self, request, user):
        if self.__model.deleted:
            add_notification(request, 'Procedure delted.', 0)
            return HttpResponseRedirect(reverse("showCurveSet", args=[self.__model.curveSet.id]))

        if any([
            self.__method.has_next is False,
            self.__method.step is None
        ]):
            return HttpResponseRedirect(self.__model.getUrl(user))

        if not self.isMethodSelected():
            return HttpResponseRedirect(reverse("browseCurveSet"))

        stepText = dict(
            head='',
            body='No text'
        )

        if self.__method.step:
            stepText = self.__method.getStepHTML(
                user=user,
                request=request
            )

            step_numInfo = '<p>Step: {0} out of {1}</p>'.format(
                self.__model.active_step_num+1,
                len(self.__method._steps)
            )

            plotScr, plotDiv = generate_plot(
                request=request, 
                user=user, 
                plot_type='curveset',
                value_id=self.__model.curveSet.id,
                vtype=self.__method.type(),
                vid=self.__model.id,
                interactionName=self.__method.step['class'].plot_interaction,
                add=self.__method.getAddToPlot()
            )

            context = {
                'scripts': '\n'.join([ 
                                        plotScr, 
                                        stepText.get('head', '')
                                    ]),
                'mainPlot': plotDiv,
                'method_content': ''.join([
                                        step_numInfo,
                                        stepText.get('desc', ''),
                                        stepText.get('body', ''),
                                    ]),
                'user': user,
                'model': self.__model,
                'curveset_id': self.__model.curveSet.id,
            }

            return voltpy_render(
                request=request,
                template_name='manager/method.html',
                context=context,
            )

    def getAnalysisSelectionForm(self, *args, **kwargs):
        return MethodManager.SelectionForm(
            self,
            self.methods['analysis'],
            type='analysis',
            prefix='analysis',
            *args, 
            **kwargs
        )

    def getProcessingSelectionForm(self, *args, **kwargs):
        return MethodManager.SelectionForm(
            self, 
            self.methods['processing'],
            type='processing', 
            prefix='processing',
            *args, 
            **kwargs
        )

    def getInfo(self, request, user):
        if self.__method:
            return self.__method.getInfo(request=request, user=user)
        else:
            return ''

    def isMethodSelected(self):
        return (self.__method is not None)

    class SelectionForm(forms.Form):
        """
        Should not be obtained directly, only by:
        MethoManager.getSelectionForm('processing'/'analysis')
        """
        def __init__(self,  parent, methods, *args, **kwargs):
            self.type = kwargs.pop('type', 'processing')
            if self.type == 'processing':
                label = "Processing method"
            elif self.type == 'analysis':
                label = 'Analysis method'
            disabled = kwargs.pop('disabled', False)
            super(MethodManager.SelectionForm, self).__init__(*args, **kwargs)
            self.methods = methods
            self.parent = parent
            choices = list(
                zip(
                    [str(k) for k, v in methods.items()],
                    [v.__str__() for k, v in methods.items()]
                )
            )

            self.fields['method'] = forms.ChoiceField(
                choices=choices,
                required=True, 
                label=label,
                disabled=disabled
            )
            self.fields['method-description'] = forms.CharField(
                widget=forms.Textarea(attrs={'readonly': 'readonly'}),
                required=False,
                initial=self.methods[list(self.methods)[0]].description,
                label="Description:"
            )

        def getJS(self, request):
            import json
            js_dict = json.dumps(
                dict(
                    zip(
                        [str(k) for k, v in self.methods.items()],
                        [v.description for k, v in self.methods.items()],
                    )
                )
            )
            active_field_id = 'id_' + self.prefix + '-method'
            js_data = """
<script type='text/javascript'>
$(function(){{
    $('#{field_id}').change(function(){{
        dict = {js_dict};
        active =  $('#{field_id}').val();
        mess = dict[active];
        $('#{field_id}-description').val(mess);
    }});
}});
</script>""".format(field_id=active_field_id, js_dict=js_dict)
            return js_data

        def process(self, user, curveset):
            if self.type == 'processing':
                if self.cleaned_data.get('method') in self.methods:
                    a = mmodels.Processing(
                        owner=user,
                        curveSet=curveset,
                        method=self.cleaned_data.get('method'), 
                        name="",
                        active_step_num=0,
                        deleted=False,
                        completed=False
                    )
                    curveset.prepareUndo()
                    a.save()
                    return a.id
                else:
                    return None
            elif self.type == 'analysis':
                if self.cleaned_data.get('method') in self.methods:
                    a = mmodels.Analysis(
                        owner=user,
                        curveSet=curveset,
                        method=self.cleaned_data.get('method'),
                        name="",
                        active_step_num=0,
                        deleted=False,
                        completed=False
                    )
                    a.save()
                    curveset.locked = True  # CurveSet cannot be changed when used by Analysis method.
                    curveset.save()
                    return a.id
                else:
                    return None
