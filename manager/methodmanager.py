import sys
import os
from abc import ABC, abstractmethod, abstractclassmethod
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.utils import timezone
from django import forms
import manager.models as mmodels
import manager.plotmanager as pm
from manager.helpers.functions import generate_plot
from manager.helpers.functions import voltpy_render

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

        if ( 'curveset_id' in kwargs ):
            self.__type = 'other'
            self.__curveset_id = int(kwargs.get('curveset_id', None))
            return
        elif ( 'processing_id' in kwargs  or 'processing' in kwargs ):
            self.__type = 'processing'
            _id = int(kwargs.get('processing_id', kwargs.get('processing')))
            try:
                self.__model = mmodels.Processing.objects.get(id=_id)
                self.__curveset_id = self.__model.curveSet.id
            except ObjectDoesNotExist:
                raise 404
        elif ( 'analysis_id' in kwargs or 'analysis' in kwargs ):
            self.__type = 'analysis'
            _id = int(kwargs.get('analysis_id', kwargs.get('analysis')))
            try:
                self.__model = mmodels.Analysis.objects.get(id=_id)
            except ObjectDoesNotExist:
                raise 404
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

    def __registerMethod(self,mclass):
        if str(mclass.__name__) == self.methods[mclass.type()]:
            raise NameError("Name " + repr(mclass) + " already exists in " + mclass.type())
        self.methods[mclass.type()][str(mclass.__name__)] = mclass

    def __activateMethod(self):
        mclass = self.methods[self.__type].get(self.__model.method, None)
        if mclass:
            self.__method = mclass(self.__model)

    def process(self, request, user):
        if ( request.method != 'POST' 
        or request.POST.get('query') != 'methodmanager' ):
            return
        if self.__method:
            self.__method.process(user=user,request=request)

    def getJSON(self, user):
        if not self.__method.has_next:
            return { 'command': 'redirect', 'location': self.__model.getRedirectURL(user)  }
        else:
            return { 'command': 'reload' }

    def getContent(self, request, user):
        if self.__method.has_next == False or self.__method.operation is None:
            return HttpResponseRedirect(self.__model.getRedirectURL(user))
        elif not self.isMethodSelected():
            return HttpResponseRedirect(reverse("browseCurveSet"))

        operationText = dict( 
            head= '', 
            body= "No text"
        )

        if self.__method.operation:
            operationText = self.__method.getOperationHTML(
                user=user,
                request=request
            )

            plotScr, plotDiv = generate_plot(
                request=request, 
                user=user, 
                plot_type='curveset',
                value_id=self.__model.curveSet.id,
                vtype=self.__method.type(),
                vid=self.__model.id,
                interactionName = self.__method.operation['class'].plot_interaction,
                add = self.__method.getAddToPlot()
            )

            context = {
                'scripts': '\n'.join([ 
                                        plotScr, 
                                        operationText.get('head','') 
                                    ]),
                'mainPlot': plotDiv,
                'method_content': ''.join([
                                        operationText.get('desc',''),
                                        operationText.get('body',''),
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
        return (self.__method != None)

    class SelectionForm(forms.Form):
        """
        Should not be obtained directly, only by:
        MethoManager.getSelectionForm('processing'/'analysis')
        """
        def __init__(self,  parent, methods, *args, **kwargs):
            self.type = kwargs.pop('type', 'processing')
            if ( self.type == 'processing' ):
                label = "Processing method"
            elif (self.type == 'analysis' ):
                label = 'Analysis method'
            disabled = kwargs.pop('disabled', False)
            super(MethodManager.SelectionForm, self).__init__(*args, **kwargs)
            self.methods = methods
            self.parent = parent
            choices = list(
                zip(
                    [ str(k) for k,v in methods.items() ],
                    [ v.__str__() for k,v in methods.items() ]
                )
            )

            self.fields['method'] = forms.ChoiceField(
                choices=choices,
                required=True, 
                label=label,
                disabled=disabled
            )
            self.fields['method-description'] = forms.CharField(
                widget=forms.Textarea(attrs={'readonly':'readonly'}),
                required=False,
                initial=self.methods[list(self.methods)[0]].description,
                label="Description:"
            )

        def getJS(self, request):
            import json
            js_dict = json.dumps(
                dict(
                    zip(
                        [ str(k) for k,v in self.methods.items() ],
                        [ v.description for k,v in self.methods.items() ],
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
                        owner = user,
                        curveSet = curveset,
                        method = self.cleaned_data.get('method'), 
                        name = "",
                        step = 0,
                        deleted = False,
                        completed = False
                    )
                    a.save()
                    return a.id
                else:
                    return None
            elif self.type == 'analysis':
                if self.cleaned_data.get('method') in self.methods:
                    a = mmodels.Analysis(
                        owner = user,
                        curveSet = curveset,
                        method = self.cleaned_data.get('method'),
                        name = "",
                        step = 0,
                        deleted = False,
                        completed = False
                    )
                    a.save()
                    curveset.locked=True #CurveSet cannot be changed when used by Analysis method.
                    curveset.save()
                    return a.id
                else:
                    return None

class Method(ABC):
    """
    These should be implemented by classes providing
    either processing or analysis procedures.
    """
    operation = None
    model = None
    has_next = True
    description = None

    def __init__(self, model):
        if not model:
            raise ValueError('Model has to be set')
        self.model = model
        if model.step is not None:
            if ( model.step < len(self._operations) ):
                self.operation = self._operations[model.step]
                if self.operation['class'] is not None:
                    self.operation['object'] = self.operation['class']()
                else:
                    self.operation['object'] = None
            else:
                self.has_next = False
        else:
            self.has_next = False

    def __nextOperation(self):
        if (self.model.step+1) < len(self._operations):
            self.model.step = self.model.step + 1
            self.model.save()
            self.operation = self._operations[self.model.step]
            if self.operation['class'] is not None:
                self.operation['object'] = self.operation['class']()
            else:
                self.operation['object'] = None
            return True
        else:
            return False

    def process(self, user, request):
        """
        This processes current step.
        """
        if self.operation is None or self.operation['object'] is None:
            self.has_next = False
        elif self.operation['object'].process(user=user, request=request, model=self.model):
            self.has_next = self.__nextOperation()

        if not self.has_next:
            self.finalize(user)
            self.model.step = None
            self.model.completed = True
            self.model.save()
            self.operation = None

    def getOperationHTML(self, user, request):
        if self.operation and self.operation.get('object', None):
            opHTML = self.operation['object'].getHTML(
                user=user,
                request=request, 
                model=self.model
            )
            return { 
                'head': opHTML.get('head',''), 
                'body': opHTML.get('body',''), 
                'desc': self.operation.get('desc','')
            }
        else:
            return { 'head': '', 'body': '' , 'desc': ''}

    def getAddToPlot(self):
        return None

    @abstractmethod
    def getInfo(self, request, user):
        pass

    @abstractclassmethod
    def __str__(cls):
        """
        This is displayed to user as name of method
        """
        pass

    def __repr__(self):
        """
        This should not be reimplemented.
        """
        return self.__class__.__name__


class AnalysisMethod(Method):
    """
    Should be inherited by classes providing 
    data analysis procedures.
    """
    @classmethod
    def type(self):
        return 'analysis'

class ProcessingMethod(Method):
    """
    Should be inherted by classes providing
    data processing procedures.
    """
    @classmethod
    def type(self):
        return 'processing'

class Operation(ABC):
    @abstractmethod
    def process(self, user, request, model):
        pass

    def getHTML(self, user, request, model):
        return { 'head': '', 'body' : '' }

class OperationSelectTwoRanges(Operation):
    plot_interaction = 'set4cursors'

    def process(self, user, request, model):
        data = []
        for cnum in range(1,5):
            name = 'cursor' + str(cnum)
            if request.POST.get(name,''):
                try:
                    data.append(float(request.POST.get(name)))
                except ValueError:
                    continue
        if (len(data) == 4):
            model.customData['range1'] = [data[0], data[1]]
            model.customData['range2'] = [data[2], data[3]]
            model.save()
            return True
        return False

class OperationSelectRange(Operation):
    plot_interaction = 'set2cursors'

    def process(self, user, request, model):
        data = []
        for cnum in range(1,5):
            name = 'cursor' + str(cnum)
            if request.POST.get(name,''):
                try:
                    data.append(float(request.POST.get(name)))
                except ValueError:
                    continue
        if (len(data) == 2):
            model.customData['range1'] = data
            model.save()
            return True
        return False

class OperationSelectPoint(Operation):
    plot_interaction = 'set1cursor'

    def process(self, user, request, model):
        data = []
        for cnum in range(1,5):
            name = 'cursor' + str(cnum)
            if request.POST.get(name,''):
                try:
                    data.append(float(request.POST.get(name)))
                except ValueError:
                    continue
        if ( len(data) > 0 ):
            model.customData['pointX'] = data[0]
            model.save()
            return True
        return False

class OperationConfirmation(Operation):
    plot_interaction = 'confirm'

    def process(self, user, request, model):
        if request.POST.get('command', False) == 'confirm':
            return True
        else:
            model.step = model.step-1
            model.save()
            return False

class OperationSelectAnalyte(Operation):
    plot_interaction = 'none'

    class AnalyteSelectionForm(forms.Form):
        def __init__(self, *args, **kwargs):
            analytes = kwargs.pop('analytes',[])
            super(OperationSelectAnalyte.AnalyteSelectionForm, self).__init__(*args, **kwargs)
            choices = zip(
                [-1] + [ x.id for x in analytes ],
                ['Select'] + [ x.name for x in analytes ]
            )
            self.fields['analyteId'] = forms.ChoiceField(
                choices=choices,
                initial=-1,
                label='Analyte'
            )
            self.fields['analyteId'].widget.attrs['class'] = 'atChanger'

    def getHTML(self, user, request, model):
        cs = model.curveSet
        analytes = set()
        for cd in cs.usedCurveData.all():
            aics = mmodels.AnalyteInCurve.objects.filter(curve=cd.curve)
            for aic in aics:
                analytes.add(aic.analyte)

        style = "<style>.atOther { display: none; };</style>"
        import manager.analytesTable as at
        at_disp = at.analytesTable(user, cs)

        analyte_sel = self.AnalyteSelectionForm(analytes=analytes)
        from django.template import loader
        template = loader.get_template('manager/form.html')
        context = { 'form': analyte_sel, 'submit': 'selectAnalyte' }
        analyte_sel_disp = template.render(
            context=context,
            request=request
        )
        txt = """
        {0}
        <br />
        Data preview:<br />
        {1}
        """.format(analyte_sel_disp, at_disp)
        return { 'head': style, 'desc': '', 'body': txt }

    def process(self, user, request, model):
        cs = model.curveSet
        analytes = set()
        for cd in cs.usedCurveData.all():
            aics = mmodels.AnalyteInCurve.objects.filter(curve=cd.curve)
            for aic in aics:
                analytes.add(aic.analyte)

        analyte_sel = self.AnalyteSelectionForm(request.POST, analytes=analytes)
        if analyte_sel.is_valid():
            data = model.customData.get('analytes', [])
            try:
                analyte = mmodels.Analyte.objects.get(id=analyte_sel.cleaned_data['analyteId'])
            except ObjectDoesNotExist:
                return False
            data.append(analyte.id)
            model.customData['analytes'] = data
            model.save()
            return True
        else:
            return False

if ( __name__ == '__main__' ):
    mm = MethodManager()
