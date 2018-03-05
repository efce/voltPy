from abc import ABC, abstractmethod, abstractclassmethod

class Parser(ABC):
    @abstractmethod
    def models(self):
        pass
