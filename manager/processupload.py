import os, sys
import struct
import random
from stat import *
from .curvevolt import CurveVolt
from django.utils import timezone
from .models import *

class ProcessUpload:
    _curves = []
    _ufile = 0
    _fname = ""
    _fcomment = ""
    _user_id = ""

    def __init__(self, user_id, ufile, name, comment):
        self._user_id = user_id
        self._fname = name
        self._fcomment = comment
        self._ufile = ufile

        if ( ufile.name.endswith(".volt") or ufile.name.endswith(".voltc") ):
            self._parseVolt()
            self._createModels()
        
        elif ( ufile.name.endswith(".vol") ):
            self._parseVol()
            self._createModels()
        
        else:
            if ( __debug__ ):
                print("Unknown extension")
    

    def _parseVolt(self):
        fileContent = self._ufile.read();
        index = 0
        curvesNum = struct.unpack('<i', fileContent[index:index+4])[0]
        index += 4
        if ( __debug__ ):
            print("Number of curves in file: %i" % curvesNum)

        for i in range(0, curvesNum):
            curveSize = struct.unpack('I', fileContent[index:index+4])[0]
            index+=4
            c = CurveVolt()
            c.unserialize(fileContent[index:index+curveSize]) 
            self._curves.append(c)
            index+=curveSize-4 # 4 was added earlier

        if ( __debug__ ):
            for v in self._curves:
                print(v.name)


    def _createModels(self):
        try:
            group = Group.objects.get(pk=0)
        except Group.DoesNotExist:
            group = Group(name=random.choice("abcdeBERWdasKI"))
            group.save()
        try: 
            user = User.objects.get(pk=self._user_id)
        except User.DoesNotExist:
            user = User(id=self._user_id, name=random.choice("abcdeBERWdasKI"))
            user.save()
            user.groups.add(group)


        cf = CurveFile(
                owner=user, 
                name=self._fname,
                comment=self._fcomment,
                filename = self._ufile.name,
                fileDate=timezone.now(), 
                uploadDate=timezone.now() )
        cf.save()
        order=0
        for c in self._curves:
            cb = CurveBasic(        
                    curveFile=cf,    
                    orderInFile=order,  
                    name=c.name,  
                    comment=c.comment, 
                    params=c.vec_params, 
                    date=c.getDate() )
            cb.save()

            if ( c.vec_params[60] == 0 ):
                pr = ""
            else:
                pr = c.vec_probing

            cv = CurveVectors(  
                    curve = cb, 
                    date = c.getDate(), 
                    method = 'DPV',
                    time = c.vec_time, 
                    potential = c.vec_potential,
                    current = c.vec_current, 
                    concentration = "",
                    concentrationUnits = "",
                    probingData = pr )
            cv.save()

            ci = CurveIndexing( 
                    curveBasic = cb, 
                    potential_min = min(c.vec_potential), 
                    potential_max = max(c.vec_potential), 
                    potential_step = c.vec_potential[1] - c.vec_potential[0], 
                    time_min = min(c.vec_time), 
                    time_max = max(c.vec_time), 
                    time_step = c.vec_time[1] - c.vec_time[0], 
                    current_min = min(c.vec_current), 
                    current_max = max(c.vec_current), 
                    current_range = max(c.vec_current) - min(c.vec_current), 
                    probingRate = c.vec_params[60] )
            ci.save()
            order+=1


if __name__ == '__main__':
    p = Parse(sys.argv[1])
