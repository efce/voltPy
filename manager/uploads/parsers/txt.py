import struct
import datetime
import struct
import pandas as pd
import numpy as np
import datetime
import manager.models as mmodels
from manager.uploads.parser import Parser
from manager.uploads.generic_eaqt import Param

class Txt(Parser):

    class CurveFromFile():
        name =''
        comment = ''
        vec_param = [0] * Param.PARAMNUM
        vec_time = []
        vec_potential = []
        vec_current = []
        vec_samples = []
        date = ''

    def __init__(self, cfile, details):
        # Details not needed - ignore
        self.params = []
        self.names = []
        self._curves = []
        self.cfile = cfile
        skipRows = int(details.get('skipRows', 0))
        pdfile = pd.read_csv(self.cfile, sep='\s+', header=None, skiprows=skipRows)
        #if details.get('isSampling', False) == False:
        potential = []
        index = 0
        if details.get('firstIsE', False) == False:
            potential = pdfile[0]
            index = 1
        else:
            potential = [ i for i in range(len(pdfile[0])) ]
        time = [ i for i in range(len(pdfile[0])) ]
        for i in range(len(pdfile.columns)-index):
            ci = index + i
            c = self.CurveFromFile()
            c.name = str(i)
            c.vec_potential = potential
            c.vec_current = pdfile[ci]
            c.vec_time = time
            c.date = datetime.datetime.now()
            self._curves.append(c)


    def saveModels(self, user):
        cf = mmodels.CurveFile(
            owner=user, 
            name=self.cfile.name,
            fileName=self.cfile.name,
            fileDate=self._curves[0].date
        )
        cs = mmodels.CurveSet(
            owner=user,
            name="",
            locked=False,
        )
        cs.save()
        cf.curveSet = cs
        cf.save()

        self._file_id = cf.id
        order=0
        for c in self._curves:
            cb = mmodels.Curve(        
                curveFile=cf,    
                orderInFile=order,  
                name=c.name,  
                comment=c.comment, 
                params=c.vec_param, 
                date=c.date 
            )
            cb.save()

            cd = mmodels.CurveData(
                curve = cb, 
                date = c.date,
                processing = None,
                time = c.vec_time, 
                potential = c.vec_potential,
                current = c.vec_current, 
            )
            cd.save()
            cs.curvesData.add(cd)

            ci = mmodels.CurveIndex( 
                curve = cb, 
                potential_min = np.min(c.vec_potential), 
                potential_max = np.max(c.vec_potential), 
                potential_step = c.vec_potential[1] - c.vec_potential[0], 
                time_min = np.min(c.vec_time), 
                time_max = np.max(c.vec_time), 
                time_step = c.vec_time[1] - c.vec_time[0], 
                current_min = np.min(c.vec_current), 
                current_max = np.max(c.vec_current), 
                current_range = np.max(c.vec_current) - np.min(c.vec_current), 
                samplingRate = 0
            )
            ci.save()
            order+=1

        cs.save()
        return cf.id
