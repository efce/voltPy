import datetime
from abc import ABC, abstractproperty
from manager.models import Curve as mcurve
Param = mcruve.Param
LSV = mcruve.LSV

class Generic_EAQt(ABC):
    vec_param = {}
    vec_potential = []
    vec_current = []
    vec_time = []
    vec_sampling = []
    name = ""
    comment = ""

    @property
    def date(self):
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
