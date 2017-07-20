import struct
import datetime
from .curveea import *

class CurveVol(CurveEA):
    
    def __init__(self, name, params):
        self.name = name
        self.vec_param = params

    
    def unserialize(self, data):
        # Decode name
        index = 0
        curveNum = struct.unpack('<s',data[index:index+2])
        bytename = bytearray()
        cc=struct.unpack('c'*10, data[index:index+10])
        index+=10
        bytename.append(cc[0])
        #TODO: verify with initial name
        self.name = bytename.decode('latin1')
        if ( __debug__ ):
            print("The name is: %s" % self.name)
        
        # Decode comment 
        bytename = bytearray()
        cc=struct.unpack('c'*10, data[index:index+50])
        index+=50
        bytename.append(cc[0])
        self.comment = bytename.decode('latin1')
        if ( __debug__ ):
            print("The comment is: %s" % self._comment)

        # Decode param:
        paramDiffNum = struct.unpack('<s', data[index:index+2])[0]
        if ( __debug__ ):
            print('Number of params: %i' % paramNum)
        index += 2
        for i in range(0,paramDiffNum):
            paramId = struct.unpack('<s', data[index:index+2])[0]
            index+=2
            paramVal = struct.unpack('<i', data[index:index+4])[0]
            index+=4
            self.vec_param[paramId] = paramVal

        timeStep = 0
        if ( self.vec_param[Param.method] != Param.method_lsv ):
            timeStep = 2 * (self.vec_param[Param.tp] + self.vec_param[Param.tw])
        else:
            timeStep = LSV.LSVtime[self.vec_param[Param.dEdt]]

        #Decode vectors
        vectorSize = self.vec_param[Param.ptnr] 
        self.vec_time = [0.0] * vectorSize
        self.vec_potential = [0.0] * vectorSize
        self.vec_current = [0.0] * vectorSize
        for i in range(0,vectorSize):
            self.vec_time[i] =struct.unpack('d', data[index:index+8])[0]
            index+=8
            self.vec_potential[i] =struct.unpack('d', data[index:index+8])[0]
            index+=8
            self.vec_current[i] =struct.unpack('d', data[index:index+8])[0]
            index+=8

        # Decode probing data
        if (self.vec_param[60] != 0): ##60 = nonaveraged
            probingNum = struct.unpack('<i', data[index:index+4])[0]
            index+=4
            self.vec_probing = struct.unpack('f'*probingNum, data[index:index+probingNum*4])

