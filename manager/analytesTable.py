from django.urls import reverse
from manager.helpers.functions import get_redirect_class
import manager.models as mmodels


def analytesTable(obj, objType: str) -> str:
    """
    cs - is CurveFile or CurveSet for which the table will be prepared.
    """
    cs = obj

    htmlButton = '<button class="{goTo}">{bname}</button>'
    if not cs.locked:
        addAnalyteBtn = htmlButton.format(
            bname='Add analyte',
            goTo=get_redirect_class(
                reverse('editAnalyte', kwargs={
                    'objType': objType,
                    'objId': obj.id,
                    'analyteId': 'new'
                })
            )
        )
    else:
        addAnalyteBtn = '<button disabled> Add analyte </button>'

    lenana = len(cs.analytes.only('id'))

    ret = ['<table  cellspacing="0" cellpadding="0" border="0" class="analytes_table"><thead>']
    ret.append('<tr><th>Curve name</th>')

    unitsTrans = dict(mmodels.CurveSet.CONC_UNITS)

    for a in cs.analytes.all():
        ret.append("""
            <th class="at_other _voltJS_changeValue_{an_id}">&nbsp;
                {an_name} [{an_unit}]&nbsp;<br />
                <button class="{goTo} at_other"> Edit </button>
            </th>""".format(
                an_name=a.name,
                an_id=a.id,
                an_unit=unitsTrans[cs.analytesConcUnits[a.id]],
                goTo=get_redirect_class(
                    reverse('editAnalyte', kwargs={
                        'objType': objType,
                        'objId': obj.id, 
                        'analyteId': a.id
                    })
                )
            )
        )

    ret.append('<th class="at_other">{0}</th>'.format(addAnalyteBtn))
    ret.append('</tr></thead><tbody>')

    for cd in cs.curvesData.only('id', 'curve'):
        ret.append(
            '<tr class="_voltJS_plotHighlight _voltJS_highlightCurve@{0}"><td> {1} </td>'.format(
                cd.id,
                cd.curve.__str__()
            )
        )
        for a in cs.analytes.all():
            conc = cs.analytesConc.get(a.id, {}).get(cd.id, 0)
            ret.append('<td class="at_other _voltJS_changeValue_%s"> %f </td>' % (a.id, conc))
        ret.append('<td class="at_other">')
        if not cs.locked:
            ret.append(
                htmlButton.format(
                    bname='Delete',
                    goTo=get_redirect_class(
                        reverse('deleteCurve', kwargs={
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
    ret.append('</tbody></table>')
    return ''.join(ret)
