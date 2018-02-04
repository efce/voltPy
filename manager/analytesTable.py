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
        for cd in cds:
            curves.append(cd.curve)
            curves[-1].cdid = cd.id
    else:
        objType = 'cf'
        curves = mmodels.Curve.objects.filter(curveFile=source, deleted=False)
        for c in curves:
            cd = mmodels.CurveData.objects.filter(curve=c, processing=None)
            c.cdid = cd[0].id

    curves_filter_qs = Q()
    for c in curves:
        curves_filter_qs = curves_filter_qs | Q(curve=c)

    aic = mmodels.AnalyteInCurve.objects.filter(curves_filter_qs)

    analytes = {}
    
    for aa in aic:
        analytes[aa.analyte] = aa.analyte
    analytes = list(analytes.values())
    lenana = len(analytes)

    htmlButton = '<button class="urlChanger url@{1}">{0}</button>'
    addAnalyteBtn = htmlButton.format(
        'Add analyte',
        b64.b64encode(reverse('editAnalyte', kwargs={
                'user_id': user.id,
                'objType': objType,
                'objId': source.id,
                'analyteId': 'new'
            }).encode()
        ).decode('UTF-8')
    )

    ret = ['<table  cellspacing="0" cellpadding="0" border="0" class="analytesTable"><tr><td><table class="atHeader">']
    if lenana == 0:
        ret.append('<tr><th colspan=1>No analytes</th></tr><tr><th>Curve names</th>')
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
    ret.append('</tr></table></td></tr><tr><td><div class="atContentsContainer"><table class="atContents">')

    for c in curves:
        if objType == 'cf':
            delId = c.id
        else:
            delId = c.cdid
        ret.append('<tr class="plotHighlight highlightCurve@{0}"><td> {1} </td>'.format(c.cdid, c.name))
        for a in analytes:
            aac = aic.filter(curve=c, analyte=a)
            if len(aac) > 0:
                ret.append('<td> %f </td>' %  aac[0].concentration )
            else:
                ret.append('<td> %f </td>' % 0)
        ret.append('<td>')
        ret.append(htmlButton.format(
                'delete',
                b64.b64encode(reverse('deleteCurve', kwargs={
                    'user_id': user.id,
                    'objType': objType,
                    'objId': source.id, 
                    'delId': delId
                    }).encode()
                ).decode('UTF-8')
            )
        )
        ret.append('</td>')
        ret.append('</tr>')
    ret.append('</table></div></td></tr></table>')
    return ''.join(ret)
        
