import numpy as np
import io
from copy import copy
from enum import IntEnum
from typing import Dict, List
from overrides import overrides
from guardian.shortcuts import get_user_perms
from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from picklefield.fields import PickledObjectField
from manager.voltpymodel import VoltPyModel
from manager.exceptions import VoltPyNotAllowed
import manager


class SimpleNumpyField(models.BinaryField):
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        bf = io.BytesIO(value)
        return np.load(bf)['arr_0']

    @overrides
    def to_python(self, value):
        if isinstance(value, np.ndarray):
            return value
        if value is None:
            return value
        bf = io.BytesIO(value)
        return np.load(bf)['arr_0']

    @overrides
    def get_prep_value(self, value):
        value = np.array(value)
        bf = io.BytesIO()
        np.savez_compressed(bf, value)
        return bf.getvalue()


class Profile(models.Model):
    ONX_OPTIONS = (
        ('P', 'Potential'),
        ('T', 'Time'),
        ('S', 'Samples')
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    email_confirmed = models.BooleanField(default=False)
    show_on_x = models.CharField(max_length=1, choices=ONX_OPTIONS, default='P')


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


class FileSet(VoltPyModel):
    name = models.CharField(max_length=255)
    files = models.ManyToManyField('FileCurveSet')
    date = models.DateField(auto_now_add=True)
    disp_type = 'file set'

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    def getNewCurveSet(self):
        newcs = CurveSet(
            name=self.name,
        )
        newcs.save()
        for file_ in self.files.all():
            newcs.curvesData.add(*file_.curvesData.all())
        for file_ in self.files.all():
            for an in file_.analytes.all():
                newcs.analytes.add(an)
                newcs.analytesConc[an.id] = {}
                newcs.analytesConcUnits[an.id] = file_.analytesConcUnits[an.id]
                for cdid, concvalue in file_.analytesConc[an.id].items():
                    newcs.analytesConc[an.id][cdid] = concvalue
        for an in newcs.analytes.all():
            anconc = newcs.analytesConc[an.id]
            for cd in newcs.curvesData.all():
                anconc[cd.id] = anconc.get(cd.id, 0)
            newcs.analytesConc[an.id] = anconc
        newcs.save()
        return newcs

    def getUrl(self):
        return reverse('showFileSet', args=[self.id])

    def getDelUrl(self):
        return reverse('deleteFileSet', args=[self.id])

    def __str__(self):
        return str(self.id) + ': ' + self.name

    def export(self):
        cds = []
        for f in self.files.all():
            cds.extend(f.curvesData.all())
        return exportCDasFile(cds)

    def getHtmlDetails(self):
        user = manager.helpers.functions.getUser()
        ret = ''.join([
            '<li>Object ID: %d</li>' % self.id,
            '<li>Owner: %s</li>' % self.owner,
            '<li>Permissions: %s</li>' % ', '.join([x for x in get_user_perms(user, self)]),
            '<li>Date: %s</li>' % self.date.strftime("%Y-%m-%d"),
        ])
        return ret


class Curve(VoltPyModel):
    class Param(IntEnum):
        PARAMNUM = 64
        VOL_CMAX = 50  # maximum number of curves in ".vol" file (not in .volt)
        VOL_PMAX = 62  # number of parameters of each curve in ".vol" file

        method = 0  # measurment method
        method_scv = 0
        method_npv = 1
        method_dpv = 2
        method_sqw = 3
        method_lsv = 4

        sampl = 1  # type of sampling (usually single sampling for SCV/LSV and double sampling for NPV/DPV/SQW)
        sampl_single = 0
        sampl_double = 1

        el23 = 2  # cell setup dummy = internal
        el23_dummy = 2
        el23_two = 0
        el23_three = 1

        aver = 3  # average the curve for  # of measuremnts

        messc = 4  # cyclicity of measurement
        messc_single = 0
        messc_cyclic = 1
        messc_multicyclic = 2

        crange = 5  # current range (other for micro and other for marco)
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

        mespv = 6   # polarographic (DME) or voltamperometric (other)
        mespv_polarography = 0
        mespv_voltamperometry = 1

        electr = 7   # type of electrode used
        electr_macro = 0
        electr_dme = 0
        electr_solid = 1
        electr_cgmde = 2
        electr_micro = 3
        electr_microDme = 3   # does not exists IRL
        electr_microSolid = 4
        electr_microCgmde = 5
        electr_multi = 6
        electr_multiSolid = 6

        multi = 8   # multielectrode measurement (with m164 electrode stand) -- bitewise description of aquisition channels
        Ep = 9      # start potential [mV]
        Ek = 10     # end potential [mV]
        Estep = 11   # potential step [mV]
        dEdt = 11    # lsv potential change rate (according to lsv_stepE and lsv_time)
        E0 = 12      # NPV base potential [mV]
        dE = 12      # DPV/SQW impulse potential [mV]
        EstartLSV = 12      # LSV multicyclic starting potential [mV]
        tp = 13      # probing time [ms]
        tw = 14      # waiting time [ms]
        tk = 15      # unknown [ms]
        td = 15      # before first potential step apply potential [ms]
        ts = 15      # LSV multicyclic time of starting potential
        ptnr = 16    # number of points of the curve
        kn = 17      # hammer (knock power?)
        mix = 18     # mixer speed

        breaknr = 19   # number of interruput (eg. preconcentration) 0-7
        breakmin = 20   # time in [min] of each interrupt (from 20 to 26)
        breaksec = 27   # time in [sec] of each interrupt (from 27 to 34)
        breakE = 34     # potential in [sec] of each interrupt (from 34 to 40)

        impnr = 41   # /* offset of nr of imp. - KER-KW  */
        imptime = 42   # /* offset of impulse time         */
        inttime = 43   # /* offset of interrupt time       */
        gtype = 44   # /* offset of type of generation   */
        maxse = 45   # /* nr of impulse in max. drop */

        param46 = 46   # not in use

        inf_smooth = 47   # was curve smoothed
        inf_smooth_no = 0
        inf_smooth_yes = 1

        inf_bkgs = 48   # was background subtracted
        inf_bkgs_no = 0
        inf_bkgs_yes = 1

        inf_move = 49   # was the baseline moved
        inf_move_no = 0
        inf_move_yes = 1

        sti = 50   # stirrer speed
        kp = 51    # knock power
        kpt = 52   # knock pulse time

        Escheck = 53   # use Es potential for LSV measurement
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
            0.125, 0.25, 0.25, 0.125, 0.25, 0.5, 0.25, 0.5, 1.0, 0.25, 0.5, 1.0, 2.0, 5.0
        ]
        LSVtime = [  # time [ms]
            120, 120, 60, 20, 20, 20, 5, 5, 5, 1, 1, 1, 1, 1
        ]

    curveFile = models.ForeignKey('FileCurveSet', on_delete=models.CASCADE)
    orderInFile = models.IntegerField()
    name = models.TextField()
    comment = models.TextField()
    params = PickledObjectField()  # JSON List
    date = models.DateField(auto_now=False, auto_now_add=False)
    disp_type = 'curve'

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    def __str__(self):
        return ''. join([
            '<div style="display: inline; margin: 0px; padding: 0px">',
            '<abbr title="Comment: ',
            self.comment,
            '">',
            self.name,
            '</abbr><br /><sup style="font-size: x-small; white-space: nowrap;">',
            self.curveFile.__str__(),
            '</sup></div>'
        ])


class CurveIndex(VoltPyModel):
    curve = models.OneToOneField(Curve, on_delete=models.CASCADE, related_name='index')
    potential_min = models.FloatField()  # in mV
    potential_max = models.FloatField()  # in mV
    potential_step = models.FloatField()  # in mV
    time_min = models.FloatField()  # in ms
    time_max = models.FloatField()  # in ms
    time_step = models.FloatField()  # is ms
    current_min = models.FloatField()  # in mV
    current_max = models.FloatField()  # in mV
    current_range = models.FloatField()  # in mV
    samplingRate = models.IntegerField()  # in kHz

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )


class SamplingData(models.Model):
    data = SimpleNumpyField(null=True, default=None)


class CurveData(VoltPyModel):
    curve = models.ForeignKey(Curve, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    time = SimpleNumpyField(null=True, default=None)
    potential = SimpleNumpyField(null=True, default=None)
    current = SimpleNumpyField(null=True, default=None)
    basedOn = models.ForeignKey('CurveData', null=True, default=None, on_delete=models.DO_NOTHING)
    processedWith = models.ForeignKey('Processing', null=True, default=None, on_delete=models.DO_NOTHING)
    _currentSamples = models.ForeignKey(SamplingData, on_delete=models.DO_NOTHING, default=None, null=True)
    __currentSamplesChanged = False
    disp_type = 'data'

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    @property
    def pointsNumber(self):
        return len(self.potential)

    @property
    def samplesNumber(self):
        return len(self._currentSamples.data)

    @property
    def currentSamples(self):
        if self._currentSamples is None:
            sd = SamplingData()
            sd.save()
            self._currentSamples = sd
        return self._currentSamples.data

    @currentSamples.setter
    def currentSamples(self, value):
        self.__currentSamplesChanged = True
        sd = SamplingData()
        sd.data = value
        sd.save()
        self._currentSamples = sd

    @overrides
    def __init__(self, *args, **kwargs):
        cs = kwargs.pop('currentSamples', None)
        super(CurveData, self).__init__(*args, **kwargs)
        if cs is not None:
            self.currentSamples = cs
        
    @overrides
    def save(self, *args, **kwargs):
        if self.__currentSamplesChanged:
            self._currentSamples.save()
            self.__currentSamplesChanged = False
        self.potential = np.array(self.potential)
        self.current = np.array(self.current)
        self.time = np.array(self.time)
        super().save(*args, **kwargs)

    def getCopy(self):
        newcd = copy(self)
        newcd.id = None
        newcd.pk = None
        newcd.date = None
        newcd.basedOn = self
        newcd.save()
        return newcd

    def getProcessingHistory(self):
        steps = []
        c = self
        while True:
            if c.processedWith.deleted is False:
                steps.append(c.processedWith)
            if c.basedOn is not None:
                c = c.basedOn
            else:
                break
        return steps

    def xValue2Index(self, value):
        diffvec = np.abs(np.subtract(self.xVector, value))
        index = np.argmin(diffvec)
        return index

    @property
    def xVector(self):
        user = manager.helpers.functions.getUser()
        onx = user.profile.show_on_x
        if onx == 'P':
            return self.potential
        if onx == 'T':
            return self.time
        if onx == 'S':
            return range(len(self.currentSamples))

    @xVector.setter
    def xVector(self, val):
        user = manager.helpers.functions.getUser()
        onx = user.profile.show_on_x
        if onx == 'P':
            self.potential = val
        if onx == 'T':
            self.time = val
        if onx == 'S':
            pass

    @property
    def yVector(self):
        user = manager.helpers.functions.getUser()
        onx = user.profile.show_on_x
        if onx == 'P' or onx == 'T':
            return self.current
        if onx == 'S':
            return self.currentSamples

    @yVector.setter
    def yVector(self, val):
        user = manager.helpers.functions.getUser()
        onx = user.profile.show_on_x
        if onx == 'P' or onx == 'T':
            self.current = val
        if onx == 'S':
            self.currentSamples = val


class Analyte(VoltPyModel):
    name = models.CharField(max_length=125, unique=True)
    atomicMass = models.FloatField(null=True, default=None)  # to calculate between mol and wight

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    def __str__(self):
        return self.name


class CurveSet(VoltPyModel):
    minusOneSS = b'\xE2\x81\xBB\xC2\xB9'.decode("utf-8", "replace")
    cdot = b'\xC2\xB7'.decode("utf-8", "replace")
    CONC_UNITS = (
        ('9g', 'ng{cdot}L{ssm1}'.format(cdot=cdot, ssm1=minusOneSS)),
        ('6g', 'µg{cdot}L{ssm1}'.format(cdot=cdot, ssm1=minusOneSS)),
        ('3g', 'mg{cdot}L{ssm1}'.format(cdot=cdot, ssm1=minusOneSS)),
        ('0g', 'g{cdot}L{ssm1}'.format(cdot=cdot, ssm1=minusOneSS)),
        ('9M', 'nM'),
        ('6M', 'µM'),
        ('3M', 'mM'),
        ('0M', 'M')
    )
    CONC_UNIT_DEF = '0g'

    name = models.CharField(max_length=255)
    date = models.DateField(auto_now_add=True)
    curvesData = models.ManyToManyField(CurveData, related_name="curvesData")
    undoCurvesData = models.ManyToManyField(CurveData, related_name="undoCurvesData")
    analytes = models.ManyToManyField(Analyte, related_name="analytes")
    undoAnalytes = models.ManyToManyField(Analyte, related_name="undoAnalytes")
    analytesConc = PickledObjectField(default={})  # dictionary key is analyte id
    undoAnalytesConc = PickledObjectField(default={})  # dictionary key is analyte id
    analytesConcUnits = PickledObjectField(default={})  # dictionary key is analyte id
    undoAnalytesConcUnits = PickledObjectField(default={})  # dictionary key is analyte id
    undoProcessing = models.ForeignKey('Processing', null=True, default=None, on_delete=models.DO_NOTHING)
    disp_type = 'curve set'

    def getCopy(self):
        newcs = CurveSet(
            name=self.name+'_copy',
            analytesConc=self.analytesConc,
            analytesConcUnits=self.analytesConcUnits
        )
        newcs.save()
        newcs.analytes.set(self.analytes.all())
        newcs.curvesData.set(self.curvesData.all())
        newcs.save()
        for pr in Processing.objects.filter(curveSet=self, deleted=False, completed=True):
            newpr = pr.getCopy(curveSet=newcs)
            newpr.save()
        return newcs

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    @property
    def locked(self) -> bool:
        if Analysis.objects.filter(curveSet=self, deleted=False).exists():
            return True
        return False

    def removeCurve(self, curveData: CurveData):
        self.curvesData.remove(curveData)
        for k, v in self.analytesConc.items():
            v.pop(curveData.id, None)

    def addCurve(self, curveData: CurveData, concDict={}):
        concValues = concDict.get('values', {})
        concUnits = concDict.get('units', {})
        if not self.curvesData.filter(id=curveData.id).exists():
            self.curvesData.add(curveData)
        self.setCurveConcDict(curveData, concValues, concDict)

    def setCurveConcDict(self, curveData: CurveData, curveConcDict: Dict, curveConcUnits: Dict):
        newAnalytes = list(set(curveConcDict.keys()) - set(self.analytesConc.keys()))
        for na in newAnalytes:
            self.analytes.add(Analyte.objects.get(id=na))
            self.analytesConc[na] = self.analytesConc.get(na, {})
            self.analytesConcUnits[na] = self.analytesConcUnits.get(na, self.CONC_UNIT_DEF)
            for cd in self.curvesData.all():
                self.analytesConc[na][cd.id] = 0.0
        for k, v in self.analytesConc.items():
            v[curveData.id] = curveConcDict.get(k, 0.0)

    def getCurveConcDict(self, curveData: CurveData) -> Dict:
        """
        Returns dict of {'values': conc_values<dict>, 'units': conc_units<dict>}
        """
        ret = {}
        for k, v in self.analytesConc.items():
            ret[k] = v.get(curveData.id, 0.0)
        return {'values': ret, 'units': self.analytesConcUnits}

    def __str__(self):
        return '%s' % self.name

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
        # TODO: Undo removes also processing method ! (store id somewhere?)
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
            self.undoProcessing.error = 'Undone'
            self.undoProcessing.deleted = True
            self.undoProcessing.save()
            self.undoProcessing = None
        self.save()

    def hasUndo(self):
        if any([
            len(self.undoCurvesData.all()) == 0,
            self.locked is True
        ]):
            return False
        else:
            return True
        
    def getConc(self, analyte_id: int) -> List:
        """
        Returns list of concentration for given analyte and all current curvesData.
        """
        conc = []
        for cd in self.curvesData.all():
            conc.append(self.analytesConc.get(analyte_id, {}).get(cd.id, 0))
        return conc
        
    def getUncorrelatedConcs(self) -> List:
        """
        Returns list of list of concentrations of analytes which are not correlated.
        """
        concs_different = np.empty(0)
        for an in self.analytes.all():
            an_conc = []
            for cd in self.curvesData.all():
                an_conc.append(self.analytesConc[an.id].get(cd.id, 0))
            if concs_different.shape[0] == 0:
                concs_different = np.array([an_conc])
            else:
                for conc in concs_different:
                    rabs = np.abs(np.corrcoef(conc, an_conc)[0, 1])
                    if rabs > 0.9999:
                        break
                else:
                    concs_different = np.vstack((concs_different, an_conc))
        return concs_different

    def getProcessingHistory(self):
        return Processing.objects.filter(curveSet=self, deleted=False, completed=True).order_by('id')

    def export(self):
        return exportCDasFile(self.curvesData.all())

    def getUrl(self):
        return reverse('showCurveSet', args=[self.id])

    def getDelUrl(self):
        return reverse('deleteCurveSet', args=[self.id])

    def getHtmlDetails(self):
        proc_hist = ''
        for p in self.getProcessingHistory():
            proc_hist += ''.join(['<li>', str(p), '</li>']) 

        filesUsed = set()
        for cd in self.curvesData.all():
            filesUsed.add(cd.curve.curveFile)
        uses_files = ''
        for f in filesUsed:
            uses_files += '<li><a href="%s">%s</a></li>' % (f.getUrl(), str(f))

        user = manager.helpers.functions.getUser()
        ret = ''.join([
            '<li>Object ID: %d</li>' % self.id,
            '<li>Permissions: %s</li>' % ', '.join([x for x in get_user_perms(user, self)]),
            '<li>Owner: %s</li>' % self.owner,
            '<li>Date: %s</li>' % self.date.strftime("%Y-%m-%d"),
            '<li>Processed with:<ul>%s</ul></li>' % proc_hist,
            '<li>Uses curves from:<ul>%s</ul></li>' % uses_files,
        ])
        return ret


class FileCurveSet(CurveSet):
    fileName = models.TextField()
    fileDate = models.DateField(auto_now=False, auto_now_add=False)  # Each file has its curveset
    uploadDate = models.DateField(auto_now_add=True)
    disp_type = 'file'

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    def getNewCurveSet(self):
        newcs = CurveSet(
            name=self.name,
            analytesConc=self.analytesConc,
            analytesConcUnits=self.analytesConcUnits
        )
        newcs.save()
        newcs.analytes.set(self.analytes.all())
        newcs.curvesData.set(self.curvesData.all())
        newcs.save()
        return newcs

    def getUrl(self):
        return reverse('showCurveFile', args=[self.id])

    def getDelUrl(self):
        return reverse('deleteCurveFile', args=[self.id])

    def getHtmlDetails(self):
        user = manager.helpers.functions.getUser()
        fs = self.fileset_set.all()[0]
        ret = ''.join([
            '<li>Object ID: %d</li>' % self.id,
            '<li>Permissions: %s</li>' % ', '.join([x for x in get_user_perms(user, self)]),
            '<li>Owner: %s</li>' % self.owner,
            '<li>Date: %s</li>' % self.date.strftime("%Y-%m-%d"),
            '<li>File name: %s</li>' % self.fileName,
            '<li>File date: %s</li>' % self.fileDate,
            '<li>File set: <a href="%s">%s</a></li>' % (fs.getUrl(), fs.name)
        ])
        return ret
    
    def __str__(self):
        fs = self.fileset_set.all()[0]
        if fs.name != '':
            return '%s: %s' % (fs.name, self.name)
        else:
            return '%s' % self.name


class Analysis(VoltPyModel):
    curveSet = models.ForeignKey(CurveSet, on_delete=models.DO_NOTHING)
    date = models.DateField(auto_now_add=True)
    appliesModel = models.ForeignKey('Analysis', default=None, null=True, on_delete=models.DO_NOTHING)
    customData = PickledObjectField(default={})
    stepsData = PickledObjectField(default={})
    analytes = models.ManyToManyField(Analyte)
    name = models.CharField(max_length=255)
    method = models.CharField(max_length=255)
    methodDisplayName = models.TextField()
    active_step_num = models.IntegerField(default=0, null=True)
    error = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)
    disp_type = "analysis"

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    def save(self, *args, **kwargs):
        user = manager.helpers.functions.getUser()
        if not user.has_perm('rw', self.curveSet):
            raise VoltPyNotAllowed('Operation not allowed.')
        super().save(*args, **kwargs)

    def __str__(self):
        return '%s %s: %s' % (self.date, self.methodDisplayName, self.name)

    def getUrl(self):
        if self.completed:
            return reverse('showAnalysis', args=[self.id])
        else:
            return reverse('analyze', args=[self.id])

    def getDelUrl(self):
        return reverse('deleteAnalysis', args=[self.id])

    def getHtmlDetails(self):
        user = manager.helpers.functions.getUser()
        ret = ''.join([
            '<li>Object ID: %d</li>' % self.id,
            '<li>Permissions: %s</li>' % ', '.join([x for x in get_user_perms(user, self)]),
            '<li>Owner: %s</li>' % self.owner,
            '<li>Date: %s</li>' % self.date.strftime("%Y-%m-%d %H:%M"),
            '<li>Method: %s</li>' % self.methodDisplayName,
            '<li>Curve Set: <a href="%s">%s</a></li>' % (self.curveSet.getUrl(), self.curveSet),
        ])
        return ret

    def getCopy(self):
        newan = copy(self)
        newan.id = None
        newan.pk = None
        newan.date = None
        newan.deleted = False
        newan.curveSet = None
        newan.save()
        return newan


class Processing(VoltPyModel):
    curveSet = models.ForeignKey(CurveSet, on_delete=models.DO_NOTHING)
    date = models.DateField(auto_now_add=True)
    appliesModel = models.ForeignKey('Processing', default=None, null=True, on_delete=models.DO_NOTHING)
    customData = PickledObjectField(default={})
    stepsData = PickledObjectField(default={})
    analytes = models.ManyToManyField(Analyte)
    name = models.CharField(max_length=255)
    method = models.CharField(max_length=255)
    methodDisplayName = models.TextField()
    active_step_num = models.IntegerField(default=0, null=True)
    error = models.CharField(max_length=255)
    completed = models.BooleanField(default=0)

    def save(self, *args, **kwargs):
        user = manager.helpers.functions.getUser()
        if not user.has_perm('rw', self.curveSet):
            raise VoltPyNotAllowed('Operation not allowed.')
        super().save(*args, **kwargs)

    def getCopy(self, curveSet):
        newp = copy(self)
        newp.id = None
        newp.pk = None
        newp.curveSet = curveSet
        newp.appliesModel = None
        newp.save()
        return newp

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    def __str__(self):
        return '%s: %s' % (self.date, self.methodDisplayName)

    def getUrl(self):
        return reverse('showCurveSet', args=[self.curveSet.id])


class SharedLink(VoltPyModel):
    PERMISSIONS = (('rw', 'Read Write'), ('ro', 'Read Only'))
    creation_date = models.DateField(auto_now_add=True)
    users = models.ManyToManyField(User, related_name='shared_link')
    object_type = models.CharField(max_length=32)
    object_id = models.IntegerField()
    link = models.CharField(max_length=255, unique=True)
    permissions = models.CharField(choices=PERMISSIONS, max_length=6)
    name = models.CharField(max_length=255, default=None, null=True)

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    def __str__(self):
        return '%s: %s' % (self.link, self.users.all())

    def getLink(self):
        from django.contrib.sites.models import Site
        return 'https://' + Site.objects.get_current().domain + reverse('shareLink',args=[self.link])

    def addUser(self, user):
        # TODO: HACK find a better way to baypass permission check (?)
        gu = manager.helpers.functions.getUser
        manager.helpers.functions.getUser = lambda: self.owner
        try:
            self.users.add(user)
        finally:
            manager.helpers.functions.getUser = gu
        self.save
