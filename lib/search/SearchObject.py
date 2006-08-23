"""
MetPX Copyright (C) 2004-2006  Environment Canada
MetPX comes with ABSOLUTELY NO WARRANTY; For details type see the file
named COPYING in the root of the source directory tree.
"""

"""
###########################################################
# Name: SearchObject.py
#
# Author: Dominik Douville-Belanger
#
# Description: Class containing the information needed in
#              order to perform a search.
#
# Date: 2006-05-15
#
###########################################################
"""

import sys
import time

# Local imports
sys.path.insert(1,sys.path[0] + '/../')
import PXPaths; PXPaths.normalPaths()

class SearchObject(object):
    __slots__ = ["headerRegexes", "searchRegex", "searchType", "names", "logPath", "since", "fromdate", "todate", "timesort"]

    def __init__(self):
        self.headerRegexes = {}
        self.searchRegex = ""
        self.searchType = ""
        self.names = []
        self.logPath = ""
        self.since = 0
        self.fromdate = "epoch"
        self.todate = "now"
        self.timesort = False

        self.fillHeaderRegexes()

    def fillHeaderRegexes(self):
        alphanumeric = "[[:alnum:]-]" # Just an alias instead of typing it everytime
        digits = "[[:digit:]]"
        zeroOrMore = "*"
        oneOrMore = "+"
        
        self.headerRegexes["ttaaii"] = alphanumeric + oneOrMore
        self.headerRegexes["ccccxx"] = alphanumeric + oneOrMore
        self.headerRegexes["ddhhmm"] = digits + "{6}" # Repeats exactly six times
        self.headerRegexes["bbb"] = alphanumeric + zeroOrMore
        self.headerRegexes["stn"] = alphanumeric + zeroOrMore
        self.headerRegexes["target"] = alphanumeric + oneOrMore
        self.headerRegexes["seq"] = digits + "{5}"
        self.headerRegexes["prio"] = digits + "{1}"
    
    def compute(self):
        """
        Refresh the object based on its updated attributes.
        """
        
        names = self.getSearchNames()
        for name in names:
            self.logPath += "%s%s_%s.log* " % (PXPaths.LOG, self.getSearchType(), name)
        self.searchRegex = "%s_%s_%s_%s_%s_%s:%s:%s:%s:%s:%s:%s" % (self.getHeaderRegex("ttaaii"), self.getHeaderRegex("ccccxx"), self.getHeaderRegex("ddhhmm"), self.getHeaderRegex("bbb"), self.getHeaderRegex("stn"), self.getHeaderRegex("seq"), self.getHeaderRegex("target"), self.getHeaderRegex("ccccxx"), "[[:alnum:]]{2}", self.getHeaderRegex("prio"), "[[:alnum:]]+", "[[:digit:]]{14}")
    
    def getSearchRegex(self):
        return self.searchRegex

    def getLogPath(self):
        return self.logPath

    def getHeaderRegex(self, key):
        return self.headerRegexes[key]
    
    def setHeaderRegex(self, key, value):
        """
        Change the value of the regular expression dictionnary parts.
        It also performs some modification on the value.
        """
        
        if value != self.headerRegexes[key]: # Checks if the new value is different than the old.
            if key != "target": # We don't want to capitalize certain fields.
                value = value.upper()
            
            # If user enters a wildcard card, replace it with a regex wildcard
            if "*" in value:
                try:
                    int(value) # If we can convert it to an integer it means it is one.
                    value = value.reaplce("*", "[[:digit:]]+") # Then we can use a digit widlcard
                except ValueError:
                    value = value.replace("*", "[[:alnum:]-]*")
                
        self.headerRegexes[key] = value

    def getSearchType(self):
        return self.searchType

    def setSearchType(self, value):
        self.searchType = value

    def getSearchNames(self):
        return self.names

    def setSearchNames(self, value):
        self.names = value

    def getSince(self):
        return self.since

    def setSince(self, value):
        self.since = int(value)

    def getFrom(self):
        return self.fromdate

    def setFrom(self, value):
        self.fromdate = value

    def getTo(self):
        return self.todate

    def setTo(self, value):
        self.todate = value

    def getTimesort(self):
        return self.timesort

    def setTimesort(self, value):
        self.timesort = value
