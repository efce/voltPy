from abc import ABC, abstractmethod, abstractclassmethod
from django.db import transaction
from django.db import DatabaseError
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

    @property
    def _steps(self):
        raise NotImplementedError

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

    def initialForStep(self, step_num):
        """
        This will be passed to step as initial value.
        Override if some initial values are needed.
        """
        return None

    @transaction.atomic
    def process(self, user, request):
        """
        This processes current.active_step_num.
        """
        sid = transaction.savepoint()
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
            raise DatabaseError
        transaction.savepoint_commit(sid)

    def getStepContent(self, user, request):
        """
        Return the content which steps what to display.
        """
        if self.step and self.step.get('object', None):
            stepHTML = self.step['object'].getHTML(
                user=user,
                request=request, 
                model=self.model
            )
            return { 
                #  Step data come form step class, but description comes from method
                'head': stepHTML.get('head', ''),
                'body': stepHTML.get('body', ''),
                'desc': self.step.get('desc', '')
            }
        else:
            return {'head': '', 'body': '', 'desc': ''}

    def addToMainPlot(self):
        """
        Requires override.
        Is called to prepare main plot, after adding all elements,
        of CurveSet. This should return Dict, and will be passed to
        PlotManager.add() method.
        """
        return None

    @abstractmethod
    def getFinalContent(self, request, user):
        """
        Return content with the final results after the
        analysis if compled. This is not required from
        processing methods.
        """
        pass

    @abstractmethod
    def exportableData(self):
        """
        This procedure should provide 2d numpy matrix, which
        includes data presented on the anaysis's final plot.
        """
        pass

    @abstractmethod
    def finalize(self, user):
        """
        This will be used when all defined steps are completed.
        In case of error with the steps it should raise
        VoltPyFailed() and provide explanation.
        """
        pass

    @abstractclassmethod
    def apply(self, user, curveSet):
        """
        This should apply already completed processing/analysis method,
        to the new curveSet with the same settings as original.
        """
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


class AnalysisMethod(Method, ABC):
    """
    Should be inherited by classes providing
    data analysis procedures.
    """
    @classmethod
    def type(cls):
        return 'analysis'


class ProcessingMethod(Method, ABC):
    """
    Should be inherted by classes providing
    data processing procedures.
    """
    @classmethod
    def type(cls):
        return 'processing'

    def exportableData(self):
        return None

    def getFinalContent(self, request, user):
        return None
