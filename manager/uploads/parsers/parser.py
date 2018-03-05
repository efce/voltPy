from abc import ABC, abstractmethod, abstractclassmethod

class Parser(ABC):
    @abstractmethod
    def parse(self, text):
        pass

    @abstractmethod
    def requiredFields(self):
        pass
