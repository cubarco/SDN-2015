#!/usr/bin/env python
# coding=utf8

import sys
import os
import importlib
import config

sys.path.insert(0, os.path.dirname(config.modules_path))
for module in config.enable:
    importlib.import_module(module)
sys.path.pop(0)
