from django.urls import reverse
from manager.helpers.functions import get_redirect_class
import manager.models as mmodels


def analytesTable(obj, objType: str) -> str:
    """
    cs - is CurveFile or CurveSet for which the table will be prepared.
    """
    cs = obj

    htmlButton = '<button class="{goTo}">{bname}</button>'

    lenana = len(cs.analytes.only('id'))

    ret = [
        '<div class="analytes_table_container">',
        '<table id="fixed_header" class="analytes_table">',
        '<thead>'
    ]
    ret.append('<tr><th>Name</th>')

    unitsTrans = dict(mmodels.CurveSet.CONC_UNITS)

    for a in cs.analytes.all():
        ret.append("""
            <th class="at_hideable _voltJS_changeValue_{an_id}">&nbsp;
                <button type="button" class="{goTo}"{disabled}> {an_name} [{an_unit}] </button>
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
                ),
                disabled=' disabled' if cs.locked else ''
            )
        )

    ret.append('<th class="at_hideable at_selection">&#9634;</th>')
    ret.append('</tr></thead><tbody>')

    for cd in cs.curvesData.only('id', 'curve'):
        ret.append(
            '<tr class="_voltJS_plotHighlight _voltJS_highlightCurve@{cdid}" onclick="$(\'input[name=cd_{cdid}]\').click();"><td> {cdname} </td>'.format(
                cdid=cd.id,
                cdname=cd.curve.__str__()
            )
        )
        for a in cs.analytes.all():
            conc = cs.analytesConc.get(a.id, {}).get(cd.id, 0)
            ret.append('<td class="at_hideable _voltJS_changeValue_%s"> %f </td>' % (a.id, conc))
        ret.append('<td class="at_hideable at_selection">')
        ret.append(
            '<input onclick="event.stopPropagation();" class="at_selection" style="height: 19px" type="checkbox" name="cd_%i" %s/>'
                % (cd.id, 'disabled' if cs.locked else '')
        )
        ret.append('</td>')
        ret.append('</tr>')
    ret.append('</tbody></table></div>')
    return ''.join(ret)
