from abc import ABC, abstractmethod, abstractclassmethod
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
import manager.models as mmodels

class Method(ABC):
    """
    These should be implemented by classes providing
    either processing or analysis procedures.
    """
    step = None
    model = None
    has_next = True
    description = None
    
    def __init__(self, model):
        if not model:
            raise ValueError('Model has to be set')
        self.model = model
        if model.active_step_num is not None:
            if model.active_step_num >= 0 and model.active_step_num < len(self._steps):
                self.step = self._steps[model.active_step_num]
                self.__initializeStep()
            else:
                self.has_next = False
        else:
            self.has_next = False


    def __initializeStep(self):
        if self.step['class'] is not None:
            self.step['object'] = self.step['class'](
                initial=self.initialForStep(self.model.active_step_num)
            )
        else:
            self.step['object'] = None

    def __nextStep(self):
        if (self.model.active_step_num+1) < len(self._steps):
            self.model.active_step_num = self.model.active_step_num + 1
            self.model.save()
            self.step = self._steps[self.model.active_step_num]
            self.__initializeStep()
            return True
        else:
            return False

    def __prevStep(self):
        self.model.active_step_num = self.model.active_step_num - 1
        self.model.save()
        if self.model.active_step_num < 0:
            self.step = None
            self.model.deleted = True
            self.model.save()
        else:
            self.step = self._steps[self.model.active_step_num]
            self.__initializeStep()

    """ 
    This will be passed to step as initial value.
    Override if some initial values are needed.
    """
    def initialForStep(self, step_num):
        return None

    @transaction.atomic
    def process(self, user, request):
        """
        This processes current.active_step_num.
        """
        sid=transaction.savepoint()
        try:
            isBack = request.POST.get('_voltJS_backButton', 0) 
            if isBack != 0:
                self.__prevStep()
                return

            isBack = request.POST.get('_voltJS_backButton', 0) 
            if self.step is None or self.step['object'] is None:
                self.has_next = False
            elif self.step['object'].process(user=user, request=request, model=self.model):
                self.has_next = self.__nextStep()

            if not self.has_next:
                self.finalize(user)
                self.model.active_step_num = None
                self.model.completed = True
                self.model.save()
                if isinstance(self.model, mmodels.Processing):
                    for cd in self.model.curveSet.curvesData.all():
                        cd.processedWith = self.model
                        cd.save()
                self.step = None
        except:
            transaction.savepoint_rollback(sid)
            raise
        transaction.savepoint_commit(sid)

    def getStepHTML(self, user, request):
        if self.step and self.step.get('object', None):
            stepHTML = self.step['object'].getHTML(
                user=user,
                request=request, 
                model=self.model
            )
            return { 
            #Step data come form step class, but description comes from method
                'head': stepHTML.get('head',''), 
                'body': stepHTML.get('body',''), 
                'desc': self.step.get('desc','')
            }
        else:
            return { 'head': '', 'body': '' , 'desc': ''}

    def getAddToPlot(self):
        return None

    @abstractmethod
    def getInfo(self, request, user):
        pass

    @abstractmethod
    def finalize(self, user):
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

    def exportCSV(self):
        pass


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

