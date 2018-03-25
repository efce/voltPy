from django.urls import reverse
from manager.helpers.functions import get_redirect_class
import manager.models as mmodels


def analytesTable(user, obj, objType):
    """
    cs - is CurveFile or CurveSet for which the table will be prepared.
    """
    if objType == 'cf':
        assert isinstance(obj, mmodels.CurveFile)
        cs = obj.curveSet
    else:
        assert isinstance(obj, mmodels.CurveSet)
        cs = obj

    htmlButton = '<button class="{goTo}">{bname}</button>'
    if not cs.locked:
        addAnalyteBtn = htmlButton.format(
            bname='Add analyte',
            goTo=get_redirect_class(
                reverse('editAnalyte', kwargs={
                    'user_id': user.id,
                    'objType': objType,
                    'objId': obj.id,
                    'analyteId': 'new'
                })
            )
        )
    else:
        addAnalyteBtn = '<button disabled> Add analyte </button>'

    lenana = len(cs.analytes.only('id'))

    ret = ['<table  cellspacing="0" cellpadding="0" border="0" class="analytesTable"><tr><td><table class="atHeader">']
    if lenana == 0:
        ret.append('<tr><th colspan=1>No analytes</th></tr><tr><th>Curve name</th>')
    else:
        ret.append(
            """
                <tr>
                    <td>&nbsp;</td>
                    <th colspan={:d} class="atOther">Analyte</th>
                    <th class="atOther">Action</th>
                </tr>
                <tr>
                    <th>Curve name</th>
            """.format(lenana)
        )

    unitsTrans = dict(mmodels.CurveSet.CONC_UNITS)

    for a in cs.analytes.all():
        ret.append("""
            <th class="atOther _voltJS_changeValue_{an_id}">&nbsp;
                {an_name} [{an_unit}]&nbsp;<br />
                <button class="{goTo} atOther"> Edit </button>
            </th>""".format(
                an_name=a.name,
                an_id=a.id,
                an_unit=unitsTrans[cs.analytesConcUnits[a.id]],
                goTo=get_redirect_class(
                    reverse('editAnalyte', kwargs={
                        'user_id': user.id,
                        'objType': objType,
                        'objId': obj.id, 
                        'analyteId': a.id
                    })
                )
            )
        )

    ret.append('<th class="atOther">{0}</th>'.format(addAnalyteBtn))
    ret.append('</tr></table></td></tr><tr><td><div class="atContentsContainer"><table class="atContents">')

    for cd in cs.curvesData.only('id', 'curve'):
        ret.append(
            '<tr class="_voltJS_plotHighlight _voltJS_highlightCurve@{0}"><td> {1} </td>'.format(
                cd.id,
                cd.curve.name
            )
        )
        for a in cs.analytes.all():
            conc = cs.analytesConc.get(a.id, {}).get(cd.id, 0)
            ret.append('<td class="atOther _voltJS_changeValue_%s"> %f </td>' % (a.id, conc))
        ret.append('<td class="atOther">')
        if not cs.locked:
            ret.append(
                htmlButton.format(
                    bname='Delete',
                    goTo=get_redirect_class(
                        reverse('deleteCurve', kwargs={
                            'user_id': user.id,
                            'objType': objType,
                            'objId': obj.id, 
                            'delId': cd.id
                        })
                    )
                )
            )
        else:
            ret.append('<button disabled>Delete</button>')
        ret.append('</td>')
        ret.append('</tr>')
    ret.append('</table></div></td></tr></table>')
    return ''.join(ret)
