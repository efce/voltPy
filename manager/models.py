from django.db import models
from .compressedjsonfield import CompressedJSONField


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


class Curve(models.Model):
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


class CurveIndex(models.Model):
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


class CurveData(models.Model):
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


class Analyte(models.Model):
    name=models.CharField(max_length=124, unique=True)

    def __str__(self):
        return self.name
    

class AnalyteInCurve(models.Model):
    curve=models.ForeignKey(Curve)
    analyte=models.ForeignKey(Analyte)
    concentration=models.FloatField()


class Calibration(models.Model):
    owner = models.ForeignKey(User)
    usedCurveData = models.ManyToManyField(CurveData)
    selectedRange = CompressedJSONField(default="")
    date = models.DateField()
    name = models.TextField()
    method = models.TextField()
    result = models.FloatField()
    resultStdDev = models.FloatField()
    corrCoeff = models.FloatField()
    vector = CompressedJSONField() # JSON List: This can be simple x vs y plot, but also multidimensional
    fitEquation =CompressedJSONField()
    analyte=models.ManyToManyField(Analyte)
    deleted = models.BooleanField(default=0)
    complete = models.BooleanField(default=0)

    def __str__(self):
        return "%s: %s" % (self.date, self.name);

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
