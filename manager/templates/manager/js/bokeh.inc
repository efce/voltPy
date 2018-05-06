{% load static %}
  <link href="{% static 'manager/bokeh/bokeh-0.12.13.min.css' %}" rel="stylesheet" type="text/css"> 
  <link href="{% static 'manager/bokeh/bokeh-widgets-0.12.13.min.css' %}" rel="stylesheet" type="text/css"> 
  <script src="{% static 'manager/bokeh/bokeh-0.12.13.min.js' %}"></script> 
  <script src="{% static 'manager/bokeh/bokeh-api-0.12.13.min.js' %}"></script> 
  <script src="{% static 'manager/bokeh/bokeh-widgets-0.12.13.min.js' %}"></script>
{% include './voltPyBokeh.js' %}
