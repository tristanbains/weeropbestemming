#!/bin/bash

echo "*.pyc" > .gitignore
echo "__pycache__/" >> .gitignore
echo ".ipynb_checkpoints/" >> .gitignore
echo "venv/" >> .gitignore
echo "env/" >> .gitignore
echo "dist/" >> .gitignore
# echo "build/" >> .gitignore
echo "logs/" >> .gitignore
echo "*.log" >> .gitignore
echo "*.out" >> .gitignore
echo ".idea/" >> .gitignore
echo ".vscode/" >> .gitignore
echo "*.DS_Store" >> .gitignore