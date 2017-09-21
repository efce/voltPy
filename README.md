# voltPy -- Web based platform for voltammetric data analysis and processing
The idea of the project is to provide the electrochemist with easy tool for storing, processing and analyzing the data with newest procedures and algorithms. The project aims to offer integrated environment similar to native desktop applications for analyzers such as EAQt (https://www.github.com/efce/EAQt) or Autolab NOVA©. The platform is designed to offer easy implementation of algorithms for data scientists and easy use for electrochemists. The web platform is based on Django framework and the interactivity of the plots is achieved by taking advantage of Bokeh plotting framework and custom JavaScripts.

# Installation
The project requires following python modules: django, unipath, bokeh, numpy, scipy, pandas, django-picklefield.

# Usage
The project start as regular Django service (with 'python manage.py runserver'), and is avaiable under http://127.0.0.1:8000/manager/. The test file is included from 'EAQt - electrochemical analyzer' to upload, and check and possibilities of the service. The file is in the main directory with *.volt extensionn.
