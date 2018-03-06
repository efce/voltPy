from django.db import models
from picklefield.fields import PickledObjectField
from django.urls import reverse


class Group(models.Model):
    name = models.TextField(unique=True)
    
    def __str__(self):
        return "id: %i; name: %s" % (self.id, self.name)


class User(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField(unique=True)
    groups = models.ManyToManyField(Group)

    def __str__(self):
        return self.name


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


class FileSet(models.Model):
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User)
    name = models.TextField()
    files = models.ManyToManyField(CurveFile)
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


class Curve(models.Model):
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
    processing = models.ForeignKey('Processing', null=True, default=None, on_delete=models.DO_NOTHING) #What it was processed with
    basedOn = models.ForeignKey('CurveData', null=True, default=None, on_delete=models.DO_NOTHING)
    time = PickledObjectField() # JSON List 
    potential = PickledObjectField() # JSON List 
    current = PickledObjectField() # JSON List 
    currentSamples = PickledObjectField() # JSON List 

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
    curvesData = models.ManyToManyField(CurveData)
    analytes = models.ManyToManyField(Analyte)
    analytesConc = PickledObjectField(default={}) # dictionary key is analyte id
    analytesConcUnits = PickledObjectField(default={}) # dictionary key is analyte id
    deleted = models.BooleanField(default=False)

    def isOwnedBy(self, user):
        return (self.owner == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user) #and not self.locked

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)

    def __str__(self):
        return "%s" % self.name


class Analysis(models.Model):
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    curveSet = models.ForeignKey(CurveSet, on_delete=models.DO_NOTHING)
    date = models.DateField(auto_now_add=True)
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

    def getRedirectURL(self, user):
        return reverse('showAnalysis', args=[ user.id, self.id ])

class Processing(models.Model):
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    curveSet = models.ForeignKey(CurveSet, on_delete=models.DO_NOTHING)
    date = models.DateField(auto_now_add=True)
    customData = PickledObjectField(default={})
    stepsData = PickledObjectField(default={})
    analytes = models.ManyToManyField(Analyte)
    name = models.TextField()
    method = models.TextField()
    active_step_num  = models.IntegerField(default=0, null=True)
    deleted = models.BooleanField(default=0)
    completed = models.BooleanField(default=0)

    def __str__(self):
        return "%s: %s" % (self.date, self.method);

    class META:
        ordering = ('date')

    def isOwnedBy(self, user):
        return (self.owner == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user)

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)

    def getRedirectURL(self, user):
        return reverse('showCurveSet', args=[ user.id, self.curveSet.id ])


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
