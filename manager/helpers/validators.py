from django.core.exceptions import ValidationError


def validate_polynomial_degree(v):
    try:
        vv = int(v)
    except:
        raise ValidationError('Degree has to be integer.')
    if vv < 0:
        raise ValidationError('Degree has to be positive.')


def validate_window_span(v):
    try:
        vv = int(v)
    except:
        raise ValidationError('Window span has to be integer.')
    if vv < 0:
        raise ValidationError('Window span has to be positive.')
    if (vv % 2) != 1:
        raise ValidationError('Windows span has to be odd.')
