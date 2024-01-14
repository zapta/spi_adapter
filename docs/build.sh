#!/bin/bash

#cp ../firmware/platformio/src/__init__.py /c/Users/user/AppData/Local/Programs/Python/Python312/Lib/site-packages/i2c_adapter/__init__.py
#./make.bat html


cp \
  ../firmware/platformio/src/__init__.py \
  /Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/spi_adapter/__init__.py

make html



