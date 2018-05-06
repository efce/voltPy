{% load static %}
<script src="{% static 'manager/3.2.1/jquery.min.js' %}"></script>
<script src="{% static 'manager/mkoryak-floatThead/dist/jquery.floatThead.min.js' %}"></script>
{% include "./bokeh.inc" %}
<script>
{% include "./main.js" %}
</script>