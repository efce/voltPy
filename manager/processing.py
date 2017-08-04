from numpy import polyfit, corrcoef

class Processing:

    def standardCalibration(self, cal):
        data = cal.dataMatrix
        if not data:
            return
        p = polyfit(data['x'], data['y'], 1)
        cal.method = "normal"
        cal.fitEquation = '%f*x+%f' % (p[0],p[1])
        cal.result = p[1]/p[0]
        cal.complete = True
        cal.corrCoeff = corrcoef(data['x'], data['y'])[0,1]
        cal.save()


    def slopeStandardAddition(self, cal):
        pass


    def selfReferencing(self,cal):
        pass
