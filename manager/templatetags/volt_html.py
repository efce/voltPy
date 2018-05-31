from django import template
from manager.helpers.html import locked, unlocked
register = template.Library()


@register.simple_tag
def lock():
    return locked()


@register.simple_tag
def unlock():
    return unlocked()


@register.simple_tag
def topmenu_height():
    return '71px'


@register.simple_tag
def topmenu_height_logo():
    return '65px'