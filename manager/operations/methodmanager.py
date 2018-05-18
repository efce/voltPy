import sys
import os
import io
from typing import Dict
import numpy as np
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.template import loader
import manager.models as mmodels
from manager.exceptions import VoltPyDoesNotExists
from manager.exceptions import VoltPyFailed
from manager.helpers.functions import generate_plot
from manager.helpers.functions import voltpy_render
from manager.helpers.functions import add_notification
from manager.helpers.functions import get_user


class MethodManager:
    """
    MethodManager loads and manages the data processing
    and analysis procedures. Each procedure should be
    placed in "./methods/" directory and it should contain
    variable main_class = <Class Object>.
    The main class object should inherit
    either from AnalysisMethod or ProcessingMethod.
    If procedure meets the requirements it should be immediately
    available for usage.
    """

    def __init__(self, user, **kwargs):
        self.methods = {
            'processing': dict(),
            'analysis': dict()
        }
        self.__type = None
        self.__method = None
        self.__model = None
        self.__user = user

        self.__loadMethods()

        if 'dataset_id' in kwargs:
            self.__type = 'other'
            self.__dataset_id = int(kwargs.get('dataset_id', None))
            return
        elif 'processing_id' in kwargs or 'processing' in kwargs:
            self.__type = 'processing'
            _id = int(kwargs.get('processing_id', kwargs.get('processing')))
            try:
                self.__model = mmodels.Processing.get(id=_id)
                self.__dataset_id = self.__model.dataset.id
            except ObjectDoesNotExist:
                raise VoltPyDoesNotExists
        elif 'analysis_id' in kwargs or 'analysis' in kwargs:
            self.__type = 'analysis'
            _id = int(kwargs.get('analysis_id', kwargs.get('analysis')))
            try:
                self.__model = mmodels.Analysis.get(id=_id)
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
                add_notification(request, """
                    Procedure failed. The data may be incompatible with the processing method.
                    Please verify and try again.
                """)
                add_notification(request, 'Fail reason: %s' % e)

    def exportFile(self):
        """
        Exports data provided by the methods as csv files.
        """
        memoryFile = io.StringIO()
        numpyarr = self.__method.exportableData()
        np.savetxt(memoryFile, numpyarr, delimiter=",", newline="\r\n", fmt='%s')
        return memoryFile, self.__model.name

    def ajax(self, user) -> Dict:
        """
        Replies to json request.
        """
        if not self.__method.has_next:
            return {'command': 'redirect', 'location': self.__model.getUrl()}
        else:
            return {'command': 'reload'}

    def getStepContent(self, request, user):
        """
        Provides contents of processing step of methods.
        """
        if self.__model.deleted:
            add_notification(request, 'Procedure delted.', 0)
            return HttpResponseRedirect(self.__model.dataset.getUrl())

        if any([
            self.__method.has_next is False,
            self.__method.step is None
        ]):
            return HttpResponseRedirect(self.__model.getUrl())

        if not self.isMethodSelected():
            return HttpResponseRedirect(reverse("browseDataset"))

        stepText = {
            'head': '',
            'body': 'No text'
        }

        if self.__method.step:
            stepText = self.__method.getStepContent(
                user=user,
                request=request
            )

            step_numInfo = '{0} out of {1}'.format(
                self.__model.active_step_num+1,
                len(self.__method._steps)
            )

            plotScr, plotDiv, butDiv = generate_plot(
                request=request,
                user=user,
                to_plot=self.__model.dataset,
                vtype=self.__method.type(),
                vid=self.__model.id,
                interactionName=self.__method.step['class'].plot_interaction,
                add=self.__method.addToMainPlot()
            )

            context = {
                'scripts': '\n'.join([
                                        plotScr,
                                        stepText.get('head', '')
                                    ]),
                'main_plot': plotDiv,
                'main_plot_buttons': butDiv,
                'method_content': ''.join([
                                        '<fieldset class="mt_rest"><legend class="mt_name">Step</legend>%s</fieldset>' % step_numInfo,
                                        '<fieldset class="mt_rest"><legend class="mt_name">Description</legend>%s</fieldset>' % stepText.get('desc', ''),
                                        '<div class="mt_rest">%s</div>' % stepText.get('body', ''),
                                    ]),
                'user': user,
                'model': self.__model,
                'dataset_id': self.__model.dataset.id,
            }

            return voltpy_render(
                request=request,
                template_name='manager/method.html',
                context=context,
            )

    def methodCanBeApplied(self) -> bool:
        return self.__method.can_be_applied

    def applyTo(self, user, request, dataset_id) -> None:
        try:
            cs = mmodels.Dataset.get(id=int(dataset_id))
        except (ObjectDoesNotExist, ValueError):
            raise VoltPyDoesNotExists
        try:
            ret_id = self.__method.apply(user=user, dataset=cs)
        except VoltPyFailed as e:
            add_notification(request, """
                Procedure failed. The data may be incompatible with the processing method.
                Please verify and try again.
            """)
            raise e

        if not self.__method.isAnalysis():
            return cs.getUrl()
        else:
            return reverse("showAnalysis", args=[ret_id])

    def getAnalysisSelectionForm(self, *args, **kwargs):
        """
        Returns form instance with selection of analysis methods.
        """
        dataset = kwargs.pop('dataset')
        return MethodManager._AltSelectionForm(
            self,
            self.methods['analysis'],
            type='analysis',
            prefix='analysis',
            dataset=dataset,
            *args,
            **kwargs
        )

    def getProcessingSelectionForm(self, *args, **kwargs):
        """
        Returns form instance with selection of processing methods.
        """
        dataset = kwargs.pop('dataset')
        return MethodManager._AltSelectionForm(
            self,
            self.methods['processing'],
            type='processing',
            prefix='processing',
            dataset=dataset,
            *args,
            **kwargs
        )

    def getFinalContent(self, request, user) -> Dict:
        """
        Returns content of finalized analysis method.
        """
        if self.__method:
            return self.__method.getFinalContent(request=request, user=user)
        else:
            raise VoltPyDoesNotExists('Method could not be loaded.')

    def isMethodSelected(self) -> bool:
        return (self.__method is not None)

    class _AltSelectionForm(forms.Form):
        def __init__(self, parent, methods: Dict, *args, **kwargs):
            dataset = kwargs.pop('dataset')
            self.type = kwargs.pop('type', 'processing')
            if self.type == 'processing':
                label = 'Processing method'
            elif self.type == 'analysis':
                label = 'Analysis method'
            else:
                raise ValueError('Wrong value %s as type in %s' % (self.type, self.__str__()))
            self.disabled = kwargs.pop('disabled', False)
            super(MethodManager._AltSelectionForm, self).__init__(*args, **kwargs)
            self.methods = methods
            self.parent = parent
            choices = list(
                zip(
                    [str(k) for k, v in methods.items()],
                    [v.__str__() for k, v in methods.items()]
                )
            )
            self._checkDataset(dataset)

            defKey = list(self.methods)[0]
            defMethod = self.methods[defKey]
            self.fields['method'] = forms.ChoiceField(
                choices=choices,
                required=True,
                label=label,
                initial=defKey
            )

        def _checkDataset(self, dataset):
            for k, v in self.methods.items():
                v.errors = []
                for check in v.checks:
                    if check is None:
                        continue
                    try:
                        check(dataset)
                    except VoltPyFailed as err:
                        v.errors.append(err)
        
        def draw(self):
            to_disp = [(k, v.__str__(), v.description or '', v.errors, v.video) for k, v in self.methods.items()]
            context = {
                'disabled': self.disabled,
                'methods': to_disp,
                'type': self.type,
                'user': get_user()
            }
            tt = loader.get_template('manager/method_selection.html')
            return tt.render(context=context)

        def process(self, user, dataset):
            self._checkDataset(dataset)
            if self.type == 'processing':
                mname = self.cleaned_data.get('method', None)
                if mname in self.methods:
                    if self.methods[mname].errors:
                        errors = '\n'.join([str(x) for x in self.methods[mname].errors])
                        raise VoltPyFailed('Data does not meets requirements for selected method: %s' % errors)
                    a = mmodels.Processing(
                        owner=user,
                        dataset=dataset,
                        method=mname,
                        method_display_name=self.methods[mname].__str__(),
                        name='',
                        active_step_num=0,
                        deleted=False,
                        completed=False
                    )
                    a.save()
                    dataset.prepareUndo(processing_instance=a)
                    return a.id
                return None
            elif self.type == 'analysis':
                mname = self.cleaned_data.get('method', None)
                if mname in self.methods:
                    if self.methods[mname].errors:
                        errors = '\n'.join([str(x) for x in self.methods[mname].errors])
                        raise VoltPyFailed('Data does not meets requirements for selected method: %s' % errors)
                    a = mmodels.Analysis(
                        owner=user,
                        dataset=dataset,
                        method=mname,
                        method_display_name=self.methods[mname].__str__(),
                        name='',
                        active_step_num=0,
                        deleted=False,
                        completed=False
                    )
                    a.save()
                    dataset.save()
                    return a.id
            return None

        def getJS(self, request) -> str:
            return ''

    class _SelectionForm(forms.Form):
        """
        Should not be obtained directly, only by:
        MethoManager.getSelectionForm('processing'/'analysis')
        """
        def __init__(self,  parent, methods: Dict, *args, **kwargs):
            self.type = kwargs.pop('type', 'processing')
            if self.type == 'processing':
                label = 'Processing method'
            elif self.type == 'analysis':
                label = 'Analysis method'
            else:
                raise ValueError('Wrong value %s as type in %s' % (self.type, self.__str__()))
            disabled = kwargs.pop('disabled', False)
            super(MethodManager._SelectionForm, self).__init__(*args, **kwargs)
            self.methods = methods
            self.parent = parent
            choices = list(
                zip(
                    [str(k) for k, v in methods.items()],
                    [v.__str__() for k, v in methods.items()]
                )
            )

            defKey = list(self.methods)[0]
            defMethod = self.methods[defKey]

            self.fields['method'] = forms.ChoiceField(
                choices=choices,
                required=True,
                label=label,
                disabled=disabled,
                initial=defKey
            )
            self.fields['method-description'] = forms.CharField(
                widget=forms.Textarea(attrs={'readonly': 'readonly'}),
                required=False,
                initial=defMethod.description,
                label="Description:"
            )

        def getJS(self, request) -> str:
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

        def process(self, user, dataset):
            if self.type == 'processing':
                mname = self.cleaned_data.get('method', None)
                if mname in self.methods:
                    a = mmodels.Processing(
                        owner=user,
                        dataset=dataset,
                        method=mname,
                        method_display_name=self.methods[mname].__str__(),
                        name='',
                        active_step_num=0,
                        deleted=False,
                        completed=False
                    )
                    a.save()
                    dataset.prepareUndo(processingObject=a)
                    return a.id
                return None
            elif self.type == 'analysis':
                mname = self.cleaned_data.get('method', None)
                if mname in self.methods:
                    a = mmodels.Analysis(
                        owner=user,
                        dataset=dataset,
                        method=mname,
                        method_display_name=self.methods[mname].__str__(),
                        name='',
                        active_step_num=0,
                        deleted=False,
                        completed=False
                    )
                    a.save()
                    dataset.save()
                    return a.id
            return None
