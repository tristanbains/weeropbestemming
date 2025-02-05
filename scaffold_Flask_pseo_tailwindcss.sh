#!/bin/bash

mkdir -p static/src
echo "@tailwind base;" > static/src/style.css
echo "@tailwind components;" >> static/src/style.css
echo "@tailwind utilities;" >> static/src/style.css