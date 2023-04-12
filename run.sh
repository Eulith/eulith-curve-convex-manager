#!/bin/bash

function show_help() {
  echo -e "\nYou can run several Curve/Compound examples from this script. Here are the options:\n"
  echo "  -a               |  Auto-compound"
  echo "  -m               |  Monitor & auto-unwind for USDC depeg"
  echo -e "\nIf you would like to examine the code for the examples, have a look at the files in the examples folder.\n"
}

if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

source venv/bin/activate

while getopts "h?am" opt; do
  case "$opt" in
    h|\?)
      show_help
      exit 0
      ;;
    a) python examples/auto_compound.py
      ;;
    m) python examples/monitor_usdc.py
      ;;
  esac
done