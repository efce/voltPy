import manager.models as mmodels
from django.db.models import Q

def analytesTable(source):
    """
    source - is CurveFile or CurveSet for which the table will be prepared.
    """
    assert isinstance(source, mmodels.CurveFile) \
        or isinstance(source, mmodels.CurveSet)

    if isinstance(source, mmodels.CurveSet):
        cds = source.usedCurveData.all()
        curves = []
        for c in cds:
            curves.append(c.curve)
    else:
        curves = mmodels.Curve.objects.filter(curveFile=source)

    curves_filter_qs = Q()
    for c in curves:
        curves_filter_qs = curves_filter_qs | Q(curve=c)

    aic = mmodels.AnalyteInCurve.objects.filter(curves_filter_qs)

    analytes = {}
    
    for aa in aic:
        analytes[aa.analyte] = aa.analyte
    analytes = list(analytes.values())
    lenana = len(analytes)

    ret = ['<table>']
    if lenana == 0:
        ret.append('<tr><th colspan=1>No analytes</th></tr><tr><th>Curve names</th>')
    else:
        ret.append('<tr><td>&nbsp;</td><th colspan={:d}>Analytes</th></tr><tr><th>Curve names</th>'.format(lenana))
    for a in analytes:
        ret.append('<th> %s </th>' % a)
    ret.append('</tr>')

    for c in curves:
        ret.append('<tr><td> %s </td>' % c.name)
        for a in analytes:
            aac = aic.filter(curve=c, analyte=a)
            if len(aac) > 0:
                ret.append('<td> %f </td>' %  aac[0].concentration )
            else:
                ret.append('<td> %f </td>' % 0)
        ret.append('</tr>')
    ret.append('</table>')
    return ''.join(ret)
        
