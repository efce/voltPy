from enum import IntEnum
import datetime
from abc import ABC, abstractproperty

class Param(IntEnum):
    PARAMNUM = 64
    VOL_CMAX = 50 # maximum number of curves in ".vol" file (not in .volt)
    VOL_PMAX = 62 # number of parameters of each curve in ".vol" file

    method = 0 #measurment method
    method_scv = 0
    method_npv = 1
    method_dpv = 2
    method_sqw = 3
    method_lsv = 4

    sampl = 1 #type of sampling (usually single sampling for SCV/LSV and double sampling for NPV/DPV/SQW)
    sampl_single = 0
    sampl_double = 1

    el23 = 2 #cell setup dummy = internal
    el23_dummy = 2
    el23_two = 0
    el23_three = 1

    aver = 3 #average the curve for # of measuremnts

    messc = 4 #cyclicity of measurement
    messc_single = 0
    messc_cyclic = 1
    messc_multicyclic = 2

    crange = 5 #current range (other for micro and other for marco)
    crange_macro_100nA = 6
    crange_macro_1uA = 5
    crange_macro_10uA = 4
    crange_macro_100uA = 3
    crange_macro_1mA = 2
    crange_macro_10mA = 1
    crange_macro_100mA = 0
    crange_micro_5nA = 3
    crange_micro_50nA = 2
    crange_micro_500nA = 1
    crange_micro_5uA = 0

    mespv = 6 #polarographic (DME) or voltamperometric (other)
    mespv_polarography = 0
    mespv_voltamperometry = 1

    electr = 7 #type of electrode used
    electr_macro = 0
    electr_dme = 0
    electr_solid = 1
    electr_cgmde = 2
    electr_micro = 3
    electr_microDme = 3 #does not exists IRL
    electr_microSolid = 4
    electr_microCgmde = 5
    electr_multi = 6
    electr_multiSolid = 6

    multi = 8 #multielectrode measurement (with m164 electrode stand) -- bitewise description of aquisition channels
    Ep = 9    #start potential [mV]
    Ek = 10   #end potential [mV]
    Estep = 11 #potential step [mV]
    dEdt = 11  #lsv potential change rate (according to lsv_stepE and lsv_time)
    E0 = 12    #NPV base potential [mV]
    dE = 12    #DPV/SQW impulse potential [mV]
    EstartLSV = 12    #LSV multicyclic starting potential [mV]
    tp = 13    #probing time [ms]
    tw = 14    #waiting time [ms]
    tk = 15    #unknown [ms]
    td = 15    #before first potential step apply potential [ms]
    ts = 15    #LSV multicyclic time of starting potential
    ptnr = 16  #number of points of the curve
    kn = 17    #hammer (knock power?)
    mix = 18   #mixer speed

    breaknr = 19 #number of interruput (eg. preconcentration) 0-7
    breakmin = 20 #time in [min] of each interrupt (from 20 to 26)
    breaksec = 27 #time in [sec] of each interrupt (from 27 to 34)
    breakE = 34   #potential in [sec] of each interrupt (from 34 to 40)

    impnr = 41 #/* offset of nr of imp. - KER-KW  */
    imptime = 42 #/* offset of impulse time         */
    inttime = 43 #/* offset of interrupt time       */
    gtype = 44 #/* offset of type of generation   */
    maxse = 45 #/* nr of impulse in max. drop */

    param46 = 46 # not in use

    inf_smooth = 47 #was curve smoothed
    inf_smooth_no = 0
    inf_smooth_yes = 1

    inf_bkgs = 48 #was background subtracted
    inf_bkgs_no = 0
    inf_bkgs_yes = 1

    inf_move = 49 #was the baseline moved
    inf_move_no = 0
    inf_move_yes = 1

    sti = 50 #stirrer speed
    kp = 51  #knock power
    kpt = 52 #knock pulse time

    Escheck = 53 #use Es potential for LSV measurement
    Escheck_no = 0
    Escheck_yes = 1

    date_day = 54
    date_month = 55
    date_year = 56
    date_hour = 57
    date_minutes = 58
    date_seconds = 59

    nonaveragedsampling = 60 # (old ms1) 0=regular sampling value = sampling frequency in kHz

    pro = 61 # potential program in external file
    pro_no = 0
    pro_yes = 1


class LSV():
    LSVstepE = [ # potential step [mV]
        0.125, 0.25, 0.25, 0.125, 0.25, 0.5, 0.25, 0.5,1.0, 0.25, 0.5, 1.0, 2.0, 5.0 ];
    LSVtime = [ # time [ms]
        120, 120, 60, 20, 20, 20, 5, 5, 5, 1, 1, 1, 1, 1 ];


class CurveEA(ABC):
    vec_param = []
    vec_potential = []
    vec_current = []
    vec_time = []
    vec_probing = []
    name = ""
    comment = ""

    def getDate(self):
        return datetime.datetime(self.vec_param[Param.date_year],
                                self.vec_param[Param.date_month],
                                self.vec_param[Param.date_day],
                                self.vec_param[Param.date_hour],
                                self.vec_param[Param.date_minutes],
                                self.vec_param[Param.date_seconds])

    def getMethod(self):
        methods = {
                Param.method_scv : 'SCV',
                Param.method_npv : 'NPV',
                Param.method_dpv : 'DPV',
                Param.method_sqw : 'SWV',
                Param.method_lsv : 'LSV',
                }
        num = self.vec_param[Param.method]
        if ( num >= 0 and num < len(methods) ):
            return methods[num]
        else:
            return ''
