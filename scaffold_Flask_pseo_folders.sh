#!/bin/bash

mkdir templates pages
touch templates/base.html templates/index.html templates/page.html templates/macros.html templates/navbar.html templates/footer.html
mkdir static static/css static/src static/javascript
mkdir static/images static/images/png static/images/webp static/images/svg
mkdir data data/external data/interim data/processed data/raw
mkdir notebooks python_code models
touch python_code/__init__.py python_code/download.py python_code/preprocess.py python_code/pseo.py

