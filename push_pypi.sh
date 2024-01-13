#!/bin/bash
#
# Upload from ./dist to tpypi.Assumes this config in ~/.pypirc:
#
# Must first increment version in toml file, and run ./build.sh
#
# [pypi]
#   username = __token__
#   password = (paste here the test pypi token)
#
# Documetnation here: 
# https://packaging.python.org/en/latest/tutorials/packaging-projects/
#
# To install the test package
#  pip install serial_packets 

# Abort if error
set -xe

pip install twine --upgrade
python -m twine upload --repository pypi dist/*

