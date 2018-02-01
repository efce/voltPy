import manager.models as mmodels
import base64 as b64
from django.db.models import Q
from django.urls import reverse

def analytesTable(user, source):
    """
    source - is CurveFile or CurveSet for which the table will be prepared.
    """
    assert isinstance(source, mmodels.CurveFile) \
        or isinstance(source, mmodels.CurveSet)

    objType = ''
    if isinstance(source, mmodels.CurveSet):
        objType = 'cs'
        cds = source.usedCurveData.all()
        curves = []
        for c in cds:
            curves.append(c.curve)
    else:
        objType = 'cf'
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

    addAnalyteBtn = '<button class="urlChanger url@{0}">Add</button>'.format(
        b64.b64encode(reverse('editAnalyte', kwargs={
                'user_id': user.id,
                'objType': objType,
                'objId': source.id,
                'analyteId': 'new'
            }).encode()
        ).decode('UTF-8')
    )

    ret = ['<table>']
    if lenana == 0:
        ret.append('<tr><th colspan=1>No analytes</th><th>{0}</th></tr><tr><th>Curve names</th>'.format(addAnalyteBtn))
    else:
        ret.append('<tr><td>&nbsp;</td><th colspan={:d}>Analytes</th><th>Action</th></tr><tr><th>Curve names</th>'.format(lenana))
    for a in analytes:
        ret.append('<th> {0} <br /><button class="urlChanger url@{1}">Edit</button></th>'.format(
                a.name, 
                b64.b64encode(reverse('editAnalyte', kwargs={
                    'user_id': user.id,
                    'objType': objType,
                    'objId': source.id, 
                    'analyteId':a.id
                    }).encode()
                ).decode('UTF-8')
            )
        )
    ret.append('<th>{0}</th>'.format(addAnalyteBtn))
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
        
