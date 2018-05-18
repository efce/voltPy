from abc import ABC, abstractmethod
from typing import Dict


class MethodStep(ABC):
    """
    Use as a template for new MethodSteps,
    MethodStep should update model field:
    model.steps_data[<class name>], with methodstep
    specific values.
    MethodStep should be placed in:
    manager.opperations.methodsteps directory.
    """
    def __init__(self, initial={}):
        self.initial = initial

    @abstractmethod
    def process(self, user, request, model) -> bool:
        """
        Process and verify its results, if user actrivity
        can be save, process should save it and return True.
        False will result in displaying the same step to the user.
        """
        pass

    @abstractmethod
    def getHTML(self, user, request, model) -> Dict:
        """
        Should return the page required to completed the step,
        with any forms necessary included.
        """
        return {'head': '', 'body': ''}

