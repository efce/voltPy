import sys
from abc import ABC, abstractmethod
from enum import Enum

class MethodManager:

    def __init__(self):
        self.__current_step = None
        self.__selected_method = None
        self.methods = {
                    'processing': dict(), 
                    'analysis': dict() 
                }
        self.loadMethods()

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
                


    def process(self, request):
        #TODO: is success: self.__current_step += 1
        pass


    def nextStep(self):
        methodWants = self.__selected_method.nextStep(self.__current_step)
        if ( methodWants == MethodStep.end ):
            self.__current_step = None
            self.__selectedMethod = None
            return False
        else:
            return True


    def draw(self):
        pass

    def getProcessingMethods(self):
        return MethodManager.methods['processing']

    def getAnalysisMethods(self):
        return MethodManager.methods['analysis']

    def getMethods(self):
        return self.methods


    def register(self,m):
        if str(m) in self.methods[m.type()]:
            raise "Name " + m + " already exists in " + m.type()
        self.methods[m.type()][str(m)] = m
        print(self.methods)


class Method(ABC):
    @abstractmethod
    def nextStep(self, stepNum):
        pass

    @abstractmethod
    def process(self, cal):
        pass

    @abstractmethod
    def askAdditionalData(self, cal):
        pass

    @abstractmethod
    def __str__(self):
        pass

class AnalysisMethod(Method):
    def type(self):
        return 'analysis'

class ProcessingMethod(Method):
    def type(self):
        return 'processing'


class MethodStep(Enum):
    selectPoint = 0
    selectRange = 1
    selectTwoRanges = 2
    askAdditionalData = 3
    setConcentrations = 4
    end = 99


if ( __name__ == '__main__' ):
    mm = MethodManager()
