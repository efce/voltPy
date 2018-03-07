import datetime
import struct
import zlib
import manager.models as mmodels
from manager.uploads.generic_eaqt import Generic_EAQt, Param, LSV
from manager.uploads.parser import Parser

class Volt(Parser):

    class CurveFromFile(Generic_EAQt):
        name =''
        comment = ''
        vec_param = [0] * Param.PARAMNUM
        vec_time = []
        vec_potential = []
        vec_current = []
        vec_sampling = []

    def __init__(self, cfile, details):
        # Details not needed - ignore
        self._curves = []
        self.name = ""
        self.cfile = cfile
        if cfile.name.endswith('voltc'):
            self.isCompressed = True
        else:
            self.isCompressed = False
        fileContent = self.cfile.read();
        index = 0
        curvesNum = struct.unpack('<i', fileContent[index:index+4])[0]
        index += 4
        for i in range(0, curvesNum):
            curveSize = struct.unpack('I', fileContent[index:index+4])[0]
            index+=4
            c = self.unserialize(fileContent[index:index+curveSize], self.isCompressed) 
            self._curves.append(c)
            index+=curveSize-4 # 4 was added earlier
    

    def unserialize(self, data, isCompressed):
        # Decode name
        c = self.CurveFromFile()
        bytename = bytearray()
        index = 0
        while True:
            cc=struct.unpack('<B', data[index:index+1])
            index += 1
            if (cc[0] == 0):
                break
            bytename.append(cc[0])
        c.name = bytename.decode('utf8')
        if ( __debug__ ):
            print("The name is: %s" % c.name)

        if ( isCompressed ):
            dataUnc = zlib.decompress(data[index+4:]) #QT qCompress add 4 bytes 
            # src: http://bohdan-danishevsky.blogspot.com/2013/11/qt-51-zlib-compression-compatible-with.html
        else:
            dataUnc = data[index:]

        index = 0
        
        # Decode comment 
        bytename = bytearray()
        while True:
            cc=struct.unpack('<B', dataUnc[index:index+1])
            index += 1
            if (cc[0] == 0):
                break
            bytename.append(cc[0])
        c.comment = bytename.decode('utf8')
        if ( __debug__ ):
            print("The comment is: %s" % c.comment)

        # Decode param:
        paramNum = struct.unpack('<i', dataUnc[index:index+4])[0]
        if ( __debug__ ):
            print('Number of params: %i' % paramNum)
        index += 4
        listparam = struct.unpack('<'+paramNum*'i', dataUnc[index:index+4*paramNum])
        for i,v in enumerate(listparam):
            c.vec_param[i] = v
        index+= (4*paramNum)

        #Decode vectors
        vectorSize = c.vec_param[16] #16 = ptnr
        c.vec_time = [0.0] * vectorSize
        c.vec_potential = [0.0] * vectorSize
        c.vec_current = [0.0] * vectorSize
        for i in range(0,vectorSize):
            c.vec_time[i] =struct.unpack('d', dataUnc[index:index+8])[0]
            index+=8
            c.vec_potential[i] =struct.unpack('d', dataUnc[index:index+8])[0]
            index+=8
            c.vec_current[i] =struct.unpack('d', dataUnc[index:index+8])[0]
            index+=8

        # Decode probing data
        if (c.vec_param[60] != 0): ##60 = nonaveraged
            probingNum = struct.unpack('<i', dataUnc[index:index+4])[0]
            index+=4
            c.vec_sampling = struct.unpack('f'*probingNum, dataUnc[index:index+probingNum*4])
        return c

    def saveModels(self, user):
        cf = mmodels.CurveFile(
            owner=user, 
            name=self.cfile.name,
            fileName=self.cfile.name,
            fileDate=self._curves[0].getDate(),
        )
        cs = mmodels.CurveSet(
            owner=user,
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
                date=c.getDate() 
            )
            cb.save()

            cd = mmodels.CurveData(
                curve = cb, 
                date = c.getDate(), 
                processing = None,
                time = c.vec_time, 
                potential = c.vec_potential,
                current = c.vec_current, 
                currentSamples = c.vec_probing 
            )
            cd.save()
            cs.curvesData.add(cd)

            ci = mmodels.CurveIndex( 
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
                samplingRate = c.vec_param[Param.nonaveragedsampling] if len(c.vec_param) > Param.nonaveragedsampling else 0
            )
            ci.save()
            order+=1

        cs.save()
        return cf.id
