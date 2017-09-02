import sys
from abc import ABC, abstractmethod
from enum import IntEnum
from django.core.urlresolvers import reverse

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
    redirect = '' # reverse() 


    class Step(IntEnum):
        """ 
        Enum provides available step to perform in case of 
        signals processing or analysis. This should be used by
        any class inheriting from Method.
        """
        selectAnalytes = 0
        selectPoint = 1
        selectRange = 2
        selectTwoRanges = 3
        additionalData = 4 
        setConcentrations = 5
        end = 99


    def __init__(self):
        self.__current_step = None
        self.__current_step_number = 0
        self.__selected_method = None
        self.__selected_type = None
        self.methods = {
                    'processing': dict(), 
                    'analysis': dict() 
                }
        self.loadMethods()
        self.operations = dict([
                    (int(self.Step.selectRange), self.operationSelectRange),
                    (int(self.Step.selectPoint), self.operationSelectPoint),
                    #(int(self.Step.selectTwoRanges), self.operationSelectTwoRanges),
                    #(int(self.Step.selectAnalytes), self.operationSelectAnalyte),
                ])
        self.__current_operation = None


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


    def setAnalysis(self, model):
        self.__selected_type = 'analysis'
        self.__setModel(model)


    def setProcessing(self, model):
        self.__selected_type = 'processing'
        self.__setModel(model)


    def __setModel(self, model):
        self.__selected_method = self.methods[self.__selected_type].get(model.method, None)
        self.__selected_method.setModel(model)
        self.__current_step_number = model.step
        self.__current_step = self.__selected_method.getStep(self.__current_step_number)
        if ( __debug__ ):
            print(self.__current_step)
        if ( self.__current_step['step'] == self.Step.end ):
            self.__current_operation = None
        else:
            self.__current_operation = self.operations[self.__current_step['step']]()


    def process(self, user, request):
        self.request = request
        if self.__current_operation:
            self.__current_operation.setData(
                    self.__current_step['data'],
                    request)
            if self.__current_operation.is_valid():
                if ( self.__selected_method.processStep(
                            user,
                            self.__current_step_number,
                            self.__current_operation.process()) ):
                    self.nextStep(user)
        else:
            self.nextStep(user)


    def nextStep(self, user):
        self.__current_step_number += 1
        self.__current_step  = self.__selected_method.getStep(self.__current_step_number)

        if not self.__current_step \
        or ( self.__current_step['step'] == self.Step.end ):
            self.__selected_method.finalize()
            if self.__selected_method.type() == 'analysis':
                self.redirect = reverse( 
                                    'showAnalysis',
                                     args=[ user.id,
                                         self.__selected_method.model.id ]
                                    )
            elif self.__selected_method.type() == 'processing':
                self.redirect = reverse( 
                                    'showCurveSet',
                                     args=[ 
                                         user.id,
                                         self.__selected_method.model.curveSet.id 
                                        ]
                                    )
            self.__current_step = None
            self.__current_step_number = 0
            self.__selected_method = None
            self.__current_operation = None
        else:
            self.__current_operation = self.opetations[self.__current_step['step']]()


    def getContent(self):
        if self.__current_operation:
            return self.__current_operation.draw()
        else:
            return "No operation"


    def getProcessingMethods(self):
        return self.methods['processing']


    def getAnalysisMethods(self):
        return self.methods['analysis']


    def getMethods(self):
        return self.methods


    def drawSelectPoint(self):
        pass

    def drawSelectAnalyte(self):
        pass


    def drawEnd(self):
        pass


    def getInfo(self):
        return self.__selected_method.printInfo()


    def register(self,m):
        if str(m) == self.methods[m.type()]:
            raise TypeError("Name " + str(m) + " already exists in " +
                    m.type())
        self.methods[m.type()][str(m)] = m

    def isMethodSelected(self):
        return (self.__selected_method != None)


    class operationSelectRange:
        def setData(self, data, request):
            from manager.forms import SelectRange
            self.request = request
            self.data = data
            if request and request.POST:
                self.form = SelectRange(self.data.get('starting',(0,0)), request.POST)
            else:
                self.form = SelectRange(self.data.get('starting',(0,0)))


        def draw(self):
            from manager.forms import SelectRange
            from django.template import loader
            from django.middleware import csrf
            template = loader.get_template("manager/analyzeForm.html")
            context = {
                    'desc': self.data.get('desc',""),
                    'form': self.form,
                    'csrftoken': csrf.get_token(self.request) 
                    }
            return template.render(context)


        def is_valid(self):
            return self.form.is_valid()


        def process(self):
            return { 'range1': self.form.process() }


    class operationSelectPoint:
        def setData(self, data, request):
            from manager.forms import SelectPoint
            self.request = request
            self.data = data
            if request and request.POST:
                self.form = SelectPoint(self.data.get('starting',0), request.POST)
            else:
                self.form = SelectPoint(self.data.get('starting',0))


        def draw(self):
            from manager.forms import SelectPoint
            from django.template import loader
            from django.middleware import csrf
            template = loader.get_template("manager/analyzeForm.html")
            context = {
                    'desc': self.data.get('desc',""),
                    'form': self.form,
                    'csrftoken': csrf.get_token(self.request) 
                    }
            return template.render(context)


        def is_valid(self):
            return self.form.is_valid()


        def process(self):
            return { 'point': self.form.process() }



class Method(ABC):
    """
    These should be implemented by classes providing
    either processing or analysis procedures.
    """
    model = None

    def setModel(self, model):
        self.model = model


    @abstractmethod
    def getStep(self, stepNum):
        """
        Return selected step, according to:
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
    def printInfo(self):
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
