from django.db import models
from .compressedjsonfield import CompressedJSONField


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
    owner = models.ForeignKey(User)
    name = models.TextField()
    comment = models.TextField()
    filename = models.TextField()
    fileDate = models.DateField()
    uploadDate = models.DateField()
    deleted = models.BooleanField(default=0)

    def __str__(self):
        return self.name + ": " + self.filename

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
    name    = models.TextField()
    comment = models.TextField()
    params  = CompressedJSONField()# JSON List 
    date = models.DateField()
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
    potential_min = models.FloatField()
    potential_max = models.FloatField()
    potential_step = models.FloatField()
    time_min = models.FloatField()
    time_max = models.FloatField()
    time_step = models.FloatField()
    current_min = models.FloatField()
    current_max = models.FloatField()
    current_range = models.FloatField()
    probingRate = models.IntegerField()

    def isOwnedBy(self, user):
        return (self.curve.curveFile.owner == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user)

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)


class CurveData(models.Model):
    id = models.AutoField(primary_key=True)
    curve = models.ForeignKey(Curve, on_delete=models.CASCADE)
    date = models.DateField()
    name      = models.TextField()# Name of transformation (empty for unaltered)
    method    = models.TextField()# Field empty when data unaltered
    time = CompressedJSONField()
    potential = CompressedJSONField()# JSON List 
    current   = CompressedJSONField()# JSON List 
    concentration = CompressedJSONField()# JSON List
    concentrationUnits = CompressedJSONField()#JSON List
    probingData = CompressedJSONField()# JSON List 

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
            elif value > len(self.probingData):
                return len(self.probingData)-1
            else:
                return int(value)


class Analyte(models.Model):
    name=models.CharField(max_length=124, unique=True)

    def __str__(self):
        return self.name
    

class AnalyteInCurve(models.Model):
    id = models.AutoField(primary_key=True)
    curve=models.ForeignKey(Curve)
    analyte=models.ForeignKey(Analyte)
    concentration=models.FloatField()

    def isOwnedBy(self, user):
        return (self.curve.curveFile.owner == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user)

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)


class CurveSet(models.Model):
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User)
    name = models.CharField(max_length=128)
    date = models.DateField()
    usedCurveData = models.ManyToManyField(CurveData)
    locked = models.BooleanField(default=0)
    deleted = models.BooleanField(default=0)

    def isOwnedBy(self, user):
        return (self.owner == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user) and not self.locked

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)

    def __str__(self):
        return "%s" % self.name



class Analysis(models.Model):
    curveSet = models.ForeignKey(CurveSet)
    result = models.FloatField(null=True)
    resultStdDev = models.FloatField(null=True)
    corrCoef = models.FloatField(null=True)
    dataMatrix = CompressedJSONField() 
    fitEquation =CompressedJSONField()
    analyte=models.ManyToManyField(Analyte)

    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User)
    parameters = CompressedJSONField(default="")
    date = models.DateField()
    name = models.TextField()
    method = models.TextField()
    step  = models.IntegerField(default=0)
    deleted = models.BooleanField(default=0)
    completed = models.BooleanField(default=0)

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


class Processing(models.Model):
    curves = models.ManyToManyField(Curve)

    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User)
    parameters = CompressedJSONField(default="")
    date = models.DateField()
    name = models.TextField()
    method = models.TextField()
    step  = models.IntegerField(default=0)
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


class OnXAxis(models.Model):
    AVAILABLE = (
            ( 'P', 'Potential'), 
            ( 'T', 'Time'), 
            ( 'S', 'Samples'))
    selected = models.CharField(max_length=1, choices=AVAILABLE, default='P')
    user = models.OneToOneField(User)
    
    def __str__(self):
        return self.selected;

    def isOwnedBy(self, user):
        return (self.user == user)

    def canBeUpdatedBy(self, user):
        return self.isOwnedBy(user)

    def canBeReadBy(self, user):
        return self.isOwnedBy(user)
