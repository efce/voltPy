import os, sys
import struct
import random
from stat import *
from .curvevolt import CurveVolt
from .curvevol import CurveVol
from django.utils import timezone
from django.db import transaction
from .models import *

class ProcessUpload:
    _curves = []
    _ufile = 0
    _fname = ""
    _fcomment = ""
    _user_id = ""
    status = False

    @transaction.atomic 
    def __init__(self, user_id, ufile, name, comment):
        self._user_id = user_id
        self._fname = name
        self._fcomment = comment
        self._ufile = ufile

        if ( ufile.name.endswith(".volt") or ufile.name.endswith(".voltc") ):
            self._parseVolt()
            sid=transaction.savepoint()
            try:
                self._createModels()
            except Exception as e:
                if ( __debug__ ):
                    print("Query failed, rolling back transaction. Exception:" + "%s" % e)
                transaction.savepoint_rollback(sid)
                self.status = False
                return
            if ( __debug__ ):
                print("Query succesful, commiting.")
            transaction.savepoint_commit(sid)
            self.status = True
        
        elif ( ufile.name.endswith(".vol") ):
            self._parseVol()
            sid=transaction.savepoint()
            try:
                self._createModels()
            except:
                transaction.savepoint_rollback(sid)
                self.status = False
                return
            transaction.savepoint_commit(sid)
            self.status = True
        
        else:
            if ( __debug__ ):
                print("Unknown extension")
    

    def _parseVol(self):
        fileContent = self._ufile.read();
        index = 0
        curvesNum = struct.unpack('<i', fileContent[index:index+4])[0]
        index += 4
        if ( __debug__ ):
            print("Number of curves in file: %i" % curvesNum)

        for i in range(0, curvesNum):
            curveSize = struct.unpack('I', fileContent[index:index+4])[0]
            index+=4
            c = CurveVol()
            c.unserialize(fileContent[index:index+curveSize]) 
            self._curves.append(c)
            index+=curveSize-4 # 4 was added earlier

        if ( __debug__ ):
            for v in self._curves:
                print("name: %s" % v.name)


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
                print("name: %s" % v.name)


    def _createModels(self):
        if ( __debug__ ):
            print("Getting user...")
        try: 
            user = User.objects.get(pk=self._user_id)
        except User.DoesNotExist:
            #TODO: tempormary
            user = User(id=self._user_id, name=random.choice("abcdeBERWdasKI"))
            user.save()

        cf = CurveFile(
                owner=user, 
                name=self._fname,
                comment=self._fcomment,
                filename = self._ufile.name,
                fileDate=timezone.now(), 
                uploadDate=timezone.now() )
        if ( __debug__ ):
            print("saving CurveFile")
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
            if ( __debug__ ):
                print("saving CurveBasic")
            cb.save()

            if ( c.vec_params[60] == 0 ):
                pr = ""
            else:
                pr = c.vec_probing

            cv = CurveVectors(  
                    curve = cb, 
                    date = c.getDate(), 
                    method = c.getMethod(),
                    time = c.vec_time, 
                    potential = c.vec_potential,
                    current = c.vec_current, 
                    concentration = "",
                    concentrationUnits = "",
                    probingData = pr )
            if ( __debug__ ):
                print("saving CurveVectors")
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
            if ( __debug__ ):
                print("saving CurveIndexing")
            ci.save()
            order+=1
            


if __name__ == '__main__':
    p = Parse(sys.argv[1])
