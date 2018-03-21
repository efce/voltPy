from abc import ABC, abstractmethod, abstractclassmethod

class MethodStep(ABC):
    def __init__(self, initial={}):
        self.initial = initial

    @abstractmethod
    def process(self, user, request, model):
        pass

    def getHTML(self, user, request, model):
        return { 'head': '', 'body' : '' }

