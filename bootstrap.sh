#!/bin/sh

cli=tools/bin/arduino-cli
cli_opts="--config-file  etc/arduino-cli.yaml"

conda install -y -c conda-forge pyinstaller pyserial git make
scripts/install_arduino_cli.py

${cli} ${cli_opts} cache clean
${cli} ${cli_opts} core update-index
${cli} ${cli_opts} core install  arduino:avr