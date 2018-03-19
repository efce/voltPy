import struct
import datetime
import struct
import pandas as pd
import numpy as np
import datetime
from manager.uploads.parser import Parser
from manager.models import Curve as mcurve
Param = mcurve.Param

class Txt(Parser):

    def readPandas(self, fileForPandas, skipRows):
        return pd.read_csv(fileForPandas, sep='\s+', header=None, skiprows=skipRows)

    def __init__(self, cfile, details):
        # Details not needed - ignore
        self.vec_param = []
        self.names = []
        self._curves = []
        self.cfile = cfile
        skipRows = int(details.get('skipRows', 0))
        pdfile = self.readPandas(self.cfile, skipRows)
        potential = []
        time = []
        index = 0
        isSampling = details.get('isSampling', None) 
        spp = int(details.get('isSampling_SPP', 1)) # samples per point
        samplingFreq = float(details.get('isSampling_SFreq', 0)) # in kHz
        col1 = details.get('firstColumn', 'firstIsI') 
        Ep = float(details.get('firstColumn_Ep', 0))
        Ek = float(details.get('firstColumn_Ek', 1))
        dE = float(details.get('firstColumn_dE', 0))
        t_E = float(details.get('firstColumn_t', 1))
        method = details.get('voltMethod', 'lsv')
        ptnr = len(pdfile[0])

        if isSampling == None:
            if col1 == 'firstIsE': #potential in 1st col
                potential = pdfile[0]
                Ep = potential[0]
                Ek = potential[len(potential)-1]
                Estep = potential[1] - potential[0]
                time = [ i for i in range(len(pdfile[0])) ]
                index = 1
            elif col1 == 'firstIsT': #time in 1st col
                time = pdfile[0]
                Estep = (Ek - Ep) / ptnr
                potential = list(np.arange(Ep, Ek, Estep))
                index = 1
            else: #current in 1st col
                Estep = (Ek - Ep) / ptnr
                potential = list(np.arange(Ep, Ek, Estep))
                time = list(np.arange(0, t_E*ptnr, t_E))
        else: #it is sampling data
            def processNonE():
                lessPtnr = ( 'npv', 'dpv', 'swv' )
                if method in lessPtnr:
                    Estep = (Ek - Ep) / (ptnr / (2*spp))
                    time = list(np.arange(0, t_E*ptnr/(2*spp), t_E))
                else:
                    Estep = (Ek - Ep) / (ptnr / spp)
                    time = list(np.arange(0, t_E*ptnr/spp, t_E))
                potential = list(np.arange(Ep, Ek, Estep))

            if col1 == 'firstIsE':
                potential = pdfile[0]
                Ep = potential[0]
                Ek = potential[len(potential)-1]
                Estep = potential[1] - potential[1+(2*spp)]
                time = [ (i/samplingFreq) for i in range(len((pdfile[0])/spp)) ]
                index = 1
            elif col1 == 'firstIsT':
                processNonE()
                time = pdfile[0]
                index = 1
            else:
                processNonE()

        self.vec_param = [0]*Param.PARAMNUM
        self.vec_param[Param.Ek] = Ek
        self.vec_param[Param.Ep] = Ep
        self.vec_param[Param.Estep] = Estep
        self.vec_param[Param.dE] = dE
        self.vec_param[Param.method] = self.methodDict[details.get('voltMethod', 'lsv')]
        self.vec_param[Param.nonaveragedsampling] = samplingFreq
        self.vec_param[Param.tw] = 0
        self.vec_param[Param.tp] = t_E if samplingFreq == 0 else spp

        for i in range(len(pdfile.columns)-index):
            ci = index + i
            c = self.CurveFromFile()
            c.name = str(i)
            c.vec_param = self.vec_param
            c.vec_potential = potential
            if isSampling == None:
                c.vec_sampling = []
                c.vec_current = pdfile[ci]
            else:
                c.vec_sampling = pdfile[ci]
                c.vec_current = self.calculateMethod(c.vec_sampling, spp, self.vec_param[Param.method])
            c.vec_time = time
            c.date = datetime.datetime.now()
            self._curves.append(c)
