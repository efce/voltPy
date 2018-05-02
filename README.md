# voltPy - web based platform for voltammetric data analysis and processing
The idea of the project is to provide the electrochemist with an easy tool for storing, processing and analyzing the data with newest procedures and algorithms. The project aims to offer integrated environment similar to the native desktop applications for analyzers such as EAQt (https://www.github.com/efce/EAQt) or Autolab NOVA©. The web platform is designed to offer easy implementation of algorithms for data scientists and easy use for electrochemists. Service is based on Django framework and the interactivity of the plots is achieved by taking advantage of Bokeh plotting framework and custom JavaScripts.

# Installation
The project requirements are in requirements.txt file.
```
pip install -r requirements.txt
```
# Usage
For developement purpose the project start as a regular Django service (with 'python manage.py runserver'), and is available under http://127.0.0.1:8000/manager/. The different test files are included, vol, volt and voltc are from 'EAQt - electrochemical analyzer', which are located in ./test_files/ directory. These files can be uploaded to check the current capabilities of the web service. 
