import sys
from abc import ABC, abstractmethod
from enum import Enum

class MethodManager:
    """
    MethodManager loads and manages the data processing
    and analysis procedures. Each procedure should be 
    placed in "./methods/" directory and its name should
    match exactly its filename. Also, class should inherit
    either from AnalysisMethod or ProcessingMethod. 
    If procedure meets the requirements it should be immedietly
    avaiable for usage.
    """
    class Step(Enum):
        """ 
        Enum provides available step to perform in case of 
        signals processing or analysis. This should be used by
        any class inheriting from Method.
        """
        selectPoint = 0
        selectRange = 1
        selectTwoRanges = 2
        askAdditionalData = 3
        setConcentrations = 4
        end = 99


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


    def selectAnalysis(self, name):
        self.__selected_method = self.methods['analysis'].get(name, None)


    def selectProcessing(self, name):
        self.__selected_method = self.methods['processing'].get(name, None)


    def process(self, request):
        #TODO: is success: self.__current_step += 1
        pass


    def nextStep(self):
        self.__current_step  = self.__selected_method.nextStep(self.__current_step)
        if ( self.__current_step == Step.end ):
            self.__current_step = None
            self.__selected_method = None
            return False
        else:
            return True


    def draw(self):
        pass

    def getProcessingMethods(self):
        return self.methods['processing']

    def getAnalysisMethods(self):
        return self.methods['analysis']

    def getMethods(self):
        return self.methods


    def register(self,m):
        if str(m) == self.methods[m.type()]:
            raise TypeError("Name " + str(m) + " already exists in " +
                    m.type())
        self.methods[m.type()][str(m)] = m
        print(self.methods)


    def isMethodSelected(self):
        return (self.__selected_method != None)



class Method(ABC):
    """
    These should be implemented by classes providing
    either processing or analysis procedures.
    """
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

    def __repr__(self):
        """
        This should not be reimplemented.
        """
        return self.__str__().replace(" ","")


class AnalysisMethod(Method):
    """
    Should be inherited by classes providing 
    data analysis procedures.
    """
    def type(self):
        return 'analysis'


class ProcessingMethod(Method):
    """
    Should be inherted by classes providing
    data processing procedures.
    """
    def type(self):
        return 'processing'


if ( __name__ == '__main__' ):
    mm = MethodManager()
