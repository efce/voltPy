from django import template
from manager.helpers.html import locked, unlocked
register = template.Library()


@register.simple_tag
def lock():
    return locked()


@register.simple_tag
def unlock():
    return unlocked()