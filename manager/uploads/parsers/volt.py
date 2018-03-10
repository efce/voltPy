import datetime
import struct
import zlib
from manager.uploads.generic_eaqt import Generic_EAQt
from manager.uploads.parser import Parser
from manager.models import Curve as mcurve
Param = mcurve.Param
LSV = mcurve.LSV

class Volt(Parser):
    class CurveFromFile(Generic_EAQt):
        pass

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
