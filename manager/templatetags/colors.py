from django import template
register = template.Library()


@register.simple_tag
def color1():
    return '#555'


@register.simple_tag
def color1font():
    return 'white'


@register.simple_tag
def color2():
    return '#779'


@register.simple_tag
def color2even():
    return '#667'


@register.simple_tag
def color2font():
    return 'white'


@register.simple_tag
def color3():
    return '#EEF'


@register.simple_tag
def color3even():
    return '#CCE'


@register.simple_tag
def color3font():
    return 'black'