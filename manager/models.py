import numpy as np
import io
from copy import copy
from enum import IntEnum
from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from picklefield.fields import PickledObjectField


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_confirmed = models.BooleanField(default=False)


@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()


def exportCDasFile(cds):
    ''' Not a model, just helper '''
    cdict = {}
    explen = len(cds)
    for i, cd in enumerate(cds):
        for x, y in zip(cd.xVector, cd.yVector):
            tmp = cdict.get(x, [None]*explen)
            tmp[i] = y
            cdict[x] = tmp
    xcol = np.array(list(cdict.keys())).reshape((-1, 1))
    ycols = np.array(list(cdict.values()))
    allCols = np.concatenate((xcol, ycols), axis=1)
    memoryFile = io.StringIO()
    np.savetxt(memoryFile, allCols, delimiter=",", newline="\r\n", fmt='%s')
    return memoryFile


class CurveFile(models.Model):
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    name = models.TextField()
    comment = models.TextField()
    fileName = models.TextField()
    fileDate = models.DateField(auto_now=False, auto_now_add=False) # Each file has its curveset 
    curveSet = models.ForeignKey('CurveSet', on_delete=models.DO_NOTHING)
    uploadDate = models.DateField(auto_now_add=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name + ": " + self.fileName

    class META:
        ordering = ('uploadDate')

    def isOwnedBy(self, user):
        return (self.owner == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user)

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)

    def export(self):
        return self.curveSet.export()


class FileSet(models.Model):
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    name = models.TextField()
    files = models.ManyToManyField(CurveFile)
    date = models.DateField(auto_now_add=True)
    deleted = models.BooleanField(default=0)

    def __str__(self):
        return str(self.id) + ' ' + self.name

    class META:
        ordering = ('uploadDate')

    def isOwnedBy(self, user):
        return (self.owner == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user)

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)

    def export(self):
        cds = []
        for f in self.files.all():
            cds.extend(f.curveSet.curvesData.all())
        return exportCDasFile(cds)


class Curve(models.Model):
    class Param(IntEnum):
        PARAMNUM = 64
        VOL_CMAX = 50  # maximum number of curves in ".vol" file (not in .volt)
        VOL_PMAX = 62  # number of parameters of each curve in ".vol" file

        method = 0  #measurment method
        method_scv = 0
        method_npv = 1
        method_dpv = 2
        method_sqw = 3
        method_lsv = 4

        sampl = 1  #type of sampling (usually single sampling for SCV/LSV and double sampling for NPV/DPV/SQW)
        sampl_single = 0
        sampl_double = 1

        el23 = 2  #cell setup dummy = internal
        el23_dummy = 2
        el23_two = 0
        el23_three = 1

        aver = 3  #average the curve for  # of measuremnts

        messc = 4  #cyclicity of measurement
        messc_single = 0
        messc_cyclic = 1
        messc_multicyclic = 2

        crange = 5  #current range (other for micro and other for marco)
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

        mespv = 6  #polarographic (DME) or voltamperometric (other)
        mespv_polarography = 0
        mespv_voltamperometry = 1

        electr = 7  #type of electrode used
        electr_macro = 0
        electr_dme = 0
        electr_solid = 1
        electr_cgmde = 2
        electr_micro = 3
        electr_microDme = 3  #does not exists IRL
        electr_microSolid = 4
        electr_microCgmde = 5
        electr_multi = 6
        electr_multiSolid = 6

        multi = 8  #multielectrode measurement (with m164 electrode stand) -- bitewise description of aquisition channels
        Ep = 9     #start potential [mV]
        Ek = 10    #end potential [mV]
        Estep = 11  #potential step [mV]
        dEdt = 11   #lsv potential change rate (according to lsv_stepE and lsv_time)
        E0 = 12     #NPV base potential [mV]
        dE = 12     #DPV/SQW impulse potential [mV]
        EstartLSV = 12     #LSV multicyclic starting potential [mV]
        tp = 13     #probing time [ms]
        tw = 14     #waiting time [ms]
        tk = 15     #unknown [ms]
        td = 15     #before first potential step apply potential [ms]
        ts = 15     #LSV multicyclic time of starting potential
        ptnr = 16   #number of points of the curve
        kn = 17     #hammer (knock power?)
        mix = 18    #mixer speed

        breaknr = 19  #number of interruput (eg. preconcentration) 0-7
        breakmin = 20  #time in [min] of each interrupt (from 20 to 26)
        breaksec = 27  #time in [sec] of each interrupt (from 27 to 34)
        breakE = 34    #potential in [sec] of each interrupt (from 34 to 40)

        impnr = 41  #/* offset of nr of imp. - KER-KW  */
        imptime = 42  #/* offset of impulse time         */
        inttime = 43  #/* offset of interrupt time       */
        gtype = 44  #/* offset of type of generation   */
        maxse = 45  #/* nr of impulse in max. drop */

        param46 = 46  # not in use

        inf_smooth = 47  #was curve smoothed
        inf_smooth_no = 0
        inf_smooth_yes = 1

        inf_bkgs = 48  #was background subtracted
        inf_bkgs_no = 0
        inf_bkgs_yes = 1

        inf_move = 49  #was the baseline moved
        inf_move_no = 0
        inf_move_yes = 1

        sti = 50  #stirrer speed
        kp = 51   #knock power
        kpt = 52  #knock pulse time

        Escheck = 53  #use Es potential for LSV measurement
        Escheck_no = 0
        Escheck_yes = 1

        date_day = 54
        date_month = 55
        date_year = 56
        date_hour = 57
        date_minutes = 58
        date_seconds = 59

        nonaveragedsampling = 60  # (old ms1) 0=regular sampling value = sampling frequency in kHz

        pro = 61  # potential program in external file
        pro_no = 0
        pro_yes = 1

    class LSV():
        LSVstepE = [  # potential step [mV]
            0.125, 0.25, 0.25, 0.125, 0.25, 0.5, 0.25, 0.5,1.0, 0.25, 0.5, 1.0, 2.0, 5.0 ];
        LSVtime = [  # time [ms]
            120, 120, 60, 20, 20, 20, 5, 5, 5, 1, 1, 1, 1, 1 ];

    id = models.AutoField(primary_key=True)
    curveFile = models.ForeignKey(CurveFile, on_delete=models.CASCADE)
    orderInFile = models.IntegerField()
    name = models.TextField()
    comment = models.TextField()
    params = PickledObjectField() # JSON List
    date = models.DateField(auto_now=False, auto_now_add=False)
    deleted = models.BooleanField(default=0)

    def __str__(self):
        return self.curveFile.name + ": " + self.name

    class META:
        ordering = ('curveFile', 'orderInFile')

    def isOwnedBy(self, user):
        return (self.curveFile.owner == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user)

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)


class CurveIndex(models.Model):
    id = models.AutoField(primary_key=True)
    curve = models.ForeignKey(Curve, on_delete=models.CASCADE)
    potential_min = models.FloatField() # in mV
    potential_max = models.FloatField() # in mV
    potential_step = models.FloatField() # in mV
    time_min = models.FloatField() # in ms
    time_max = models.FloatField() # in ms
    time_step = models.FloatField() # is ms
    current_min = models.FloatField() # in mV
    current_max = models.FloatField() # in mV
    current_range = models.FloatField() # in mV
    samplingRate = models.IntegerField() # in kHz

    def isOwnedBy(self, user):
        return (self.curve.curveFile.owner == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user)

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)


class CurveData(models.Model):
    id = models.AutoField(primary_key=True)
    curve = models.ForeignKey(Curve, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    time = PickledObjectField() # JSON List 
    potential = PickledObjectField() # JSON List 
    current = PickledObjectField() # JSON List 
    currentSamples = PickledObjectField() # JSON List 
    basedOn = models.ForeignKey('CurveData', null=True, default=None, on_delete=models.DO_NOTHING)
    processedWith = models.ForeignKey('Processing', null=True, default=None, on_delete=models.DO_NOTHING)

    def getCopy(self):
        newcd = copy(self)
        newcd.id = None
        newcd.pk = None
        newcd.date = None
        newcd.basedOn = self
        return newcd

    def getProcessingHistory(self):
        steps = []
        c = self
        while True:
            steps.append(c.processedWith)
            if c.basedOn is not None:
                c = c.basedOn
            else:
                break
        return steps


    def isOwnedBy(self, user):
        return (self.curve.curveFile.owner == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user)

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)

    def xvalueToIndex(self, user, value):
        onx = OnXAxis.objects.get(user=user).selected
        if ( onx == 'P' ):
            diffvec = [ abs(x-value) for x in self.potential ]
            index, value = min(enumerate(diffvec), key=lambda p: p[1])
            return index
        if ( onx == 'T' ):
            diffvec = [ abs(x-value) for x in self.time ]
            index, value = min(enumerate(diffvec), key=lambda p: p[1])
            return index
        if ( onx == 'S' ):
            if value < 0:
                return 0
            elif value > len(self.currentSamples):
                return len(self.currentSamples)-1
            else:
                return int(value)

    @property
    def xVector(self):
        user = User.objects.get(id=1) #TODO FIXME do zmiany !!
        onx = OnXAxis.objects.get(user=user).selected
        if ( onx == 'P' ):
            return self.potential
        if ( onx == 'T' ):
            return self.time
        if ( onx == 'S' ):
            return range(len(self.currentSamples))

    @xVector.setter
    def xVector(self, val):
        user = User.objects.get(id=1) #TODO FIXME do zmiany !!
        onx = OnXAxis.objects.get(user=user).selected
        if ( onx == 'P' ):
            self.potential = val
        if ( onx == 'T' ):
            self.time = val
        if ( onx == 'S' ):
            pass

    @property
    def yVector(self):
        user = User.objects.get(id=1) #TODO FIXME do zmiany !!
        onx = OnXAxis.objects.get(user=user).selected
        if ( onx == 'P' ) or ( onx == 'T' ):
            return self.current
        if ( onx == 'S' ):
            return self.currentSamples

    @yVector.setter
    def yVector(self, val):
        user = User.objects.get(id=1) #TODO FIXME do zmiany !!
        onx = OnXAxis.objects.get(user=user).selected
        if ( onx == 'P'
        or onx == 'T' ):
            self.current = val
        if ( onx == 'S' ):
            self.currentSamples = val


class Analyte(models.Model):
    id = models.AutoField(primary_key=True)
    name=models.CharField(max_length=125, unique=True)
    atomicMass = models.FloatField(null=True, default=None) # to calculate between mol and wight

    def __str__(self):
        return self.name


class CurveSet(models.Model):
    minusOneSS = b'\xE2\x81\xBB\xC2\xB9'.decode("utf-8", "replace")
    cdot = b'\xC2\xB7'.decode("utf-8", "replace")
    CONC_UNITS = (
        ('9g','ng{cdot}L{ssm1}'.format(cdot=cdot,ssm1=minusOneSS)),
        ('6g','µg{cdot}L{ssm1}'.format(cdot=cdot,ssm1=minusOneSS)),
        ('3g','mg{cdot}L{ssm1}'.format(cdot=cdot,ssm1=minusOneSS)),
        ('0g','g{cdot}L{ssm1}'.format(cdot=cdot,ssm1=minusOneSS)),
        ('9M','nM'),
        ('6M','µM'),
        ('3M','mM'),
        ('0M','M')
    )
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=128)
    date = models.DateField(auto_now_add=True)
    locked = models.BooleanField(default=False)
    curvesData = models.ManyToManyField(CurveData, related_name="curvesData")
    undoCurvesData = models.ManyToManyField(CurveData, related_name="undoCurvesData")
    analytes = models.ManyToManyField(Analyte, related_name="analytes")
    undoAnalytes = models.ManyToManyField(Analyte, related_name="undoAnalytes")
    analytesConc = PickledObjectField(default={}) # dictionary key is analyte id
    undoAnalytesConc = PickledObjectField(default={}) # dictionary key is analyte id
    analytesConcUnits = PickledObjectField(default={}) # dictionary key is analyte id
    undoAnalytesConcUnits = PickledObjectField(default={}) # dictionary key is analyte id
    undoProcessing = models.ForeignKey('Processing', null=True, default=None, on_delete=models.DO_NOTHING)
    deleted = models.BooleanField(default=False)

    def removeCurve(self, curveData):
        self.curvesData.remove(curveData)
        for k,v in self.analytesConc.items():
            v.pop(curveData.id, None)

    def addCurve(self, curveData, curveConcDict={}):
        if not self.curvesData.filter(id=curveData.id).exists():
            self.curvesData.add(curveData)
        self.setCurveConcDict(curveData, curveConcDict)

    def setCurveConcDict(self, curveData, curveConcDict):
        newAnalytes = list(set(curveConcDict.keys()) - set(self.analytesConc.keys()))
        for na in newAnalytes:
            self.analytes.add(Analyte.objects.get(id=na))
            self.analytesConc[na] = self.analytesConc.get(na, {})
            for cd in self.curvesData.all():
                self.analytesConc[na][cd.id] = 0.0
        for k,v in self.analytesConc.items():
            v[curveData.id] = curveConcDict.get(k, 0.0)

    def getCurveConcDict(self, curveData):
        ret = {}
        for k,v in self.analytesConc.items():
            ret[k] = v.get(curveData.id, 0.0)
        return ret

    def isOwnedBy(self, user):
        return (self.owner == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user) #and not self.locked

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)

    def __str__(self):
        return "%s" % self.name

    def prepareUndo(self, processingObject=None):
        self.undoCurvesData.clear()
        for cd in self.curvesData.all():
            self.undoCurvesData.add(cd)
        self.undoAnalytes.clear()
        for a in self.analytes.all():
            self.undoAnalytes.add(a)
        self.undoAnalytesConc = copy(self.analytesConc)
        self.undoAnalytesConcUnits = copy(self.analytesConcUnits)
        self.undoProcessing = processingObject
        self.save()

    def undo(self):
        #TODO: Undo removes also processing method ! (store id somewhere?)
        if not self.hasUndo():
            return
        self.curvesData.clear()
        for cd in self.undoCurvesData.all():
            self.curvesData.add(cd)
        self.analytes.clear()
        for a in self.undoAnalytes.all():
            self.analytes.add(a)
        self.analytesConc = copy(self.undoAnalytesConc)
        self.analytesConcUnits = copy(self.undoAnalytesConcUnits)
        self.undoCurvesData.clear()
        self.undoAnalytes.clear()
        self.undoAnalytesConc.clear()
        self.undoAnalytesConcUnits.clear()
        if self.undoProcessing is not None:
            self.undoProcessing.delete()
            self.undoProcessing = None
        self.save()

    def hasUndo(self):
        if len(self.undoCurvesData.all()) == 0 or self.locked == True:
            return False
        else:
            return True

    def getProcessingHistory(self):
        return Processing.objects.filter(curveSet=self).order_by('id')

    def export(self):
        return exportCDasFile(self.curvesData.all())


class Analysis(models.Model):
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    curveSet = models.ForeignKey(CurveSet, on_delete=models.DO_NOTHING)
    date = models.DateField(auto_now_add=True)
    appliesModel = models.ForeignKey(Analysis, default=None, null=True, on_delete=models.DO_NOTHING)
    customData = PickledObjectField(default={})
    stepsData = PickledObjectField(default={})
    analytes = models.ManyToManyField(Analyte)
    name = models.TextField()
    method = models.TextField()
    active_step_num = models.IntegerField(default=0, null=True)
    deleted = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return "%s %s: %s" % (self.date, self.method, self.name);

    class META:
        ordering = ('date')

    def isOwnedBy(self, user):
        return (self.owner == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user)

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)

    def getUrl(self, user):
        if self.completed:
            return reverse('showAnalysis', args=[ self.id ])
        else:
            return reverse('analyze', args=[ self.id ])

class Processing(models.Model):
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    curveSet = models.ForeignKey(CurveSet, on_delete=models.DO_NOTHING)
    date = models.DateField(auto_now_add=True)
    appliesModel = models.ForeignKey(Processing, default=None, null=True, on_delete=models.DO_NOTHING)
    customData = PickledObjectField(default={})
    stepsData = PickledObjectField(default={})
    analytes = models.ManyToManyField(Analyte)
    name = models.TextField()
    method = models.TextField()
    active_step_num  = models.IntegerField(default=0, null=True)
    deleted = models.BooleanField(default=0)
    completed = models.BooleanField(default=0)

    def __str__(self):
        return "%s: %s" % (self.date, self.method)

    class META:
        ordering = ('date')

    def isOwnedBy(self, user):
        return (self.owner == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user)

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)

    def getUrl(self, user):
        return reverse('showCurveSet', args=[ self.curveSet.id ])


class OnXAxis(models.Model):
    AVAILABLE = (
        ('P', 'Potential'), 
        ('T', 'Time'), 
        ('S', 'Samples')
    )
    selected = models.CharField(max_length=1, choices=AVAILABLE, default='P')
    user = models.OneToOneField(User, on_delete=models.DO_NOTHING)
    
    def __str__(self):
        return self.selected;

    def isOwnedBy(self, user):
        return (self.user == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user)

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)
