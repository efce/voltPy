#!/bin/bash
if [ $(id -u) -ne 0 ]; then
	echo This program has to be run as a root.
	exit 1
fi
pip install django
pip install jsonfield
pip install matplotlib
pip install unipath
pip install bokeh
pip install numpy
