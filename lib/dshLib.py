"""
MetPX Copyright (C) 2004-2007  Environment Canada
MetPX comes with ABSOLUTELY NO WARRANTY; For details type see the file
named COPYING in the root of the source directory tree.
"""

"""
#############################################################################################
# Name: dshLib.py
#
# Author: Daniel Lemay
#
# Date: 2007-10-11
#
# Description: Useful dsh related functions
#
#############################################################################################
"""
import sys
import fileLib

DSH_ROOT = "/etc/dsh/"
DSH_GROUP = DSH_ROOT + "group/"


def getMachines(group):
    machines = fileLib.getLines(DSH_GROUP + group)
    return machines or ['userver1-new', 'userver2-new']

if __name__ == '__main__':
    

    print getMachines("px")
    print getMachines("pds")
    print getMachines("pxatx")

    print getMachines("PX")
    print getMachines("PDS")
    print getMachines("PXATX")

