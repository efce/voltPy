from abc import ABC, abstractmethod, abstractclassmethod

class Parser(ABC):
    @abstractmethod
    def saveModels(self, user):
        pass
