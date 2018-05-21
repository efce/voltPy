import numpy as np
from scipy.stats import t
import manager.operations.method as method
from manager.operations.methodsteps.selectanalyte import SelectAnalyte
from manager.operations.methodsteps.selectrange import SelectRange
import manager.plotmanager as pm
import manager.models as mmodels
from manager.helpers.fithelpers import calc_normal_equation_fit
from manager.helpers.fithelpers import calc_sx0
from manager.helpers.fithelpers import significant_digit
from manager.exceptions import VoltPyFailed
from manager.operations.checks.check_analyte import check_analyte


class RegularStandardAddition(method.AnalysisMethod):
    can_be_applied = True
    _steps = [
        {
            'class': SelectAnalyte,
            'title': 'Select analyte',
            'desc': 'Select analyte for analysis.',
        },
        {
            'class': SelectRange,
            'title': 'Select range',
            'desc': 'Select range containing peak and press Forward, or press Back to change the analyte selection.',
        },
    ]
    checks = (check_analyte, )
    description = """
The standard addition method uses estimation of the unknown concentration
based on the linear regression fit with
<i>peak&nbsp;current</i>&nbsp;=&nbsp;m&middot;<i>concentration</i>&nbsp;+&nbsp;b
and final result is given by result&nbsp;=&nbsp;b/m.
Peak current is calculated as the difference between highest and lowest point in the given interval.
Because of the way sx0 (standard deviation of x0) value is calculated the point [0, y], i.e. point for concentration 0,
has to be included in the dataset.
"""

    @classmethod
    def __str__(cls):
        return "Regular Standard Addition"

    def exportableData(self):
        if not self.model.completed:
            raise VoltPyFailed('Incomplete data')
        return np.matrix(self.model.custom_data['matrix']).T

    def apply(self, user, dataset):
        an = self.model.getCopy()
        an.dataset = dataset
        an.appliesModel = self.model
        an.save()
        self.model = an
        try:
            self.finalize(user)
        except:
            an.deleted = True
            an.save()
            raise VoltPyFailed('Could not apply model.')
        return an.id

    def finalize(self, user):
        xvalues = []
        yvalues = []
        selRange = self.model.steps_data['SelectRange']
        try:
            analyte = self.model.analytes.get(id=int(self.model.steps_data['SelectAnalyte']))
        except:
            VoltPyFailed('Wrong analyte selected.')
        self.model.custom_data['analyte'] = analyte.name
        unitsTrans = dict(mmodels.Dataset.CONC_UNITS)
        self.model.custom_data['units'] = unitsTrans[self.model.dataset.analytes_conc_unit[analyte.id]]
        for cd in self.model.dataset.curves_data.all():
            startIndex = cd.xValue2Index(selRange[0])
            endIndex = cd.xValue2Index(selRange[1])
            if endIndex < startIndex:
                endIndex, startIndex = startIndex, endIndex
            yvalues.append(max(cd.yVector[startIndex:endIndex])-min(cd.yVector[startIndex:endIndex]))
            xvalues.append(self.model.dataset.analytes_conc.get(analyte.id, {}).get(cd.id, 0))

        if 0 not in xvalues:
            raise VoltPyFailed('The method requires signal value for concentration 0 %s' % self.model.custom_data['units'])
        data = [
            [float(b) for b in xvalues],
            [float(b) for b in yvalues]
        ]
        self.model.custom_data['matrix'] = data
        p = calc_normal_equation_fit(data[0], data[1])
        sx0, sslope, sintercept = calc_sx0(p['slope'], p['intercept'], data[0], data[1])
        if p['slope'] != 0:
            self.model.custom_data['fitEquation'] = p
            self.model.custom_data['slopeStdDev'] = sslope
            self.model.custom_data['interceptStdDev'] = sintercept
            self.model.custom_data['result'] = p['intercept']/p['slope']
            self.model.custom_data['resultStdDev'] = sx0,
            self.model.custom_data['corrCoef'] = np.corrcoef(data[0], data[1])[0, 1]
        else:
            self.model.custom_data['fitEquation'] = p
            self.model.custom_data['result'] = None
            self.model.custom_data['resultStdDev'] = None
            self.model.custom_data['corrCoef'] = None
        self.model.completed = True
        self.model.step = 0
        self.model.save()

    def getFinalContent(self, request, user):
        p = pm.PlotManager()
        data = p.analysisHelper(self.model.owner, self.model.id)
        for d in data:
            p.add(**d)
        p.plot_width = 500
        p.plot_height = 400
        p.sizing_mode = 'fixed'
        p.xlabel = 'c_({analyte}) / {units}'.format(
            analyte=self.model.custom_data['analyte'],
            units=self.model.custom_data['units']
        )
        p.ylabel = 'i / µA'
        scr, div, buttons = p.getEmbeded(request, user, 'analysis', self.model.id)
        n = len(self.model.custom_data['matrix'][0])
        talpha = t.ppf(0.975, n-2)
        conf_interval = np.multiply(self.model.custom_data['resultStdDev'], talpha)
        sd = significant_digit(conf_interval, 2)
        slope_interval = np.multiply(self.model.custom_data['slopeStdDev'], talpha)
        slopesd = significant_digit(slope_interval, 2)
        int_interval = np.multiply(self.model.custom_data['interceptStdDev'], talpha)
        intsd = significant_digit(int_interval, 2)
        return {
            'head': scr,
            'body': ''.join([
                '<table><tr><td style="width: 500px; height: 400px">',
                div,
                """
                </td></tr><tr><td>
                    Analyte: {an}<br />
                    Equation: y = {slope}(&plusmn;{sci}) &middot; x + {int}(&plusmn;{ici})<br />
                    r = {corrcoef}<br />
                    Result: {res}&plusmn;{ci} {anu}
                    </td></tr></table>
                """.format(
                    res='%.*f' % (sd, self.model.custom_data['result']),
                    ci='%.*f' % (sd, conf_interval),
                    corrcoef='%.4f' % self.model.custom_data['corrCoef'],
                    slope='%.*f' % (slopesd, self.model.custom_data['fitEquation']['slope']),
                    sci='%.*f' % (slopesd, slope_interval),
                    int='%.*f' % (intsd, self.model.custom_data['fitEquation']['intercept']),
                    ici='%.*f' % (intsd, int_interval),
                    an=self.model.custom_data['analyte'],
                    anu=self.model.custom_data['units']
                )
            ])
        }

main_class = RegularStandardAddition 
