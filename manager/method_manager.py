from abc import ABC, abstractmethod
from enum import Enum

class MethodManager:
    processing = 0
    analysis = 1
    __methods = ( list(), list() )

    def __init__(self):
        self.selectedMethod = (-1, -1)
        self.__current_step = -1


    def loadMethods(self):
        import os
        dir_path = os.path.dirname(os.path.realpath(__file__))
        from os import listdir
        from os.path import isfile, join
        mypath = dir_path + "/methods/"
        app = self.__module__.split(".")[0]
        onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
        for fm in onlyfiles:
            if not fm == '__init__.py':
                exec('import ' + app + '.methods.' + fm[:-3])

    def loadSession(self, request):
        if request and request.session:
            self.session = request.session.get('MethodManager', None)
            if self.session:
                self.selectedMethod = self.session.get('selectedMethod', (-1,-1))

    def selectMethod(self, typeId, methodId):
        self.selectMethod = (typeId, methodId)
        self.session.set('selectedMethod', self.selectedMethod)


    def setMethod(self, procOrAnal, methodId):
        if ( procOrAnal == 0 ):#Processing
            if methodId >= 0 and methodId < len(MethodManager._MethodManager__methods[0]):
                MethodManager.selectMethod(0, methodId)
            else:
                raise 1
        if ( procOrAnal == 1 ):#Analysis
            if methodId >= 0 and methodId < len(MethodManager._MethodManager__methods[1]):
                MethodManager.selectMethod(1, methodId)
            else:
                raise 1
        else:
            raise 1

    def nextStep(self):
        self.__current_step += 1
        methodWants = MethodManager.methods[MethodManager.selectedMethod].nextStep(self.__current_step)
        if ( methodWants == MethodStep.end ):
            return False
        else:
            self.__current_step = -1
            return True

    def getProcessingMethods(self):
        return MethodManager._MethodManager__methods[0]

    def getAnalysisMethods(self):
        return MethodManager._MethodManager__methods[1]

    @staticmethod
    def register(m):
        if isinstance(m,ProcessingMethod):
            MethodManager._MethodManager__methods[0].append(m)
        elif isinstance(m,AnalysisMethod):
            MethodManager._MethodManager__methods[1].append(m)
        else:
            raise TypeError('Paramter has to inherent either ProcessingMethod or AnalysisMethod class')


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
    pass

class ProcessingMethod(Method):
    pass


class MethodStep(Enum):
    selectPoint = 0
    selectRange = 1
    selectTwoRanges = 2
    askAdditionalData = 3
    setConcentrations = 4
    end = 99


if ( __name__ == '__main__' ):
    mm = MethodManager()
    mm.load()
