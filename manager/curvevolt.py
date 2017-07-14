import struct
import datetime

class CurveVolt:
    _params = []
    _vCurrent = []
    _vPotential = []
    _vTime = []
    _vProbing = [] 
    _name = ""
    _comment = ""
    
    def __init__(self):
        self._name = ""

    def setParams(self, arr):
        self._params = arr

    def setParam(self, num, val):
        self._params[num] = val

    def getParam(self, num):
        return self._params[num]

    def getParams(self):
        return self._params

    def getDate(self):
        return datetime.datetime(self._params[56],self._params[55],self._params[54],self._params[57],self._params[58],self._params[59])

    def setCurrent(self, vector):
        self._vCurrent = vector

    def getCurrent(self):
        return self._vCurrent

    def setPotential(self, vector):
        self._vPotential = vector

    def getPotential(self):
        return self._vPotential

    def setProbingData(self, vec):
        self._vProbing = vec

    def getProbingData(self):
        return self._vProbing

    def setTime(self, vector):
        self._vTime = vector

    def getTime(self):
        return self._vTime

    def setName(self, name):
        self._name = name

    def getName(self):
        return self._name

    def setComment(self, comment):
        self._comment = comment

    def getComment(self):
        return self._comment
    
    def unserialize(self, data):
        # Decode name
        bytename = bytearray()
        index = 0
        while True:
            cc=struct.unpack('<B', data[index:index+1])
            #print("index: %i, cc: %s" % (index, cc[0]))
            index += 1
            if (cc[0] == 0):
                break
            bytename.append(cc[0])
        self._name = bytename.decode('utf8')
        if ( __debug__ ):
            print("The name is: %s" % self._name)
        
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
            print('Params # %i' % paramNum)
        index += 4
        self._params =struct.unpack('<'+paramNum*'i', data[index:index+4*paramNum])
        index+= (4*paramNum)

        #Decode vectors
        vectorSize = self._params[16] #16 = ptnr
        vTime = [0.0] * vectorSize
        vPot = [0.0] * vectorSize
        vCurrent = [0.0] * vectorSize
        for i in range(0,vectorSize):
            vTime[i] =struct.unpack('d', data[index:index+8])[0]
            index+=8
            vPot[i] =struct.unpack('d', data[index:index+8])[0]
            index+=8
            vCurrent[i] =struct.unpack('d', data[index:index+8])[0]
            index+=8
        self._vTime = vTime
        self._vPotential = vPot
        self._vCurrent = vCurrent

        # Decode probing data
        if (self._params[60] != 0): ##60 = nonaveraged
            probingNum = struct.unpack('<i', data[index:index+4])[0]
            index+=4
            self._vProbing = struct.unpack('f'*probingNum, data[index:index+probingNum*4])

