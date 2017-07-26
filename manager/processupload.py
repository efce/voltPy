import os, sys
import struct
import random
from stat import *
from .curvevolt import CurveVolt
from .curvevol import CurveVol
from .curveea import *
from django.utils import timezone
from django.db import transaction
from .models import *

class ProcessUpload:
    _curves = []
    _ufile = 0
    _fname = ""
    _fcomment = ""
    _user_id = ""
    _analyte = ""
    _analyte_conc = ""
    _analyte_conc_list = []
    status = False

    @transaction.atomic 
    def __init__(self, user_id, ufile, name, comment):
        self._user_id = user_id
        self._fname = name
        self._fcomment = comment
        self._ufile = ufile

        if ( ufile.name.lower().endswith(".volt") or ufile.name.lower().endswith(".voltc") ):
            isCompressed = False
            if ( ufile.name.lower().endswith(".voltc") ):
                isCompressed = True
            self._parseVolt(isCompressed)
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
        
        elif ( ufile.name.lower().endswith(".vol") ):
            self._parseVol()
            sid=transaction.savepoint()
            try:
                self._createModels()
            except:
                if ( __debug__ ):
                    print("Query failed, rolling back transaction. Exception:" + "%s" % e)
                transaction.savepoint_rollback(sid)
                self.status = False
                return
            if ( __debug__ ):
                print("Query succesful, commiting.")
            transaction.savepoint_commit(sid)
            self.status = True
        
        else:
            if ( __debug__ ):
                print("Unknown extension")
    

    def _parseVol(self):
        fileContent = self._ufile.read();
        index = 0
        curvesNum = struct.unpack('<h', fileContent[index:index+2])[0]
        index += 2
        if ( __debug__ ):
            print("Number of curves in file: %i" % curvesNum)

        offsets=[]
        names = []
        start_addr = 2 + (60*4) + (50*12)#num of curves (int16) + 60 params (int32[60]) + 50 curves names char[10] 
        if ( curvesNum > 0 and curvesNum <= 50 ):
            for i in range(0, curvesNum):
                name = str(struct.unpack('{}s'.format(10), fileContent[index:index+10])[0])
                index+=10 
                offset = struct.unpack('<h', fileContent[index:index+2])[0]
                index+=2
                names.append(name)
                offsets.append(offset)

        index = 2 + 50*12 # The dictionary of .vol always reseves the place for
                          # names and offsets of 50 curves
        params = struct.unpack('i'*60, fileContent[index:index+4*60])
        index += 4*60
        fileSize = len(fileContent)

        if ( len(offsets) > 0 ):
            for i, offset in enumerate(offsets):
                index_start = start_addr
                for a in range(0,i):
                    index_start += offsets[a]
                index_end = index_start + offsets[i]
                if ( __debug__):
                    print("start %i ; end %i" % (index_start, index_end))
                c = CurveVol(names[i],params)
                retIndex = c.unserialize(fileContent[index_start:index_end]) 
                self._curves.append(c)
                if ( retIndex < (index_end-index_start) ):
                    print("WARNING!: last index lower than data end cyclic curve not processed ?")

        if ( __debug__ ):
            for v in self._curves:
                print("name: %s" % v.name)


    def _parseVolt(self, isCompressed):
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
            c.unserialize(fileContent[index:index+curveSize], isCompressed) 
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
        if ( __debug__ ):
            print("saved")

        analyte = Analyte(name=self._analyte)
        if ( __debug__ ):
            print("saving Analytes")
        analyte.save()
        if ( __debug__ ):
            print("saved")

        order=0
        for c in self._curves:
            cb = Curve(        
                    curveFile=cf,    
                    orderInFile=order,  
                    name=c.name,  
                    comment=c.comment, 
                    params=c.vec_param, 
                    date=c.getDate() )
            if ( __debug__ ):
                print("saving CurveBasic")
            cb.save()
            if ( __debug__ ):
                print("saved")
                print(c.vec_param)

            if ( c.vec_param[Param.nonaveragedsampling] == 0 ):
                pr = []
            else:
                pr = c.vec_probing

            cv = CurveData(
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
            if ( __debug__ ):
                print("saved")

            ci = CurveIndex( 
                    curve = cb, 
                    potential_min = min(c.vec_potential), 
                    potential_max = max(c.vec_potential), 
                    potential_step = c.vec_potential[1] - c.vec_potential[0], 
                    time_min = min(c.vec_time), 
                    time_max = max(c.vec_time), 
                    time_step = c.vec_time[1] - c.vec_time[0], 
                    current_min = min(c.vec_current), 
                    current_max = max(c.vec_current), 
                    current_range = max(c.vec_current) - min(c.vec_current), 
                    probingRate = c.vec_param[Param.nonaveragedsampling] )
            if ( __debug__ ):
                print("saving CurveIndexing")
            ci.save()
            if ( __debug__ ):
                print("saved")
            order+=1

    def _processAnalyte(self):
        if not self._analyte:
            raise 1
        if not self._analyte_conc:
            raise 2

        self._analyte_conc.replace(" ","")

        acl = self._analyte_conc.split(",")
        for conc in acl:
            self._analyte_conc_list.append(float(conc))


if __name__ == '__main__':
    p = Parse(sys.argv[1])
