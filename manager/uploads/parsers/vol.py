import struct
import datetime
from generic_eaqt import Generic_EAQt, Param, LSV

class Vol(Generic_EAQt):
    
    def __init__(self, name, params):
        self.name = name
        #self.vec_param = Param.PARAMNUM * [0]
        for i, val in enumerate(params):
            self.vec_param[i] = val

    
    def unserialize(self, data):
        # Decode name
        index = 0
        curveNum = struct.unpack('<h',data[index:index+2])[0]
        index+=2
        cc=struct.unpack('{}s'.format(10), data[index:index+10])
        index+=10
        #TODO: verify with initial name
        self.name = cc[0].split(b'\0',1)[0].decode("cp1250") 
        if ( __debug__ ):
            print("The name is: %s" % self.name)
        
        # Decode comment 
        cc=struct.unpack('{}s'.format(50), data[index:index+50])
        index+=50
        self.comment = cc[0].split(b'\0',1)[0].decode("cp1250")
        if ( __debug__ ):
            print("The comment is: %s" % self.comment)

        # Decode param:
        paramDiffNum = struct.unpack('<h', data[index:index+2])[0]
        if ( __debug__ ):
            print('Number of params: %i' % paramDiffNum)
        index += 2
        for i in range(0,paramDiffNum):
            paramId = struct.unpack('<h', data[index:index+2])[0]
            index+=2
            paramVal = struct.unpack('<i', data[index:index+4])[0]
            index+=4
            self.vec_param[paramId] = paramVal

        timeStep = 0
        if ( self.vec_param[Param.method] != Param.method_lsv ):
            timeStep = 2 * (self.vec_param[Param.tp] + self.vec_param[Param.tw])
        else:
            timeStep = LSV.LSVtime[self.vec_param[Param.dEdt]]

        eStep = (self.vec_param[Param.Ek] - self.vec_param[Param.Ep]) / self.vec_param[Param.ptnr]

        #Decode vectors
        vectorSize = self.vec_param[Param.ptnr] 
        self.vec_time = [0.0] * vectorSize
        self.vec_potential = [0.0] * vectorSize
        self.vec_current = [0.0] * vectorSize
        time = timeStep
        potential = self.vec_param[Param.Ep]
        for i in range(0,vectorSize):
            self.vec_current[i] =struct.unpack('d', data[index:index+8])[0]
            index+=8
            self.vec_time[i] = time
            time += timeStep
            self.vec_potential[i] = potential
            potential += eStep
    
        return index
