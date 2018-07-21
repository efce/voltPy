from abc import ABC, abstractmethod
from typing import Dict, Any
from django.contrib.auth.models import User
from django.http.request import HttpRequest


class MethodStep(ABC):
    """
    Use as a template for new MethodStep,
    MethodStep should update model field:
    model.steps_data[<class name>], with methodstep
    specific values (it can be list dict or single value).
    New MethodStep should be placed in:
    manager.opperations.methodsteps directory.
    If the step requires some precofiguration it will
    be passed via initial: Dict value in constructor.
    """
    def __init__(self, initial: Dict={}):
        self.initial = initial

    @property
    def plot_interaction(self) -> str:
        """
        Sets the type of interaction with the main_plot,
        for available options please see PlotManager.
        """
        raise NotImplementedError

    @classmethod
    def getData(cls, method_instance) -> Any:
        """
        This should probably remain unchanged. It returns the saved data of the method step.
        """
        return method_instance.model.steps_data.get(cls.__name__, None)

    @abstractmethod
    def process(self, user: User, request: HttpRequest, model) -> bool:
        """
        Process and verify its results, if user activity
        can be saved, process should save it and return True.
        False will result in displaying the same step to the user.
        """
        pass

    @abstractmethod
    def getHTML(self, user: User, request: HttpRequest, model) -> Dict:
        """
        Should return the html content required to completed the step,
        with any forms necessary included.
        """
        return {'head': '', 'body': ''}
