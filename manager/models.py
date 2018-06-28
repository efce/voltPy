import io
import numpy as np
from copy import copy
from enum import IntEnum
from typing import Dict, List
from overrides import overrides
from guardian.shortcuts import get_user_perms
from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.db.models import Q
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
    new_email = models.CharField(max_length=255, null=True, default=None)
    new_email_confirmation_hash = models.CharField(max_length=64, null=True, default=None)
    show_on_x = models.CharField(max_length=1, choices=ONX_OPTIONS, default='P')
    starred_processing = PickledObjectField(default=[])
    starred_analysis = PickledObjectField(default=[])

    @property
    def lastUsedProcessing(self, number=3) -> List:
        return self._lastUsed(Processing, number)

    @property
    def lastUsedAnalysis(self, number=3) -> List:
        return self._lastUsed(Analysis, number)

    def _lastUsed(self, Klass, number):
        user = manager.helpers.functions.get_user()
        qury = Klass.filter(owner=user).order_by('-id').values('method', 'method_display_name')
        ret = []
        for qr in qury:
            if qr not in ret:
                ret.append(qr)
                if len(ret) >= number:
                    break
        return ret


@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()


def get_user_name(self):
    user = self
    if user is None:
        return '[not logged in]'
    elif user.groups.filter(name='temp_users').exists():
        return '[temp]'
    return user.username
User.__str__ = get_user_name


def displayable_groups(self):
    if any([
        self is None,
        self.groups.filter(name='temp_users').exists()
    ]):
        return []
    else:
        ret = []
        for g in self.groups.filter(~Q(name='registered_users')):
            ret += g.__str__
        return ret
User.displayable_groups = displayable_groups


class Fileset(VoltPyModel):
    name = models.CharField(max_length=255)
    files = models.ManyToManyField('File')
    date = models.DateField(auto_now_add=True)
    disp_type = 'fileset'

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    def getNewDataset(self):
        newcs = Dataset(
            name=self.name,
        )
        newcs.save()
        for file_ in self.files.all():
            newcs.curves_data.add(*file_.curves_data.all())
        for file_ in self.files.all():
            for an in file_.analytes.all():
                newcs.analytes.add(an)
                newcs.analytes_conc[an.id] = {}
                newcs.analytes_conc_unit[an.id] = file_.analytes_conc_unit[an.id]
                for cdid, concvalue in file_.analytes_conc[an.id].items():
                    newcs.analytes_conc[an.id][cdid] = concvalue
        for an in newcs.analytes.all():
            anconc = newcs.analytes_conc[an.id]
            for cd in newcs.curves_data.all():
                anconc[cd.id] = anconc.get(cd.id, 0)
            newcs.analytes_conc[an.id] = anconc
        newcs.save()
        return newcs

    def getUrl(self):
        return reverse('showFileset', args=[self.id])

    def getDelUrl(self):
        return reverse('deleteFileset', args=[self.id])

    def __str__(self):
        return str(self.id) + ': ' + self.name

    def export(self):
        cds = []
        for f in self.files.all():
            cds.extend(f.curves_data.all())
        return manager.helpers.functions.export_curves_data_as_csv(cds)

    def getHtmlDetails(self):
        user = manager.helpers.functions.get_user()
        ret = ''.join([
            '<li>Object ID: %d</li>' % self.id,
            '<li>Owner: %s</li>' % self.owner,
            '<li>Permissions: %s</li>' % ', '.join([x for x in get_user_perms(user, self)]),
            '<li>Date: %s</li>' % self.date.strftime("%Y-%m-%d"),
        ])
        return ret

    @property
    def analytes(self):
        return Analyte.objects.filter(dataset__in=[x.id for x in self.files.all().only('id')]).distinct()


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

    file = models.ForeignKey('File', on_delete=models.CASCADE)
    order_in_file = models.IntegerField()
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
            self.file.__str__(),
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
    sampling_rate = models.IntegerField()  # in kHz

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
    based_on = models.ForeignKey('CurveData', null=True, default=None, on_delete=models.DO_NOTHING)
    processedWith = models.ForeignKey('Processing', null=True, default=None, on_delete=models.DO_NOTHING)
    _current_samples = models.ForeignKey(SamplingData, on_delete=models.DO_NOTHING, default=None, null=True)
    _crop_beg = models.IntegerField(null=True, default=None)
    _crop_end = models.IntegerField(null=True, default=None)
    __current_samples_changed = False
    disp_type = 'data'

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    @property
    def points_number(self):
        return len(self.current[self._crop_beg:self._crop_end])

    @property
    def samples_number(self):
        return len(self._current_samples.data)

    @property
    def current_samples(self):
        if self._current_samples is None:
            sd = SamplingData()
            sd.save()
            self._current_samples = sd
        return self._current_samples.data

    @overrides
    def __init__(self, *args, **kwargs):
        cs = kwargs.pop('current_samples', None)
        super(CurveData, self).__init__(*args, **kwargs)
        if cs is not None:
            self.current_samples = cs

    @current_samples.setter
    def current_samples(self, value):
        self.__current_samples_changed = True
        sd = SamplingData()
        sd.data = value
        sd.save()
        self._current_samples = sd

    @overrides
    def save(self, *args, **kwargs):
        if self.__current_samples_changed:
            self._current_samples.save()
            self.__current_samples_changed = False
        self.potential = np.array(self.potential)
        self.current = np.array(self.current)
        self.time = np.array(self.time)
        super().save(*args, **kwargs)

    def getCopy(self):
        newcd = copy(self)
        newcd.id = None
        newcd.pk = None
        newcd.date = None
        newcd.based_on = self
        newcd.save()
        return newcd

    def getProcessingHistory(self):
        steps = []
        c = self
        while True:
            if c.processedWith.deleted is False:
                steps.append(c.processedWith)
            if c.based_on is not None:
                c = c.based_on
            else:
                break
        return steps

    def xValue2Index(self, value):
        diffvec = np.abs(np.subtract(self.xVector[self._crop_beg:self._crop_end], value))
        index = np.argmin(diffvec)
        return index

    @property
    def xVector(self):
        user = manager.helpers.functions.get_user()
        onx = user.profile.show_on_x
        if onx == 'P':
            return self.potential[self._crop_beg:self._crop_end]
        if onx == 'T':
            return self.time[self._crop_beg:self._crop_end]
        if onx == 'S':
            return range(len(self.current_samples))

    @xVector.setter
    def xVector(self, val):
        user = manager.helpers.functions.get_user()
        onx = user.profile.show_on_x
        if onx == 'P':
            self.potential[self._crop_beg:self._crop_end] = val
        if onx == 'T':
            self.time[self._crop_beg:self._crop_end] = val
        if onx == 'S':
            pass

    @property
    def yVector(self):
        user = manager.helpers.functions.get_user()
        onx = user.profile.show_on_x
        if onx == 'P' or onx == 'T':
            return self.current[self._crop_beg:self._crop_end]
        if onx == 'S':
            return self.current_samples

    @yVector.setter
    def yVector(self, val):
        user = manager.helpers.functions.get_user()
        onx = user.profile.show_on_x
        if onx == 'P' or onx == 'T':
            self.current[self._crop_beg:self._crop_end] = val
        if onx == 'S':
            self.current_samples = val

    def setCrop(self, index_beg: int, index_end: int):
        """
        Changes the displayable area of the plot, use None
        for index to remove cropping on that side of the signal.
        """
        if all([
            index_beg is not None,
            index_end is not None,
            index_beg > index_end
        ]):
            index_end, index_beg = index_beg, index_end

        self._crop_beg = index_beg
        self._crop_end = index_end

    def getCrop(self) -> List:
        return (self._crop_beg, self._crop_end)


class Analyte(VoltPyModel):
    name = models.CharField(max_length=125, unique=True)
    atomic_mass = models.FloatField(null=True, default=None)  # to calculate between mol and wight

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    def __str__(self):
        return self.name


class Dataset(VoltPyModel):
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
    curves_data = models.ManyToManyField(CurveData, related_name="curves_data")
    analytes = models.ManyToManyField(Analyte)
    analytes_conc = PickledObjectField(default={})  # dictionary key is analyte id
    analytes_conc_unit = PickledObjectField(default={})  # dictionary key is analyte id
    undo_curves_data = models.ManyToManyField(CurveData, related_name="undoCurvesData")
    undo_analytes = models.ManyToManyField(Analyte, related_name="undoAnalytes")
    undo_analytes_conc = PickledObjectField(default={})  # dictionary key is analyte id
    undo_analytes_conc_unit = PickledObjectField(default={})  # dictionary key is analyte id
    undo_processing = models.ForeignKey(
        'Processing',
        null=True,
        default=None,
        on_delete=models.DO_NOTHING,
        related_name='undoProcessing'
    )
    disp_type = 'dataset'

    def getCopy(self):
        newcs = Dataset(
            name=self.name + '_copy',
            analytes_conc=self.analytes_conc,
            analytes_conc_unit=self.analytes_conc_unit
        )
        newcs.save()
        newcs.analytes.set(self.analytes.all())
        newcs.curves_data.set(self.curves_data.all())
        newcs.save()
        for pr in Processing.objects.filter(dataset=self, deleted=False, completed=True):
            newpr = pr.getCopy(dataset=newcs)
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
        if Analysis.objects.filter(dataset=self, deleted=False).exists():
            return True
        return False

    def removeCurve(self, cd: CurveData):
        self.curves_data.remove(cd)
        for k, v in self.analytes_conc.items():
            v.pop(cd.id, None)

    def addCurve(self, cd: CurveData, conc_dict={}):
        concValues = conc_dict.get('values', {})
        concUnits = conc_dict.get('units', {})
        if not self.curves_data.filter(id=cd.id).exists():
            self.curves_data.add(cd)
        self.setCurveConcDict(cd, concValues, conc_dict)

    def setCurveConcDict(self, cd: CurveData, curve_conc_dict: Dict, curve_conc_units: Dict):
        newAnalytes = list(set(curve_conc_dict.keys()) - set(self.analytes_conc.keys()))
        for na in newAnalytes:
            self.analytes.add(Analyte.objects.get(id=na))
            self.analytes_conc[na] = self.analytes_conc.get(na, {})
            self.analytes_conc_unit[na] = self.analytes_conc_unit.get(na, self.CONC_UNIT_DEF)
            for cd in self.curves_data.all():
                self.analytes_conc[na][cd.id] = 0.0
        for k, v in self.analytes_conc.items():
            v[cd.id] = curve_conc_dict.get(k, 0.0)

    def getCurveConcDict(self, curveData: CurveData) -> Dict:
        """
        Returns dict of {'values': conc_values<dict>, 'units': conc_units<dict>}
        """
        ret = {}
        for k, v in self.analytes_conc.items():
            ret[k] = v.get(curveData.id, 0.0)
        return {'values': ret, 'units': self.analytes_conc_unit}

    def __str__(self):
        return '%s' % self.name

    def prepareUndo(self, processing_instance=None):
        self.undo_curves_data.clear()
        for cd in self.curves_data.all():
            self.undo_curves_data.add(cd)
        self.undo_analytes.clear()
        for a in self.analytes.all():
            self.undo_analytes.add(a)
        self.undo_analytes_conc = copy(self.analytes_conc)
        self.undo_analytes_conc_unit = copy(self.analytes_conc_unit)
        self.undo_processing = processing_instance
        self.save()

    def undo(self):
        if not self.hasUndo():
            return
        self.curves_data.clear()
        for cd in self.undo_curves_data.all():
            self.curves_data.add(cd)
        self.analytes.clear()
        for a in self.undo_analytes.all():
            self.analytes.add(a)
        self.analytes_conc = copy(self.undo_analytes_conc)
        self.analytes_conc_unit = copy(self.undo_analytes_conc_unit)
        self.undo_curves_data.clear()
        self.undo_analytes.clear()
        self.undo_analytes_conc.clear()
        self.undo_analytes_conc_unit.clear()
        if self.undo_processing is not None:
            self.undo_processing.error = 'Undone'
            self.undo_processing.deleted = True
            self.undo_processing.save()
            self.undo_processing = None
        self.save()

    def hasUndo(self) -> bool:
        if any([
            len(self.undo_curves_data.all()) == 0,
            self.locked is True
        ]):
            return False
        else:
            return True
        
    def getConc(self, analyte_id: int) -> List:
        """
        Returns list of concentration for given analyte and all current curves_data.
        """
        conc = []
        for cd in self.curves_data.all():
            conc.append(self.analytes_conc.get(analyte_id, {}).get(cd.id, 0))
        return conc
        
    def getUncorrelatedConcs(self) -> List:
        """
        Returns list of list of concentrations of analytes which are not correlated.
        """
        concs_different = np.empty(0)
        for an in self.analytes.all():
            an_conc = []
            for cd in self.curves_data.all():
                an_conc.append(self.analytes_conc[an.id].get(cd.id, 0))
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
        return Processing.objects.filter(dataset=self, deleted=False, completed=True).order_by('id')

    def export(self):
        return manager.helpers.functions.export_curves_data_as_csv(self.curves_data.all())

    def getUrl(self):
        return reverse('showDataset', args=[self.id])

    def getDelUrl(self):
        return reverse('deleteDataset', args=[self.id])

    def getHtmlDetails(self):
        proc_hist = ''
        for p in self.getProcessingHistory():
            proc_hist += ''.join(['<li>', str(p), '</li>']) 

        files_used = set()
        for cd in self.curves_data.all():
            files_used.add(cd.curve.file)
        uses_files = ''
        for f in files_used:
            uses_files += '<li><a href="%s">%s</a></li>' % (f.getUrl(), str(f))

        user = manager.helpers.functions.get_user()
        ret = ''.join([
            '<li>Object ID: %d</li>' % self.id,
            '<li>Status: %s</li>' % ('Locked' if self.locked else 'Unlocked'),
            '<li>Permissions: %s</li>' % ', '.join([x for x in get_user_perms(user, self)]),
            '<li>Owner: %s</li>' % self.owner,
            '<li>Date: %s</li>' % self.date.strftime("%Y-%m-%d"),
            '<li>Processed with:<ul>%s</ul></li>' % proc_hist,
            '<li>Uses curves from:<ul>%s</ul></li>' % uses_files,
        ])
        return ret


class File(Dataset):
    filename = models.TextField()
    file_date = models.DateField(auto_now=False, auto_now_add=False)  # Each file has its dataset
    disp_type = 'file'

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    def getNewDataset(self):
        newcs = Dataset(
            name=self.name,
            analytes_conc=self.analytes_conc,
            analytes_conc_unit=self.analytes_conc_unit
        )
        newcs.save()
        newcs.analytes.set(self.analytes.all())
        newcs.curves_data.set(self.curves_data.all())
        newcs.save()
        return newcs

    def getUrl(self):
        return reverse('showFile', args=[self.id])

    def getDelUrl(self):
        return reverse('deleteFile', args=[self.id])

    def getHtmlDetails(self):
        user = manager.helpers.functions.get_user()
        fs = self.fileset_set.all()[0]
        ret = ''.join([
            '<li>Object ID: %d</li>' % self.id,
            '<li>Permissions: %s</li>' % ', '.join([x for x in get_user_perms(user, self)]),
            '<li>Owner: %s</li>' % self.owner,
            '<li>Date: %s</li>' % self.date.strftime("%Y-%m-%d"),
            '<li>File date: %s</li>' % self.file_date,
            '<li>Filename: %s</li>' % self.filename,
            '<li>Fileset: <a href="%s">%s</a></li>' % (fs.getUrl(), fs.name)
        ])
        return ret
    
    def __str__(self):
        fs = self.fileset_set.all()[0]
        if fs.name != '':
            return '%s: %s' % (fs.name, self.name)
        else:
            return '%s' % self.name


class ModelMethod(VoltPyModel):
    dataset = models.ForeignKey(Dataset, on_delete=models.DO_NOTHING)
    date = models.DateField(auto_now_add=True)
    applies_model = models.ForeignKey('Analysis', default=None, null=True, on_delete=models.DO_NOTHING)
    custom_data = PickledObjectField(default={})
    steps_data = PickledObjectField(default={})
    analytes = models.ManyToManyField(Analyte)
    name = models.CharField(max_length=255)
    method = models.CharField(max_length=255)
    method_display_name = models.TextField()
    active_step_num = models.IntegerField(default=0, null=True)
    error = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)

    class Meta:
        abstract = True


class Analysis(ModelMethod):
    disp_type = "analysis"

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    def save(self, *args, **kwargs):
        user = manager.helpers.functions.get_user()
        if not user.has_perm('rw', self.dataset):
            raise VoltPyNotAllowed('Operation not allowed.')
        super().save(*args, **kwargs)

    def __str__(self):
        return '%s %s: %s' % (self.date, self.method_display_name, self.name)

    def getUrl(self):
        if self.completed:
            return reverse('showAnalysis', args=[self.id])
        else:
            return reverse('analyze', args=[self.id])

    def getDelUrl(self):
        return reverse('deleteAnalysis', args=[self.id])

    def getHtmlDetails(self):
        user = manager.helpers.functions.get_user()
        ret = ''.join([
            '<li>Object ID: %d</li>' % self.id,
            '<li>Permissions: %s</li>' % ', '.join([x for x in get_user_perms(user, self)]),
            '<li>Owner: %s</li>' % self.owner,
            '<li>Date: %s</li>' % self.date.strftime("%Y-%m-%d %H:%M"),
            '<li>Method: %s</li>' % self.method_display_name,
            '<li>Dataset: <a href="%s">%s</a></li>' % (self.dataset.getUrl(), self.dataset),
        ])
        return ret

    def getCopy(self):
        newan = copy(self)
        newan.id = None
        newan.pk = None
        newan.date = None
        newan.deleted = False
        newan.dataset = None
        newan.save()
        return newan


class Processing(ModelMethod):
    disp_type = 'processing'

    def save(self, *args, **kwargs):
        user = manager.helpers.functions.get_user()
        if not user.has_perm('rw', self.dataset):
            raise VoltPyNotAllowed('Operation not allowed.')
        super().save(*args, **kwargs)

    def getCopy(self, dataset):
        newp = copy(self)
        newp.id = None
        newp.pk = None
        newp.dataset = dataset
        newp.applies_model = None
        newp.save()
        return newp

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

    def __str__(self):
        return '%s: %s' % (self.date, self.method_display_name)

    def getUrl(self):
        return reverse('showDataset', args=[self.dataset.id])


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
        return '<Sharing: {klass} {kid}: {name}; permission: {perm}>'.format(
            klass=self.object_type,
            kid=self.object_id,
            name=self.getSharedObject().name,
            perm=self.permissions,
        )

    def getLink(self):
        from django.contrib.sites.models import Site
        return ''.join([
            'https://',
            Site.objects.get_current().domain,
            reverse('shareLink', args=[self.link])
        ])

    def addUser(self, user):
        # TODO: HACK find a better way to baypass permission check (?)
        gu = manager.helpers.functions.get_user
        manager.helpers.functions.get_user = lambda: self.owner
        try:
            self.users.add(user)
        finally:
            manager.helpers.functions.get_user = gu
        self.save

    def user_names(self):
        unames = [x.__str__() for x in self.users.all()]
        if not unames:
            return None
        return list(set(unames))
            
    def getSharedObject(self):
        importlib = __import__('importlib')
        load_models = importlib.import_module('manager.models')
        obj_class = getattr(load_models, self.object_type)
        try:
            obj = obj_class.objects.get(id=self.object_id)
            return obj
        except ObjectDoesNotExist as e:
            raise VoltPyDoesNotExists
