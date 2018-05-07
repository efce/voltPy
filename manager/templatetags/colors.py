from django import template
register = template.Library()


@register.simple_tag
def color1():
    return '#0070BB'


@register.simple_tag
def color1font():
    return 'white'


@register.simple_tag
def color2():
    return '#012b87'


@register.simple_tag
def color2even():
    return '#011577'


@register.simple_tag
def color2font():
    return 'white'


@register.simple_tag
def color3():
    return '#c6e8ff'


@register.simple_tag
def color3even():
    return '#aac9dd'


@register.simple_tag
def color3font():
    return 'black'