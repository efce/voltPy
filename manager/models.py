from django.db import models
from jsonfield import JSONField


class Group(models.Model):
    name = models.TextField(unique=True)
    
    def __str__(self):
        return "id: %i; name: %s" % (self.id, self.name)


class User(models.Model):
    name = models.TextField(unique=True)
    groups = models.ManyToManyField(Group)


class CurveFile(models.Model):
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


class CurveBasic(models.Model):
    curveFile = models.ForeignKey(CurveFile, on_delete=models.CASCADE)
    orderInFile = models.IntegerField()
    name    = models.TextField()
    comment = models.TextField()
    params  = JSONField()# JSON List 
    date = models.DateField()
    deleted = models.BooleanField(default=0)

    def __str__(self):
        return self.curveFile + ": " + self.name

    class META:
        ordering = ('curveFile', 'orderInFile')


class CurveIndexing(models.Model):
    curveBasic = models.ForeignKey(CurveBasic, on_delete=models.CASCADE)
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


class CurveVectors(models.Model):
    curve = models.ForeignKey(CurveBasic, on_delete=models.CASCADE)
    date = models.DateField()
    name      = models.TextField()# Name of transformation (empty for unaltered)
    method    = models.TextField()# Field empty when data unaltered
    time = JSONField()
    potential = JSONField()# JSON List 
    current   = JSONField()# JSON List 
    concentration = JSONField()# JSON List
    concentrationUnits = JSONField()#JSON List
    probingData = JSONField()# JSON List 


class Analytes(models.Model):
    name=models.CharField(max_length=124)

    def __str__(self):
        return self.name
    

class AnalytesInCurve(models.Model):
    curve=models.ForeignKey(CurveBasic)
    analyte=models.ForeignKey(Analytes)
    concentration=models.FloatField()


class CurveCalibrations(models.Model):
    curves = models.ManyToManyField(CurveVectors)
    date = models.DateField()
    name = models.TextField()
    method = models.TextField()
    result = models.FloatField()
    resultStdDev = models.FloatField()
    corrCoeff = models.FloatField()
    vector = JSONField() # JSON List: This can be simple x vs y plot, but also multidimensional
    fitEquation =JSONField()
    analyte=models.ManyToManyField(Analytes)
    deleted = models.BooleanField(default=0)

    def __str__(self):
        return "%s: %s" % (date, name);

    class META:
        ordering = ('date')


class OnXAxis(models.Model):
    AVAILABLE = (
            ( 'P', 'Potential'), 
            ( 'T', 'Time'), 
            ( 'S', 'Samples'))
    selected = models.CharField(max_length=1, choices=AVAILABLE, default='P')
    user = models.IntegerField(User)
    
    def __str__(self):
        return self.selected;
