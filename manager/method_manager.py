import sys
from abc import ABC, abstractmethod
from enum import Enum

class MethodManager:
    """
    MethodManager loads and manages the data processing
    and analysis procedures. Each procedure should be 
    placed in "./methods/" directory and its classname should
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
        selectAnalyte
        selectPoint
        selectRange
        selectTwoRanges
        additionalData
        setConcentrations
        end


    def __init__(self):
        self.__current_step = None
        self.__current_step_number = 0
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


    def setAnalysis(self, analysis):
        self.__selected_method = self.methods['analysis'].get(analysis.method, None)
        self.__selected_method.setModel(analysis)


    def setProcessing(self, processing):
        self.__selected_method = self.methods['processing'].get(processing.method, None)
        self.__selected_method.setModel(processing)


    def process(self, request):
        if self.__selected_method:
            if ( self.__selected_method.processStep(
                        self.__current_step_number,
                        request) ):
                return self.nextStep()
        return False


    def nextStep(self):
        self.__current_step_number += 1
        self.__current_step  = self.__selected_method.nextStep(self.__current_step_number)
        if ( self.__current_step == Step.end ):
            if ( self.__selected_method.type() == 'analysis' ):
                self.__selected_method.finalize()
            elif ( self.__selected_method.type() == 'processing' ):
                self.__selected_method.finalize()
            self.__current_step = None
            self.__current_step_number = 0
            self.__selected_method = None
            return False
        else:
            return True


    def getContent(self):
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
    def setModel(self, model):
        pass


    @abstractmethod
    def nextStep(self, stepNum):
        """
        This provies next step, according to:
        MethodManager.Step enum.
        """
        pass

    @abstractmethod
    def processStep(self, stepNum, data):
        """
        This processes current step.
        """
        pass

    @abstractmethod
    def finalize(self, *args, **kwargs):
        """
        This is the last step of analysis,
        after all steps have been completed
        succssfuly.
        """
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
