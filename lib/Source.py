"""
MetPX Copyright (C) 2004-2006  Environment Canada
MetPX comes with ABSOLUTELY NO WARRANTY; For details type see the file
named COPYING in the root of the source directory tree.
"""

"""
#############################################################################################
# Name: Source.py
#
# Authors: Peter Silva (imperative style)
#          Daniel Lemay (OO style)
#
# Date: 2005-01-10 (Initial version by PS)
#       2005-08-21 (OO version by DL)
#       2005-10-28 (mask in source by MG)
#
# Description:
#
# Revision History: 
#               2005-12-15 Added parsing of collection conf file
#               2006-05-15 MG   Modification  of collection conf 
#############################################################################################

"""
import sys, os, os.path, time, string, commands, re, signal, fnmatch

# default library path

# old way
sys.path.insert(1, '/apps/px/lib')

# debian way
sys.path.insert(1, '/usr/lib/px')

# developpement library path option through PXLIB

try:
         sys.path.insert(1, os.path.normpath(os.environ['PXLIB']) )
except :
         pass

import PXPaths
from Logger import Logger
from Ingestor import Ingestor
from URLParser import URLParser


PXPaths.normalPaths()              # Access to PX paths

class Source(object):

    def __init__(self, name='toto', logger=None, ingestion=True, filter=False ) :
        
        # General Attributes
        self.name   = name                        # Source's name
        self.filter = filter                      # is this source realy defines a filter ?
        if logger is None:
            pathlog     = PXPaths.LOG + 'rx_' + name + '.log'
            namelog     = 'RX' + name
            if self.filter :
               pathlog  = PXPaths.LOG + 'fx_' + name + '.log'
               namelog  = 'FX' + name
            self.logger = Logger(pathlog, 'INFO', namelog ) # Enable logging
            self.logger = self.logger.getLogger()
        else:
            self.logger = logger

        if not self.filter :
           self.logger.info("Initialisation of source %s" % self.name)
        else :
           self.logger.info("Initialisation of filter %s" % self.name)

        # Attributes coming from the configuration file of the source
        #self.extension = 'nws-grib:-CCCC:-TT:-CIRCUIT:Direct'  # Extension to be added to the ingest name
        self.ingestion = ingestion                # do we want to start the ingestion...
        self.debug = False                        # If we want sections with debug code to be executed
        self.batch = 100                          # Number of files that will be read in each pass
        self.cache_size = 125000                  # Maximum Number of md5sum from files kept in cache manager
        self.bulletin_type = None                 # type of bulletin ingested (None, am, wmo)
        self.masks = []                           # All the masks (accept and reject)
        self.masks_deprecated = []                # All the masks (imask and emask)
        self.routemask = True                     # use accept and parenthesis in mask to create a key and route with it
        self.routing_version = 1                  # directRouting version setting
        self.nodups = False                       # Check if the file was already received (md5sum present in the cache)
        self.tmasks = []                          # All the transformation maks (timask, temask)
        self.extension = ':MISSING:MISSING:MISSING:MISSING:'   # Extension to be added to the ingest name
        # Extension to be added to the ingest name when the bulletin is outside its arrival range
        self.arrival_extension = None
        self.type = None                                       # Must be in ['filter','file','single-file', 'bulletin-file', 'am', 'wmo']
        self.port = None                                       # Port number if type is in ['am', 'wmo']
        self.routingTable = PXPaths.ROUTING_TABLE              # Defaut routing table name
        self.mapEnteteDelai = None                             #
        self.addStationInFilename = True                       #
        self.addSMHeader = False                               #
        self.validation = False                                # Validate the filename (ex: prio an timestamp)
        self.patternMatching = True                            # No pattern matching
        self.clientsPatternMatching = True                     # No clients pattern matching
        self.sorter = None                                     # No sorting on the filnames
        self.feeds = []                                        # more source to feed directly
        self.keepAlive = True                                  # TCP SO_KEEPALIVE on (True) or off(False)
        self.mtime = 0                                         # Integer indicating the number of seconds a file must not have 
                                                               # been touched before being picked


        # AMQP

        self.exchange_key   = ''
        self.exchange_name  = None
        self.exchange_realm = '/data'
        self.exchange_type  = 'fanout'

        #-----------------------------------------------------------------------------------------
        # Setting up pulls configuration values
        #-----------------------------------------------------------------------------------------

        self.pulls = []                           # All the directories and file patterns to pull
        self.host = 'localhost'                   # Remote host address (or ip) where to send files
        self.protocol = None                      # First thing in the url: ftp, file, am, wmo, amis
        self.url = None
        self.user = None                    # User name used to connect
        self.passwd = None                  # Password 
        self.ssh_keyfile = None             # ssh private key file for sftp protocol
        self.ftp_mode = 'passive'           # Default is 'passive', can be set to 'active'

        self.timeout_get = 0                # Timeout in sec. to consider a get to hang ( 0 means inactive )
        self.pull_sleep  = 600              # Time in sec. to retry the pull
        self.pull_wait   = 10               # Time in sec. to wait after ls before pulling (make sure files are arrived)
        self.delete = False                 # file is deleted after pull  if it is false, the file's ls is kept
                                            # to check if it changed...
        self.pull_prefix = ''               # file may be prefixed bu some string filename will than be prefix_filename
                                            # or value 'HDATETIME' for the file data time on remote host

        # VIP option, None for standalone process
        self.vip = None

        #-----------------------------------------------------------------------------------------
        # Setting up default collection configuration values
        #-----------------------------------------------------------------------------------------

        self.headers       = []   # Title for report in the form TT from (TTAAii)
        self.issue_hours   = []   # list of emission hours to collect
        self.issue_primary = []   # amount of minutes past emission hours for the primary collection (report on time)
        self.issue_cycle   = []   # amount of minutes for cycling after the primary collection for more reports
        self.history       = 25   # time in hours to consider a valid report even if "history" hours late.
        self.future        = 40   # time in minutes to consider a valid report even if "future" minutes too soon

        #-----------------------------------------------------------------------------------------
        # Setting file transformations/conversions... etc...
        #-----------------------------------------------------------------------------------------

        self.fx_script   = None   # a script to convert/modify each received files
        self.fx_execfile = None

        self.lx_script   = None   # a script to convert/modify a list of received files
        self.lx_execfile = None

        self.pull_script   = None # a script to pull files prior to read rxq
        self.pull_execfile = None

        #-----------------------------------------------------------------------------------------
        # All defaults for a source were set earlier in this class
        # But some of them may have been overwritten in the px.conf file
        # Load the px.conf stuff related to the source
        #-----------------------------------------------------------------------------------------

        pxconf_Path = PXPaths.ETC + 'px.conf'
        if os.path.isfile(pxconf_Path) : self.readConfig( pxconf_Path )

        #-----------------------------------------------------------------------------------------
        # Parse the configuration file
        #-----------------------------------------------------------------------------------------

        filePath                  = PXPaths.RX_CONF +  self.name + '.conf'
        if self.filter : filePath = PXPaths.FX_CONF +  self.name + '.conf'
        self.readConfig( filePath )

        #-----------------------------------------------------------------------------------------
        # instantiate the fx script in source class
        #-----------------------------------------------------------------------------------------

        if self.fx_execfile != None :
           try    : execfile(PXPaths.SCRIPTS + self.fx_execfile )
           except : self.logger.error("Problem with fx_script %s" % self.fx_execfile)

        if self.lx_execfile != None :
           try    : execfile(PXPaths.SCRIPTS + self.lx_execfile )
           except : self.logger.error("Problem with lx_script %s" % self.lx_execfile)

        if self.pull_execfile != None :
           try    : execfile(PXPaths.SCRIPTS + self.pull_execfile )
           except : self.logger.error("Problem with pull_script %s" % self.pull_execfile)

        #-----------------------------------------------------------------------------------------
        # Make sure the collection params are valid
        #-----------------------------------------------------------------------------------------
        if self.type == 'collector' :
           self.validateCollectionParams()

        #-----------------------------------------------------------------------------------------
        # If we do want to start the ingestor...
        #-----------------------------------------------------------------------------------------

        if self.ingestion :

           if hasattr(self, 'ingestor'):
               # Will happen only when a reload occurs
               self.ingestor.__init__(self)
           else:
               self.ingestor = Ingestor(self)

           if len(self.feeds) > 0 :
              self.ingestor.setFeeds(self.feeds)

           self.ingestor.setClients()

        #self.printInfos(self)

    def readConfig(self,filePath):

        def isTrue(s):
            if  s == 'True' or s == 'true' or s == 'yes' or s == 'on' or \
                s == 'Yes' or s == 'YES' or s == 'TRUE' or s == 'ON' or \
                s == '1' or  s == 'On' :
                return True
            else:
                return False

        try:
            config = open(filePath, 'r')
        except:
            (type, value, tb) = sys.exc_info()
            print("Type: %s, Value: %s" % (type, value))
            return 

        # current dir and filename could eventually be used
        # for file renaming and perhaps file move (like a special receiver/dispatcher)

        currentDir = '.'                # just to preserve consistency with client : unused in source for now
        currentFileOption = 'WHATFN'    # just to preserve consistency with client : unused in source for now
        currentTransformation = 'GIFFY' # Default transformation for tmasks
        currentLST = None               # a list consisting of one directory followed one or more file patterns

        for line in config.readlines():
            words = line.split()
            if (len(words) >= 2 and not re.compile('^[ \t]*#').search(line)):
                try:
                    if words[0] == 'extension':
                        if len(words[1].split(':')) != 5:
                            self.logger.error("Extension (%s) for source %s has wrong number of fields" % (words[1], self.name)) 
                        else:
                            self.extension = ':' + words[1]
                            self.extension = self.extension.replace('-NAME',self.name)
                    elif words[0] == 'arrival_extension':
                        if len(words[1].split(':')) != 5:
                            self.logger.error("arrival_extension (%s) for source %s has wrong number of fields" % (words[1], self.name)) 
                        else:
                            self.arrival_extension = ':' + words[1]
                            self.arrival_extension = self.arrival_extension.replace('-NAME',self.name)
                    elif words[0] == 'accept': 
                         cmask = re.compile(words[1])
                         self.masks.append((words[1], currentDir, currentFileOption,cmask,True))
                    elif words[0] == 'reject':
                         cmask = re.compile(words[1])
                         self.masks.append((words[1], currentDir, currentFileOption,cmask,False))
                    elif words[0] == 'routemask': self.routemask = isTrue(words[1])
                    elif words[0] == 'routing_version': self.routing_version = int(words[1])
                    elif words[0] == 'noduplicates': self.nodups =  isTrue(words[1])
                    elif words[0] == 'imask': self.masks_deprecated.append((words[1], currentDir, currentFileOption))
                    elif words[0] == 'emask': self.masks_deprecated.append((words[1],))
                    elif words[0] == 'timask': self.tmasks.append((words[1], currentTransformation))
                    elif words[0] == 'temask': self.tmasks.append((words[1],))
                    elif words[0] == 'transformation': currentTransformation = words[1]
                    elif words[0] == 'batch': self.batch = int(words[1])
                    elif words[0] == 'cache_size': self.cache_size = int(words[1])
                    elif words[0] == 'bulletin_type': self.bulletin_type = words[1]
                    elif words[0] == 'type': self.type = words[1]
                    elif words[0] == 'port': self.port = int(words[1])
                    elif words[0] == 'AddSMHeader' and isTrue(words[1]): self.addSMHeader = True
                    elif words[0] == 'addStationInFilename' : self.addStationInFilename = isTrue(words[1])
                    elif words[0] == 'patternMatching': self.patternMatching =  isTrue(words[1])
                    elif words[0] == 'clientsPatternMatching': self.clientsPatternMatching =  isTrue(words[1])
                    elif words[0] == 'validation' and isTrue(words[1]): self.validation = True
                    elif words[0] == 'keepAlive': self.keepAlive = isTrue(words[1])
                    elif words[0] == 'debug' and isTrue(words[1]): self.debug = True
                    elif words[0] == 'mtime': self.mtime = int(words[1])
                    elif words[0] == 'sorter': self.sorter = words[1]
                    elif words[0] == 'header': self.headers.append(words[1])
                    elif words[0] == 'hours': self.issue_hours.append(words[1])
                    elif words[0] == 'primary': self.issue_primary.append(words[1])
                    elif words[0] == 'cycle': self.issue_cycle.append(words[1])
                    elif words[0] == 'feed': self.feeds.append(words[1])
                    elif words[0] == 'routingTable': self.routingTable = words[1]
                    elif words[0] == 'fx_script': self.fx_execfile = words[1]
                    elif words[0] == 'lx_script': self.lx_execfile = words[1]
                    elif words[0] == 'pull_script': self.pull_execfile = words[1]
                    elif words[0] == 'vip': self.vip = words[1]

                    elif words[0] == 'arrival':
                         if self.mapEnteteDelai == None : self.mapEnteteDelai = {}
                         self.mapEnteteDelai[words[1]] = (int(words[2]), int(words[3]))
		  
	  	    elif words[0] == 'logrotate':
                         if words[1].isdigit():
                                self.logger.setBackupCount(int(words[1]))

                    # options for pull
                    elif words[0] == 'directory': 
                         currentDir = words[1]
                         currentLST = []
                         # permit directory duplications but warn
                         for lst in self.pulls :
                             if lst[0] == currentDir :
                                currentLST = lst
                                break
                         if len(currentLST) != 0 :
                            self.logger.warning("This directory appears twice %s" % currentDir)
                            self.logger.warning("Please correct your config")
                            continue
                         # normal directory addition
                         currentLST.append( currentDir )
                         self.pulls.append( currentLST )
                    elif words[0] == 'get':
                         currentFilePattern = words[1]
                         currentLST.append(currentFilePattern)
                    elif words[0] == 'destination':
                        self.url = words[1]
                        urlParser = URLParser(words[1])
                        (self.protocol, currentDir, self.user, self.passwd, self.host, self.port) =  urlParser.parse()
                        if len(words) > 2:
                            currentFileOption = words[2]
                        currentLST = []
                        currentLST.append( currentDir )
                        self.pulls.append( currentLST )
                    elif words[0] == 'protocol': self.protocol = words[1]
                    elif words[0] == 'host': self.host = words[1]
                    elif words[0] == 'user': self.user = words[1]
                    elif words[0] == 'password': self.passwd = words[1]
                    elif words[0] == 'ssh_keyfile': self.ssh_keyfile = words[1]
                    elif words[0] == 'timeout_get': self.timeout_get = int(words[1])
                    elif words[0] == 'ftp_mode': self.ftp_mode = words[1]
                    elif words[0] == 'pull_sleep': self.pull_sleep = int(words[1])
                    elif words[0] == 'pull_wait': self.pull_wait = int(words[1])
                    elif words[0] == 'delete': self.delete = isTrue(words[1])
                    elif words[0] == 'pull_prefix': self.pull_prefix = words[1]


                    # AMQP
                    elif words[0] == 'exchange_key': self.exchange_key = words[1]
                    elif words[0] == 'exchange_name': self.exchange_name = words[1]
                    elif words[0] == 'exchange_realm': self.exchange_realm = words[1]
                    elif words[0] == 'exchange_type':
                         if words[1] in ['fanout','direct','topic','headers'] :
                            self.exchange_type = words[1]
                         else :
                            self.logger.error("Problem with exchange_type %s" % words[1])

                    # options for collector
                    if   self.type == 'collector' :
                         if   words[0] == 'aaxx'   : self.aaxx  = words[1].split(',')
                         if   words[0] == 'metar'  : self.metar = words[1].split(',')
                         elif words[0] == 'taf'    : self.taf = words[1].split(',')
                         elif words[0] == 'history': self.history = int(words[1])
                         elif words[0] == 'future' : self.future = int(words[1])
                         elif words[0] == 'issue'  : 
                                                     if words[1] == 'all' :
                                                        lst = []
                                                        lst.append(words[1])
                                                        self.issue_hours.append(lst)
                                                     else :
                                                        lst = words[1].split(",")
                                                        self.issue_hours.append( lst )
                                                     self.issue_primary.append(  int(words[2])       )
                                                     self.issue_cycle.append(    int(words[3])       )

                except:
                    self.logger.error("Problem with this line (%s) in configuration file of source %s" % (words, self.name))

        config.close()

        if len(self.masks) > 0 : self.patternMatching = True
        if len(self.masks_deprecated) > 0 : self.patternMatching = True

        self.logger.debug("Configuration file of source  %s has been read" % (self.name))

    def run_fx_script(self, filename, logger):
        if self.fx_script == None : return filename
        return self.fx_script(filename, logger)

    def run_lx_script(self, filelist, logger):
        if self.lx_script == None : return filelist
        return self.lx_script(filelist, logger)

    def run_pull_script(self, flow, logger, sleeping):
        filelist = []
        if self.pull_script == None : return filelist
        return self.pull_script(flow, logger, sleeping)

    def getTransformation(self, filename):
        for mask in self.tmasks:
            if fnmatch.fnmatch(filename, mask[0]):
                try:
                    return mask[1]
                except:
                    return None
        return None

    def fileMatchMask(self, filename):
    # IMPORTANT NOTE HERE FALLBACK BEHAVIOR IS TO ACCEPT THE FILE
    # THIS IS THE OPPOSITE OF THE CLIENT WHERE THE FALLBACK IS REJECT

        # check against the deprecated masks

        if len(self.masks_deprecated) > 0 :
           for mask in self.masks_deprecated:
               if fnmatch.fnmatch(filename, mask[0]):
                  try:
                       if mask[2]: return True
                  except:
                       return False

        # check against the masks
        for mask in self.masks:
            if mask[3].match(filename) : return mask[4]

        # fallback behavior 
        return True

    def printInfos(self, source):
        print("==========================================================================")
        print("Name: %s " % source.name)
        print("Type: %s" % source.type)
        print("Batch: %s" %  source.batch)
        print("Cache_size: %s" %  source.cache_size)
        print("Bulletin_type: %s" %  source.bulletin_type)
        print("Port: %s" % source.port)
        print("TCP SO_KEEPALIVE: %s" % source.keepAlive)
        print("Extension: %s" % source.extension)
        print("Arrival_Extension: %s" % source.arrival_extension)
        print("Arrival: %s" % source.mapEnteteDelai)
        print("addSMHeader: %s" % source.addSMHeader)
        print("addStationInFilename: %s" % source.addStationInFilename)
        print("Validation: %s" % source.validation)
        print("Source Pattern Matching: %s" % source.patternMatching)
        print("Clients Pattern Matching: %s" % source.clientsPatternMatching)
        print("mtime: %s" % source.mtime)
        print("Sorter: %s" % source.sorter)
        print("Routing table: %s" % source.routingTable)
        print("Route with Mask: %s" % source.routemask)
        print("No duplicates: %s" % source.nodups)
        print("FX script: %s" % source.fx_execfile)
        print("LX script: %s" % source.lx_execfile)
        print("Pull script: %s" % source.pull_execfile)
        print("VIP : %s" % source.vip)

        print("******************************************")
        print("*       AMQP stuff                       *")
        print("******************************************")

        print("exchange_key: %s" % source.exchange_key)
        print("exchange_name: %s" % source.exchange_name)
        print("exchange_realm: %s" % source.exchange_realm)
        print("exchange_type: %s" % source.exchange_type)

        print("******************************************")
        print("*       Source Masks                     *")
        print("******************************************")

        for mask in self.masks:
            if mask[4] : 
               print(" accept %s" % mask[0])
            else :
               print(" reject %s" % mask[0])

        print("*       Source Masks deprecated          *")
        for mask in self.masks_deprecated:
            print mask

        print("==========================================================================")

        print("******************************************")
        print("*       Source T-Masks                   *")
        print("******************************************")

        for mask in self.tmasks:
            print mask

        print("==========================================================================")

        print("******************************************")
        print("*       sources to feed (collections...) *")
        print("******************************************")

        for feed in self.feeds:
            print feed

        print("==========================================================================")

        if self.type == 'pull-file' :
           print("******************************************")
           print("*       Pull Params                      *")
           print("******************************************")

           print "protocol          %s" % self.protocol
           print "host              %s" % self.host
           print "user              %s" % self.user
           print "passwd            %s" % self.passwd
           print "ssh_keyfile       %s" % self.ssh_keyfile
           print "ftp_mode          %s" % self.ftp_mode
           print ""
           print "delete            %s" % self.delete
           print "pull_sleep        %s" % self.pull_sleep
           print "pull_wait         %s" % self.pull_wait
           print "pull_prefix       %s" % self.pull_prefix
           print "timeout_get       %s" % self.timeout_get

           print ""
           for lst in self.pulls :
               for pos, elem in enumerate(lst):
                   if pos == 0 : print "directory         %s" % elem
                   else        : print "get               %s" % elem

        print("==========================================================================")

        if self.type == 'collector' :
           print("******************************************")
           print("*       Collection Params                *")
           print("******************************************")
           print "bulletin aaxx  %s" % self.aaxx
           print "bulletin metar %s" % self.metar
           print "bulletin taf   %s" % self.taf

           for position, header in enumerate(self.headers):
               print "\nHeader %s" % header
               lst = self.issue_hours[position]
               print "issue hours         %s" % lst
               print "issue primary       %s" % self.issue_primary[position]
               print "issue cycle         %s" % self.issue_cycle[position]

           print "history             %s" % self.history
           print "future              %s" % self.future

           print("==========================================================================")


    def validateCollectionParams(self):
        """ validateCollectionParams(self)

        The purpose of this method is to make sure that the collection config parameters
        are valid.
        """
        if self.type == 'collector':

            #-----------------------------------------------------------------------------------------
            # Check other collection parameters.  All lists below should have the same size
            #-----------------------------------------------------------------------------------------
            if not (len(self.headers)== len(self.issue_hours)== len(self.issue_primary) == len(self.issue_cycle)):
                    self.logger.error("Error: There should be the same number of parameters given for EACH header in Configuration file: %s" % (self.name))
                    self.terminateWithError()

            #-----------------------------------------------------------------------------------------
            # Make sure that issue_hours is valid
            #-----------------------------------------------------------------------------------------
            for item in self.issue_hours:
                if len(item) == 1 and item[0] == "all" : continue
                for i in item :
                    if int(i) < 0 or int(i) > 23:
                       self.logger.error("Error: The given 'headerHours' parameter in Configuration file: %s must be between 0 and 23 or all" % (self.name))
                       self.terminateWithError()

            #-----------------------------------------------------------------------------------------
            # Make sure that issue_primary is valid
            #-----------------------------------------------------------------------------------------
            for item in self.issue_primary:
                if (int(item) < 1) or (int(item) > 60):
                    self.logger.error("Error: The given 'primary' parameter in Configuration file: %s must be positive" % (self.name))
                    self.terminateWithError()
            
            #-----------------------------------------------------------------------------------------
            # Make sure that issue_cycle is valid
            #-----------------------------------------------------------------------------------------
            for item in self.issue_cycle:
                if (int(item) < 0):
                    self.logger.error("Error: The given 'cycle' parameter in Configuration file: %s must be positive" % (self.name))
                    self.terminateWithError()

            #-----------------------------------------------------------------------------------------
            # Make sure that history is valid
            #-----------------------------------------------------------------------------------------
            if self.history <= 0 :
               self.logger.error("Error: The 'history' parameter is given an invalid value in Configuration file: %s" % (self.name))
               self.terminateWithError()

            #-----------------------------------------------------------------------------------------
            # Make sure that future is valid
            #-----------------------------------------------------------------------------------------
            if self.future < 0 :
               self.logger.error("Error: The 'future' parameter is given an invalid value in Configuration file: %s" % (self.name))
               self.terminateWithError()

    def terminateWithError (self):
        """ terminateWithError(self)

        The purpose of this method is to perform cleanup operations and return from the script 
        with an error
        """
        #-----------------------------------------------------------------------------------------
        # perform cleanup before termination
        #-----------------------------------------------------------------------------------------

        #-----------------------------------------------------------------------------------------
        # Terminate this script
        #-----------------------------------------------------------------------------------------
        sys.exit()

      
if __name__ == '__main__':

    """
    source=  Source('tutu')
    #source.readConfig()
    source.printInfos(source)
    source.ingestor.createDir('/apps/px/turton', source.ingestor.dbDirsCache)
    source.ingestor.setClients()
    print source.ingestor.getIngestName('toto:titi:tata')
    print source.ingestor.getClientQueueName('tutu', source.ingestor.getIngestName('toto:titi:tata'))
    print source.ingestor.getDBName(source.ingestor.getIngestName('toto:titi:tata'))
    print source.ingestor.isMatching(source.ingestor.clients['amis'], source.ingestor.getIngestName('toto:titi:tata'))
    print source.ingestor.getMatchingClientNamesFromMasks(source.ingestor.getIngestName('toto:titi:tata'))
    """
    """
    for filename in os.listdir(PXPaths.RX_CONF):
        if filename[-5:] != '.conf': 
            continue
        else:
            source = Source(filename[:-5])
            source.readConfig()
            source.printInfos(source)
            source.ingestor.setClients()
            print source.ingestor.getIngestName('toto')

    source = Source('wmo')
    if source.getTransformation('ALLOxxxxBonjour'): print source.getTransformation('ALLOxxxxBonjour')
    if source.getTransformation('TUTU'): print source.getTransformation('TUTU')
    if source.getTransformation('*Salut*Bonjour'): print source.getTransformation('*Salut*Bonjour')
    
    source=  Source('collecteur')
    source.readConfig('/tmp/trunk/sundew/etc/rx/collecteur.conf')
    source.printInfos(source)
    """
