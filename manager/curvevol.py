import struct
import datetime

class CurveVol:
    vec_params = []
    vec_current = []
    vec_potential = []
    vec_time = []
    vec_probing = [] 
    name = ""
    comment = ""
    
    def __init__(self):
        self._name = ""


    def _getMethod(self):
        methods = {
                0 : 'SCV',
                1 : 'NPV',
                2 : 'DPV',
                3 : 'SWV',
                4 : 'LSV',
                }
        if ( num >= 0 and num < len(methods) ):
            return methods[vec_params[60]]
        else:
            return ''


    def getDate(self):
        return datetime.datetime(self.vec_params[56],self.vec_params[55],self.vec_params[54],self.vec_params[57],self.vec_params[58],self.vec_params[59])
    
    def unserialize(self, data):
        # Decode name
        bytename = bytearray()
        index = 0
        while True:
            cc=struct.unpack('<B', data[index:index+1])
            index += 1
            if (cc[0] == 0):
                break
            bytename.append(cc[0])
        self.name = bytename.decode('utf8')
        if ( __debug__ ):
            print("The name is: %s" % self.name)
        
        # Decode comment 
        bytename = bytearray()
        while True:
            cc=struct.unpack('<B', data[index:index+1])
            index += 1
            if (cc[0] == 0):
                break
            bytename.append(cc[0])
        self._comment = bytename.decode('utf8')
        if ( __debug__ ):
            print("The comment is: %s" % self._comment)

        # Decode param:
        paramNum = struct.unpack('<i', data[index:index+4])[0]
        if ( __debug__ ):
            print('Number of params: %i' % paramNum)
        index += 4
        self.vec_params =struct.unpack('<'+paramNum*'i', data[index:index+4*paramNum])
        index+= (4*paramNum)

        #Decode vectors
        vectorSize = self.vec_params[16] #16 = ptnr
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
        if (self.vec_params[60] != 0): ##60 = nonaveraged
            probingNum = struct.unpack('<i', data[index:index+4])[0]
            index+=4
            self.vec_probing = struct.unpack('f'*probingNum, data[index:index+probingNum*4])

