from django.utils.safestring import mark_safe
from django.contrib.staticfiles.templatetags.staticfiles import static


def locked():
    return mark_safe('<img src="%s" alt="locked" style="border:0px; margin: 0px; padding: 0px"/>' % ( 
        static('manager/padlock_close.png')
    ))


def unlocked():
    return mark_safe('<img src="%s" alt="locked" style="border:0px; margin: 0px; padding: 0px"/>' % ( 
        static('manager/padlock_open.png')
    ))
