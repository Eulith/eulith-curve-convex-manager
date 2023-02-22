#!/bin/bash

if [ -z ${1+x} ]
then
  echo -e "Please give me your Eulith Refresh Token. For example, you can run \n\n./setup.sh <EULITH_REFRESH_TOKEN>\n"
  exit 1
fi

python3 -m venv venv
source venv/bin/activate
echo "START installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install eulith-web3 > /dev/null 2>&1
echo "DONE installing dependencies"
python utils/setup.py "$1"