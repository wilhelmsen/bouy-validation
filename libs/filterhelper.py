#!/usr/bin/env python
# coding: utf-8
def format(value):
    try:
        return "%8.3f"%(float(value))
    except:
        try:
            return "%8i"%(int(value))
        except:
            return "%8s"%str(value)
