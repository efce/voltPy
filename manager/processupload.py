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
                print(v.getName())


    def _createModels(self):
        try:
            group = Group.objects.get(pk=3)
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
                    name=c.getName(),  
                    comment=c.getComment(), 
                    params=c.getParams(), 
                    date=c.getDate() )
            cb.save()

            if ( c.getParams()[60] == 0 ):
                pr = ""
            else:
                pr = c.getProbingData()

            cv = CurveVectors(  
                    curve = cb, 
                    date = c.getDate(), 
                    method = 'DPV',
                    time = c.getTime(), 
                    potential = c.getPotential(),
                    current = c.getCurrent(), 
                    concentration = "",
                    concentrationUnits = "",
                    probingData = pr )
            cv.save()

            ci = CurveIndexing( 
                    curveBasic = cb, 
                    potential_min = min(c.getPotential()), 
                    potential_max = max(c.getPotential()), 
                    potential_step = c.getPotential()[1] - c.getPotential()[0], 
                    time_min = min(c.getTime()), 
                    time_max = max(c.getTime()), 
                    time_step = c.getTime()[1] - c.getTime()[0], 
                    current_min = min(c.getCurrent()), 
                    current_max = max(c.getCurrent()), 
                    current_range = max(c.getCurrent()) - min(c.getCurrent()), 
                    probingRate = c.getParams()[60] )
            ci.save()
            order+=1


if __name__ == '__main__':
    p = Parse(sys.argv[1])
