#!/bin/bash

# https://packaging.python.org/en/latest/tutorials/packaging-projects/

# Abort if error
set -xe

if [ -e "./dist" ]; then
  rm -r ./dist
fi

python -m pip install --upgrade build
python -m build

