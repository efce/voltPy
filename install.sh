#!/bin/bash
if [ $(id -u) -ne 0 ]; then
	echo This program has to be run as a root.
	exit 1
fi
pip install django unipath bokeh numpy scipy pandas django-picklefield xlrd ezodf lxml
