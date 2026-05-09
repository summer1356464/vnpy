#!/bin/sh
cd ../..
pip install -e . -q && cd strategies/lance_breitstein && python3 backtest_lance_strategy.py
