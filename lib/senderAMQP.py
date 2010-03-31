# -*- coding: iso-8859-1 -*-
# MetPX Copyright (C) 2004-2006  Environment Canada
# MetPX comes with ABSOLUTELY NO WARRANTY; For details type see the file
# named COPYING in the root of the source directory tree.

"""
#############################################################################################
# Name: senderAMQP.py
#
# Author: Michel Grenier
#
# Date: 2008-11-19
#
#############################################################################################

"""
import os, sys, time, string
from DiskReader import DiskReader
from MultiKeysStringSorter import MultiKeysStringSorter
from CacheManager import CacheManager
from TextSplitter import TextSplitter

import amqplib.client_0_8 as amqp

import PXPaths

PXPaths.normalPaths()

class senderAMQP: 
   
   def __init__(self, client, logger):
      self.client     = client                        # Client object (give access to all configuration options)
      self.timeout    = client.timeout                # No timeout for now
      self.logger     = logger                        # Logger object
      self.connection = None                          # The connection
      self.igniter    = None
      self.realm      = None
      self.ssl        = False
      self.reader     = DiskReader(PXPaths.TXQ  + self.client.name, self.client.batch,
                               self.client.validation, self.client.patternMatching,
                               self.client.mtime, True, self.logger, eval(self.client.sorter), self.client)

      self.debugFile    = False

      self.cacheManager = CacheManager(maxEntries=self.client.cache_size, timeout=8*3600)

      # AMQP  is there a max for bulletin size
      # self.set_maxLength(self.client.maxLength)

      # statistics.
      self.totBytes = 0
      self.initialTime = time.time()
      self.finalTime = None

      self._connect()

   def printSpeed(self):
      elapsedTime = time.time() - self.initialTime
      speed = self.totBytes/elapsedTime
      self.totBytes = 0
      self.initialTime = time.time()
      return "Speed = %i" % int(speed)

   def setIgniter(self, igniter):
      self.igniter = igniter 

   def resetReader(self):
      self.reader = DiskReader(PXPaths.TXQ  + self.client.name, self.client.batch,
                               self.client.validation, self.client.patternMatching,
                               self.client.mtime, True, self.logger, eval(self.client.sorter), self.client)

   def _connect(self):

      self.connection = None
      self.channel    = None
      self.realm      = None

      while True:
         try:
              host = self.client.host
              if self.client.port != None : host = host + ':' + self.client.port
              self.connection = amqp.Connection(host, userid=self.client.user, password=self.client.passwd, ssl=self.ssl)
              self.channel    = self.connection.channel()

              self.logger.info("AMQP Sender is now connected to: %s" % str(self.client.host))
              break
         except:
            (type, value, tb) = sys.exc_info()
            self.logger.error("Type: %s, Value: %s, Sleeping 5 seconds ..." % (type, value))
         time.sleep(5)

   def shutdown(self):
      pass

   def read(self):
      if self.igniter.reloadMode == True:
         # We assign the defaults and reread the configuration file (in __init__)
         if self.channel    != None : self.channel.close()
         if self.connection != None : self.connection.close()

         self.client.__init__(self.client.name, self.client.logger)

         self.resetReader()
         self.cacheManager.clear()
         self.logger.info("Cache has been cleared")
         self.logger.info("Sender AMQP has been reloaded")
         self.igniter.reloadMode = False

      self.reader.read()
      return self.reader.getFilesContent(self.client.batch)

   def write(self, data):
      if len(data) >= 1:
         self.logger.info("%d new bulletins will be sent", len(data) )

         for index in range(len(data)):

             # data info

             msg_body = data[index]
             nbBytesSent = len(msg_body)

             # if in cache than it was already sent... nothing to do
             # priority 0 is retransmission and is never suppressed

             path = self.reader.sortedFiles[index]
             priority = path.split('/')[-3]

             if self.client.nodups and priority != '0' and self.in_cache( data[index], True, path ) :
                #PS... same bug as in Senders AM, AMIS & WMO.
                #self.unlink_file( self.reader.sortedFiles[index] )
                continue

             # get/check destination Name
             basename = os.path.basename(path)
             destName, destDir = self.client.getDestInfos(basename)
             if not destName :
                os.unlink(path)
                self.logger.info('No destination name: %s has been erased' % path)
                continue

             self.realm = destDir
             if destDir[:2] == '//': self.realm = destDir[1:]

             try :
                    self.channel.access_request(self.realm, active=True, write=True)
                    self.channel.exchange_declare('myfan', 'fanout', auto_delete=True)

                    limit = nbBytesSent
                    if limit > 15 : limit = 15
                    pts = msg_body[:limit].split()

                    hdr = {'T1T2A1A2ii': pts[0], 'CCCC': pts[1]}
                    msg = amqp.Message(msg_body, content_type='text/plain', application_headers=hdr)
                    routing_key = pts[0] + '_' + pts[1]
                    self.channel.basic_publish(msg, 'myfan', routing_key )

                    self.logger.info("(%i Bytes) Bulletin %s  delivered" % (nbBytesSent, basename))
                    self.unlink_file( path )

                    self.totBytes += nbBytesSent
             except:
                    self.logger.info("%s: Sending problem" % path )
      else:
         time.sleep(1)

      if (self.totBytes > 108000):
         self.logger.info(self.printSpeed() + " Bytes/sec")
         # Log infos about caching
         (stats, cached, total) = self.cacheManager.getStats()
         if total:
            percentage = "%2.2f %% of the last %i requests were cached (implied %i files were deleted)" % (cached/total * 100,  total, cached)
         else:
            percentage = "No entries in the cache"
         self.logger.info("Caching stats: %s => %s" % (str(stats), percentage))

   def run(self):
      while True:
         data = self.read()
         try:
            self.write(data)
         except socket.error, e:
            (type, value, tb) = sys.exc_info()
            self.logger.error("Sender error! Type: %s, Value: %s" % (type, value))
            
            # We close the connection
            try:
                self.channel.close()
                self.connection.close()
            except:
                (type, value, tb) = sys.exc_info()
                self.logger.error("Problem in closing socket! Type: %s, Value: %s" % (type, value))

            # We try to reconnect. 
            self._connect()

         #time.sleep(0.2)

   # check if data in cache... if not it is added automatically
   def in_cache(self,data,unlink_it,path):
       already_in = False

        # If data is already in cache, we don't send it
       if self.cacheManager.find(data, 'md5') is not None:
           already_in = True
           if unlink_it :
              try:
                   os.unlink(path)
                   self.logger.info("suppressed duplicate send %s", os.path.basename(path))
              except OSError, e:
                   (type, value, tb) = sys.exc_info()
                   self.logger.info("in_cache unable to unlink %s ! Type: %s, Value: %s"
                                   % (path, type, value))

       return already_in

   # MG unlink file (isolated to clear code when segmentation was added)
   def unlink_file(self,path):
       try:
              os.unlink(path)
              self.logger.debug("%s has been erased", os.path.basename(path))
       except OSError, e:
              (type, value, tb) = sys.exc_info()
              self.logger.error("Unable to unlink %s ! Type: %s, Value: %s" % (path, type, value))

if __name__ == "__main__":
   from Logger import Logger
   from Client import Client

   logger = Logger('/apps/px/log/amqpTEST_MG.log', 'DEBUG', 'amqpTEST_MG')
   logger = logger.getLogger()

   client = Client('amqpTEST_MG', logger)
   client.host = "grogne.cmc.ec.gc.ca"
   client.user = 'guest'
   client.passwd = 'guest'
   client.ssl = False
   sender = senderAMQP(client, logger)
   sender.run()