from numpy import polyfit

class Processing:
    def standardCalibration(self, cal):
        data = cal.dataMatrix
        p,covmat = polyfit(data['x'], data['y'], 1, cov=True)
        cal.method = "normal"
        cal.fitEquation = '%f*x+%f' % (p[0],p[1])
        cal.result = p[1]/p[0]
        cal.complete = True
        cal.corrCoeff = covmat[0,1]
        cal.save()
