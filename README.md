# Introduction 
This project serves as the placeholder of all the assets developed
for the POC of MapCrop project.

# Getting Started
0. Ensure pip is installed 
- $ sudo python3 -m ensurepip --upgrade
- $ pip install virtual env
1. Create virtual environment
    - $ python3 -m venv env3
    - $ source env3/bin/activate
    - $ pip install -r requirements.txt
    - (for developers): $ install -r requirements_dev.txt
2. Run 'python pipeline.py -h' for instructions

# Contents
geojsons/ contain .geojson files for various sites.

notebook/ contains a .ipynb script used for activating an image through
Planet API and then downloading it.