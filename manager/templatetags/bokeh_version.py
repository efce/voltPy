from django import template
import bokeh
register = template.Library()
@register.simple_tag
def get_bokeh_version():
    return bokeh.__version__
