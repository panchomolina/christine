#!/bin/bash
cd ~/asistente
source asistente_env/bin/activate
python main.py > /dev/null 2>&1 &
