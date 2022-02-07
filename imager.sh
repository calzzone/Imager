#!/bin/bash

# pip install --upgrade pip
# pip install numpy pandas scipy rawkit rawpy imageio scikit-image sortedcontainers pyqtgraph opencv-python-headless PyQT5

python imager.py

echo "Press ESC key to quit"
# read a single character
while read -r -n1 key
do
# if input == ESC key
if [[ $key == $'\e' ]];
then
break;
done
