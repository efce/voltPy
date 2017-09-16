import sys
from abc import ABC, abstractmethod
from enum import IntEnum
from django.core.urlresolvers import reverse
from django import forms
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.template import loader
from django.core.urlresolvers import reverse
from .models import *
import manager.plotmanager as pm
import json
import manager.views

class MethodManager:
    """
    MethodManager loads and manages the data processing
    and analysis procedures. Each procedure should be 
    placed in "./methods/" directory and its classname should
    match exactly its filename. Also, class should inherit
    either from AnalysisMethod or ProcessingMethod. 
    If procedure meets the requirements it should be immedietly
    avaiable for usage.
    """
    redirect = None # reverse() 
    json_reply = None #

    class Step(IntEnum):
        """ 
        Enum provides available step to perform in case of 
        signals processing or analysis. This should be used by
        any class inheriting from Method.
        """
        selectAnalytes = 0
        selectPoint = 1
        selectRange = 2
        selectTwoRanges = 3
        additionalData = 4 
        setConcentrations = 5
        confirmation = 98
        end = 99

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
                                [ str(x) for x in methods ],
                                methods
                            )
                        )

            self.fields['method'] = forms.ChoiceField(
                    choices=choices,
                    required=True, 
                    label=label,
                    disabled=disabled)

        def process(self, user, curveset):
            if self.type == 'processing':
                if self.cleaned_data.get('method') in self.methods:
                    a = Processing(
                            owner = user,
                            curveSet = curveset,
                            date = timezone.now(),
                            method =self.cleaned_data.get('method'), 
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
                    a = Analysis(
                            owner = user,
                            curveSet = curveset,
                            date = timezone.now(),
                            method = self.cleaned_data.get('method'),
                            name = "",
                            step = 0,
                            deleted = False
                        )
                    a.save()
                    curveset.locked=True #CurveSet cannot be changed when used by Analysis method.
                    curveset.save()
                    return a.id
                else:
                    return None


    def __init__(self, **kwargs):
        print(kwargs)
        self.operations = dict([
            (int(self.Step.selectRange), self.operationSelectRange),
            (int(self.Step.selectPoint), self.operationSelectPoint),
            (int(self.Step.confirmation), self.operationConfirmation),
            #(int(self.Step.selectTwoRanges), self.operationSelectTwoRanges),
            #(int(self.Step.selectAnalytes), self.operationSelectAnalyte),
        ])
        self.methods = {
            'processing': dict(), 
            'analysis': dict() 
        }
        self.__selected_type = None
        self.__selected_method = None
        self.__current_operation = None
        self.__current_step = None
        self.__current_step_number = 0
        self.analysis = None

        self.loadMethods()

        user = kwargs.pop('user', None)
        if ( 'curveset' in kwargs ):
            self.__selected_type = 'other'
            self.curveset_id = int(kwargs.get('curveset', None))
        elif ( 'processing' in kwargs ):
            self.__selected_type = 'processing'
            self.processing_id = int(kwargs.get('processing', None))
            try:
                self.processing = Processing.objects.get(id=self.processing_id)
                self.curveset_id = self.processing.curveSet.id
                self.__setModel(self.processing)
            except:
                raise 404
        elif ( 'analysis' in kwargs ):
            self.__selected_type = 'analysis'
            self.analysis_id = int(kwargs.get('analysis', None))
            try:
                self.analysis = Analysis.objects.get(id=self.analysis_id)
                self.__setModel(self.analysis)
            except:
                raise 404
        elif ( 'method_id' in kwargs and 'method_type' in kwargs ):
            self.__selected_type = kwargs.get('method_type')
            if ( self.__selected_type == 'analysis' ):
                model = Analysis.objects.get(id=int(kwargs['method_id']))
            if ( self.__selected_type == 'processing' ):
                model = Processing.objects.get(id=int(kwargs['method_id']))
            if not self.analysis.canBeUpdatedBy(user):
                raise 3
            self.__setModel(model)
        else:
            raise NameError('Uknown type')


    def loadMethods(self):
        import os
        dir_path = os.path.dirname(os.path.realpath(__file__))
        from os import listdir
        from os.path import isfile, join
        methodspath = dir_path + "/methods/"
        onlyfiles = [f for f in listdir(methodspath) if isfile(join(methodspath, f))  and
            f.endswith('.py')]
        sys.path.append(methodspath)
        for fm in onlyfiles:
            if not fm == '__init__.py':
                fname = fm[:-3]
                fimp = __import__(fname)
                methodInstance = fimp.newInstance()
                self.register(methodInstance)

    def __setModel(self, model):
        print('mm setting model')
        self.__selected_method = self.methods[self.__selected_type].get(model.method, None)
        self.__selected_method.setModel(model)
        self.__current_step_number = model.step
        self.__current_step = self.__selected_method.getStep(self.__current_step_number)
        if ( __debug__ ):
            print(self.__current_step)
        if ( self.__current_step['step'] == self.Step.end ):
            self.__current_operation = None
        else:
            self.__current_operation = self.operations[self.__current_step['step']]()


    def process(self, request, user):
        if ( request.method != 'POST' ):
            return
        if self.__selected_method and self.__current_operation:
            command = request.POST.get('command', None)
            val = None
            cursor_names = [ 'cursor1', 'cursor2', 'cursor3', 'cursor4' ]
            non_null_cursors = []
            for cn in cursor_names:
                wrk = request.POST.get(cn, None)
                if not wrk:
                    continue
                try:
                    wrk = float(wrk)
                except ValueError:
                    continue
                non_null_cursors.append(wrk)

            print(non_null_cursors)

            if ( command == 'set1cursor' ):
                if ( len(non_null_cursors)<0 ):
                    raise ValueError('Wrong number of cursors')
                val = non_null_cursors[0]
            elif ( command == 'set2cursors' ):
                if ( len(non_null_cursors)<2 ):
                    raise ValueError('Wrong number of cursors')
                val = [ min(non_null_cursors), max(non_null_cursors) ]
            elif ( command == 'set4cursors' ):
                if ( len(non_null_cursors)<4 ):
                    raise ValueError('Wrong number of cursors')
                non_null_cursors.sort()
                val = non_null_cursors
            elif ( command == 'cancel' ):
                val = False
            elif ( command == 'confirm' ):
                val = True
            else:
                ValueError('Unknown command')

            result,self.json_reply = self.__current_operation.process(
                model = self.__selected_method.model,
                data = val
            )
            if result:
                stepCompleted = self.__selected_method.processStep(
                    user,
                    self.__current_step_number
                ) 
                if ( stepCompleted ):
                    self.nextStep(user)
            else:
                self.nextStep(user)
        else:
            print('not selected method or no current operation')


    def nextStep(self, user):
        if self.__selected_method:
            self.__current_step_number += 1
            self.__current_step  = self.__selected_method.getStep(self.__current_step_number)
            if not self.__current_step \
            or ( self.__current_step['step'] == self.Step.end ):
                self.__selected_method.finalize()
                if self.__selected_method.type() == 'analysis':
                    self.redirect = reverse( 
                        'showAnalysis',
                         args=[ user.id, self.__selected_method.model.id ]
                    )
                elif self.__selected_method.type() == 'processing':
                    self.redirect = reverse( 
                        'showCurveSet',
                         args=[ user.id, self.__selected_method.model.curveSet.id ]
                    )
                self.__current_step = None
                self.__current_step_number = 0
                self.__selected_method = None
                self.__current_operation = None
            else:
                self.__current_operation = self.operations[self.__current_step['step']]()


    def getJSON(self):
        if self.redirect:
            return { 'command': 'redirect', 'location': self.redirect }
        elif self.json_reply:
            return self.json_reply
        else:
            return { 'command': 'none' }


    def getContent(self, request, user):
        if self.redirect:
            return HttpResponseRedirect( self.redirect )
        elif not self.isMethodSelected():
            return HttpResponseRedirect( reverse("browseCurveSet") )

        operationText = dict( 
            head= '', 
            body= "No operation"
        )
        if self.__current_operation:
            operationText = self.__current_operation.draw(self.__current_step)
        if self.__selected_type == 'analysis':
            plotScr, plotDiv = manager.views.generatePlot(
                request=request, 
                user=user, 
                plot_type='curveset',
                value_id=self.analysis.curveSet.id,
                vtype='analysis',
                vid=self.analysis.id,
                interactionName = self.__current_operation.interactionName,
            )
            template = loader.get_template('manager/analyze.html')
            context = {
                'scripts': '\n'.join( [   
                                    plotScr, 
                                    pm.PlotManager.required_scripts, 
                                    operationText.get('head','')
                                ]),
                'mainPlot': plotDiv,
                'analyze_content': operationText.get("body",''),
                'user': user,
                'analysis_id': self.analysis.id,
                'curveset_id': self.analysis.curveSet.id,
                'plot_width' : pm.PlotManager.plot_width,
                'plot_height' : pm.PlotManager.plot_height
            }
            return HttpResponse(template.render(context))
        else:
            return ''

    def getAnalysisSelectionForm(self, *args, **kwargs):
        return MethodManager.SelectionForm(
            self, 
            self.methods['analysis'],
            type='analysis', 
            *args, 
            **kwargs
        )

    def getProcessingSelectionForm(self, *args, **kwargs):
        return MethodManager.SelectionForm(
            self, 
            self.methods['processing'],
            type='processing', 
            *args, 
            **kwargs
        )

    def getInfo(self, request, user):
        return self.__selected_method.printInfo(request=request, user=user)


    def register(self,m):
        if str(m) == self.methods[m.type()]:
            raise NameError("Name " + str(m) + " already exists in " + m.type())
        self.methods[m.type()][str(m)] = m

    def isMethodSelected(self):
        return (self.__selected_method != None)


    class operationSelectRange:
        interactionName = 'set2cursors'
        def setData(self, data, request):
            pass

        def draw(self, step):
            return dict( 
                head = '', 
                body = step.get('data').get('desc','')
            )

        def process(self, model, data):
            if (len(data) == 2):
                model.customData['range1'] = data
                model.save()
                return True,{'command', 'reload'}
            else:
                return False,None

    class operationSelectPoint:
        interactionName = 'set1cursor'
        def setData(self, data, request):
            pass

        def draw(self, step):
            return dict( 
                head = '', 
                body = step.get('data').get('desc','')
            )

        def process(self, model, data):
            if isinstance(data, float):
                model.customData['pointX'] = data
                model.save()
                return True,None
            else:
                return False,None


    class operationConfirmation:
        interactionName = 'confirm'

        def setData(self, data, request):
            pass

        def draw(self, step):
            return dict( 
                head = '', 
                body = step.get('data').get('desc','')
            )

        def process(self, model, data):
            if data:
                return True,{'command': 'reload'}
            else:
                model.step = model.step-1
                model.save()
                return False,{'command', 'reload'}


class Method(ABC):
    """
    These should be implemented by classes providing
    either processing or analysis procedures.
    """
    model = None

    def setModel(self, model):
        self.model = model

    @abstractmethod
    def getStep(self, stepNum):
        """
        Return selected step, according to:
        MethodManager.Step enum.
        """
        pass

    @abstractmethod
    def processStep(self, stepNum):
        """
        This processes current step.
        """
        pass

    @abstractmethod
    def finalize(self, *args, **kwargs):
        """
        This is the last step of analysis,
        after all steps have been completed
        succssfuly.
        """
        pass

    @abstractmethod
    def printInfo(self, user):
        pass

    @abstractmethod
    def __str__(self):
        pass

    def __repr__(self):
        """
        This should not be reimplemented.
        """
        return self.__str__().replace(" ","")


class AnalysisMethod(Method):
    """
    Should be inherited by classes providing 
    data analysis procedures.
    """
    def type(self):
        return 'analysis'


class ProcessingMethod(Method):
    """
    Should be inherted by classes providing
    data processing procedures.
    """
    def type(self):
        return 'processing'


if ( __name__ == '__main__' ):
    mm = MethodManager()
