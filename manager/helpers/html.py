from django.utils.safestring import mark_safe


def locked():
    return mark_safe('<span style="margin: 0px; padding: 0px; color: red;">🔒&#xFE0E;</span>')


def unlocked():
    return mark_safe('<span style="margin: 0px; padding: 0px; color: green;">🔓&#xFE0E;</span>')
