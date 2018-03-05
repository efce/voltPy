import struct
import datetime
from .generic_eaqt import Generic_EAQt, Param, LSV
import zlib

class Volt(Generic_EAQt):
    
    def __init__(self):
        self.name = ""

    
    def unserialize(self, data, isCompressed):
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
        self.comment = bytename.decode('utf8')
        if ( __debug__ ):
            print("The comment is: %s" % self.comment)

        # Decode param:
        paramNum = struct.unpack('<i', dataUnc[index:index+4])[0]
        if ( __debug__ ):
            print('Number of params: %i' % paramNum)
        index += 4
        listparam = struct.unpack('<'+paramNum*'i', dataUnc[index:index+4*paramNum])
        for i,v in enumerate(listparam):
            self.vec_param[i] = v
        index+= (4*paramNum)

        #Decode vectors
        vectorSize = self.vec_param[16] #16 = ptnr
        self.vec_time = [0.0] * vectorSize
        self.vec_potential = [0.0] * vectorSize
        self.vec_current = [0.0] * vectorSize
        for i in range(0,vectorSize):
            self.vec_time[i] =struct.unpack('d', dataUnc[index:index+8])[0]
            index+=8
            self.vec_potential[i] =struct.unpack('d', dataUnc[index:index+8])[0]
            index+=8
            self.vec_current[i] =struct.unpack('d', dataUnc[index:index+8])[0]
            index+=8

        # Decode probing data
        if (self.vec_param[60] != 0): ##60 = nonaveraged
            probingNum = struct.unpack('<i', dataUnc[index:index+4])[0]
            index+=4
            self.vec_probing = struct.unpack('f'*probingNum, dataUnc[index:index+probingNum*4])

        return index
