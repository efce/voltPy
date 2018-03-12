import struct
import datetime
import struct
from manager.uploads.generic_eaqt import Generic_EAQt
from manager.uploads.parser import Parser
from manager.models import Curve as mcurve
Param = mcurve.Param
LSV = mcurve.LSV

class Vol(Parser):
    class CurveFromFile(Generic_EAQt):
        pass

    def __init__(self, cfile, details):
        # Details not needed - ignore
        self.names = []
        self._curves = []
        self.cfile = cfile
        fileContent = self.cfile.read();
        index = 0
        curvesNum = struct.unpack('<h', fileContent[index:index+2])[0]
        index += 2
        if ( __debug__ ):
            print("Number of curves in file: %i" % curvesNum)

        offsets=[]
        start_addr = 2 + (60*4) + (50*12) #num of curves (int16) + 60 params (int32[60]) + 50 curves names char[10] 
        if ( curvesNum > 0 and curvesNum <= 50 ):
            for i in range(0, curvesNum):
                name = str(struct.unpack('{}s'.format(10), fileContent[index:index+10])[0])
                index+=10 
                offset = struct.unpack('<h', fileContent[index:index+2])[0]
                index+=2
                self.names.append(name)
                offsets.append(offset)

        index = 2 + 50*12 # The dictionary of .vol always reseves the place for
                          # names and offsets of 50 curves
        self.params = struct.unpack('i'*60, fileContent[index:index+4*60])
        index += 4*60
        fileSize = len(fileContent)

        if ( len(offsets) > 0 ):
            for i, offset in enumerate(offsets):
                index_start = start_addr
                for a in range(0,i):
                    index_start += offsets[a]
                index_end = index_start + offsets[i]
                (c, retIndex) = self.unserialize(self.names[i], fileContent[index_start:index_end]) 
                self._curves.append(c)
                if ( retIndex < (index_end-index_start) ):
                    print("WARNING!: last index lower than data end cyclic curve not processed ?")

    
    def unserialize(self, sysname, data):
        c = self.CurveFromFile()
        #self.vec_param = Param.PARAMNUM * [0]
        for i, val in enumerate(self.params):
            c.vec_param[i] = val
        # Decode name
        index = 0
        curveNum = struct.unpack('<h',data[index:index+2])[0]
        index+=2
        cc=struct.unpack('{}s'.format(10), data[index:index+10])
        index+=10
        #TODO: verify with initial name
        c.name = cc[0].split(b'\0',1)[0].decode("cp1250") 
        if ( __debug__ ):
            print("The name is: %s" % c.name)
        
        # Decode comment 
        cc=struct.unpack('{}s'.format(50), data[index:index+50])
        index+=50
        c.comment = cc[0].split(b'\0',1)[0].decode("cp1250")
        if ( __debug__ ):
            print("The comment is: %s" % c.comment)

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
            c.vec_param[paramId] = paramVal

        timeStep = 0
        if ( c.vec_param[Param.method] != Param.method_lsv ):
            timeStep = 2 * (c.vec_param[Param.tp] + c.vec_param[Param.tw])
        else:
            timeStep = LSV.LSVtime[c.vec_param[Param.dEdt]]

        eStep = (c.vec_param[Param.Ek] - c.vec_param[Param.Ep]) / c.vec_param[Param.ptnr]

        #Decode vectors
        vectorSize = c.vec_param[Param.ptnr] 
        c.vec_time = [0.0] * vectorSize
        c.vec_potential = [0.0] * vectorSize
        c.vec_current = [0.0] * vectorSize
        time = timeStep
        potential = c.vec_param[Param.Ep]
        for i in range(0,vectorSize):
            c.vec_current[i] =struct.unpack('d', data[index:index+8])[0]
            index+=8
            c.vec_time[i] = time
            time += timeStep
            c.vec_potential[i] = potential
            potential += eStep
        return c, index
