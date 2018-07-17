"""
This is default template for processing and analysis methods.
New procedures should extend either AnalysisMethod or
ProcessingMethod.
"""
from typing import Dict, List
from abc import ABC, abstractmethod, abstractclassmethod
import numpy as np
from django.db import transaction
from django.db import DatabaseError
from manager.exceptions import VoltPyFailed
from manager.helpers.functions import add_notification


class Method(ABC):
    """
    These should be implemented by classes providing
    either processing or analysis procedures.
    This class should not be extended, please
    extend either ProcessingMethod or AnalysisMethod.
    The methods should be placed in ./operations/methods
    directory.
    """

    @property
    def _steps(self) -> List[Dict]:
        """
        tuple of dicts:
        Each dict defines what steps have to be taken
        before the method can be applied. The avaiable steps
        should be selected from manager.operations.methodsteps.
        Each dict should have following fields:
            'class': <classObject: class which extends MethodStep>,
            'title': <text: will be displayed on the title bar>,
            'desc': <text: will be displayed as the preamble for the step>,

        Example:

        from manager.operations.methodsteps.selectanalyte import SelectAnalyte
        from manager.operations.methodsteps.selectrange import SelectRange
        ...

        _steps = (
            {
                'class': SelectAnalyte,
                'title': 'Select analyte',
                'desc': 'Select analyte.',
            },
            {
                'class': SelectRange,
                'title': 'Select range',
                'desc': 'Select range containing peak and press Forward, or press Back to change the selection.',
            },
        )
        """
        raise NotImplementedError

    """
    checks described what tests should be made to the dataset in order for procedure
    to be implemented correctly. Please use procedures from manager.operations.checks.
    Use partial implementation of function if you need some parameters to be passed.
    """
    checks = ()
    errors = []

    @property
    def can_be_applied(self) -> bool:
        """
        Describes if after creating the model it can
        be applied to other dataset with apply method.
        """
        raise NotImplementedError

    @property
    def description(self) -> str:
        """
        It is displayed to the user as methods description.
        Please, include references.
        """
        raise NotImplementedError

    step = None
    model = None
    has_next = True
    video = '<iframe width="300" height="200" src="https://www.youtube-nocookie.com/embed/0gEW_BeGP2U?rel=0&amp;ecver=1" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>'

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
        if (self.model.active_step_num + 1) < len(self._steps):
            self.model.active_step_num = self.model.active_step_num + 1
            self.model.save()
            self.step = self._steps[self.model.active_step_num]
            self.__initializeStep()
            return True
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

    def initialForStep(self, step_num: int):
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
                self.step = None
        except VoltPyFailed as e:
            transaction.savepoint_rollback(sid)
            self.model.deleted = True
            self.model.error = str(e)
            self.model.save()
            add_notification(
                request=request,
                text='Processing failed with message: %s' % str(e),
                severity=1
            )
            return
        except:
            transaction.savepoint_rollback(sid)
            raise DatabaseError
        transaction.savepoint_commit(sid)

    def getStepContent(self, user, request) -> Dict:
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
        return {'head': '', 'body': '', 'desc': ''}

    def addToMainPlot(self) -> Dict:
        """
        Requires override.
        Is called to prepare main plot, after adding all elements,
        of Dataset. This should return Dict, and will be passed to
        PlotManager.add() method.
        """
        return None

    @abstractmethod
    def getFinalContent(self, request, user) -> Dict:
        """
        Return content with the final results after the
        analysis if compled. This is not required from
        processing methods.
        Returns {
            'head': ''
            'body': ''
        }
        """
        pass

    @abstractmethod
    def exportableData(self) -> np.matrix:
        """
        This procedure should provide 2d numpy matrix, which
        includes data presented on the anaysis's final plot.
        """
        pass

    @abstractmethod
    def finalize(self, user) -> None:
        """
        This will be used when all defined steps are completed.
        In case of error with the steps it should raise
        VoltPyFailed() and provide explanation.
        """
        pass

    @abstractmethod
    def apply(self, user, dataset):
        """
        This should apply already completed processing/analysis method,
        to the new dataset with the same settings as original.
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

    @classmethod
    def isAnalysis(cls):
        return True


class ProcessingMethod(Method, ABC):
    """
    Should be inherted by classes providing
    data processing procedures.
    """
    @classmethod
    def type(cls):
        return 'processing'

    @classmethod
    def isAnalysis(cls):
        return False

    def exportableData(self):
        return None

    def getFinalContent(self, request, user):
        return None
