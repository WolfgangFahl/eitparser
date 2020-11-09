#!/usr/bin/python
# encoding: utf-8
#
# EitSupport
# Copyright (C) 2011 betonme
# Copyright (C) 2016 Wolfgang Fahl
# 
# This EITParser is based on:
# https://github.com/betonme/e2openplugin-EnhancedMovieCenter/blob/master/src/EitSupport.py
#
# In case of reuse of this source code please do not remove this copyright.
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   For more information on the GNU General Public License see:
#   <http://www.gnu.org/licenses/>.
#
import pathlib
import os
import re
import struct
import sys
import time
import chardet

from datetime import datetime
def emcDebugOut(msg):
    print(msg,file=sys.stderr)
    
#from Components.config import config
#from Components.Language import language
#from EMCTasker import emcDebugOut
#from IsoFileSupport import IsoSupport

#from MetaSupport import getInfoFile

def parseMJD(MJD):
    # Parse 16 bit unsigned int containing Modified Julian Date,
    # as per DVB-SI spec
    # returning year,month,day
    YY = int( (MJD - 15078.2) / 365.25 )
    MM = int( (MJD - 14956.1 - int(YY*365.25) ) / 30.6001 )
    D  = MJD - 14956 - int(YY*365.25) - int(MM * 30.6001)
    K=0
    if MM == 14 or MM == 15: K=1

    return (1900 + YY+K), (MM-1-K*12), D

def unBCD(byte):
    return (byte>>4)*10 + (byte & 0xf)

#from Tools.ISO639 import LanguageCodes
# -*- coding: iso-8859-2 -*-
LanguageCodes = { }
LanguageCodes["deu"] = LanguageCodes["ger"] = LanguageCodes["de"] = ("German", "Germanic")
LanguageCodes["fra"] = LanguageCodes["fre"] = LanguageCodes["fr"] = ("French", "Romance")
def language_iso639_2to3(alpha2):
    ret = alpha2
    if alpha2 in LanguageCodes:
        language = LanguageCodes[alpha2]
        for alpha, name in LanguageCodes.items():
            if name == language:
                if len(alpha) == 3:
                    return alpha
    return ret

def bord(b):
    ''' 
    binary ord - just for code compatibility
    '''
    return b

class Bytes(object):
    
    def __init__(self):
        self.bytes=bytearray()
        
    def append(self,b):
        self.bytes.append(b)
        
    def toString(self):
        text=bytes(self.bytes).decode()
        return text
    
    @staticmethod
    def join(blist):
        '''
        join the list of bytes
        '''
        br=Bytes()
        for b in blist:
            br.bytes.extend(b.bytes)
        return br
    
    def strip(self):
        '''
        strip me
        '''
        # https://stackoverflow.com/questions/9560759/python-3-how-to-make-strip-work-for-bytes
        self.bytes=self.bytes.strip()
        return self
            
        
        
class Event(object):
    
    def __init__(self,name):
        self.name=name
        self.description=Bytes()
        self.descriptor = []
        self.descriptor_multi = []
        self.codepage = None
        
    @staticmethod
    def readLanguageCode(data,ofs):
        '''
        read the language code from the given offset in the data
        '''
        languageCode=Bytes()
        for i in range (ofs,ofs+3):
            languageCode.append(data[i])
        languageCode = languageCode.toString().upper()
        
    def readDescription(self,data,ofsStart,ofsEnd=None):
        '''
        read my description from the given offset
        '''
        if ofsEnd is None:
            self.event_name_length = bord(data[ofsStart])
            ofsStart=ofsStart+1
            ofsEnd=ofsStart+1+self.event_name_length
        
        for i in range (ofsStart,ofsEnd):
            try:
                if str(bord(data[i]))=="10" or int(str(bord(data[i])))>31:
                    self.description.append(data[i])
            except IndexError as e:
                emcDebugOut("[META] Exception in readEitFile: " + str(e))
                
    def appendDescription(self,lang, ISO_639_language_code,prev1_ISO_639_language_code,delim="\n\n"):
        if ISO_639_language_code == lang:
            self.descriptor.append(self.description)
        if (ISO_639_language_code == prev1_ISO_639_language_code) or (prev1_ISO_639_language_code == "x"):
            self.descriptor_multi.append(self.description)
        else:
            self.descriptor_multi.append(delim+ self.description)
            
    def joinDescriptor(self):
        if self.descriptor:
            self.descriptor = Bytes.join(self.descriptor)
        else:
            self.descriptor = Bytes.join(self.descriptor_multi).strip()
            
    def fixEncoding(self):
        if self.descriptor:
            try:
                # get back the raw bytes
                self.descriptor=bytes(self.descriptor.bytes)
                if self.codepage:
                    if self.codepage != 'utf-8':
                        self.descriptor = self.descriptor.decode(self.codepage).encode("utf-8")
                    else:
                        self.descriptor=self.descriptor.decode('utf-8')
                else:
                    encdata = chardet.detect(self.descriptor)
                    enc = encdata['encoding'].lower()
                    confidence = str(encdata['confidence'])
                    emcDebugOut("[META] Detected %s event encoding-type: %s ( %s )" % (self.name,enc,confidence))
                    if enc == "utf-8":
                        self.descriptor.decode(enc)
                    else:
                        self.descriptor = self.descriptor.decode(enc).encode('utf-8')
            except (UnicodeDecodeError, AttributeError) as e:
                emcDebugOut("[META] Exception in readEitFile: " + str(e))
        return self.descriptor

            
    def readCodepage(self,data,ofs):
        if self.codepage:
            return
        try:
            byte1 = str(bord(data[ofs]))
        except:
            byte1 = ''
        if byte1=="1": self.codepage = 'iso-8859-5'
        elif byte1=="2": self.codepage = 'iso-8859-6'
        elif byte1=="3": self.codepage = 'iso-8859-7'
        elif byte1=="4": self.codepage = 'iso-8859-8'
        elif byte1=="5": self.codepage = 'iso-8859-9'
        elif byte1=="6": self.codepage = 'iso-8859-10'
        elif byte1=="7": self.codepage = 'iso-8859-11'
        elif byte1=="9": self.codepage = 'iso-8859-13'
        elif byte1=="10": self.codepage = 'iso-8859-14'
        elif byte1=="11": self.codepage = 'iso-8859-15'
        elif byte1=="21": self.codepage = 'utf-8'
        if self.codepage:
            emcDebugOut("[META] Found %s encoding-type: %s" % (self.name,self.codepage))

# Eit File support class
# Description
# http://de.wikipedia.org/wiki/Event_Information_Table
class EitList():
    
    
    EIT_SHORT_EVENT_DESCRIPTOR = 0x4d
    EIT_EXTENDED_EVENT_DESCRIPOR = 0x4e

    def __init__(self, path=None):
        self.eit_file = None
        self.eit_mtime = 0

        #TODO
        # The dictionary implementation could be very slow
        self.eit = {}
        self.iso = None

        self.__newPath(path)
        self.__readEitFile()

        
    @staticmethod
    def readeit(eitroot):
        if os.path.isdir(eitroot):
            for p in pathlib.Path(eitroot).iterdir():
                if p.is_file():
                    if p.name.endswith(".eit"):
                        EitList.readeitFile(p)
        elif os.path.isfile(eitroot):
            EitList.readeitFile(eitroot)
            
    @staticmethod
    def readeitFile(eitfile):
        eitlist=EitList(eitfile)
        print(eitlist.getEitName());
        print(eitlist.getEitStartDate());
        print(eitlist.getEitDescription());    

    def __newPath(self, path):
        name = None
        if path:
            #TODO Too slow
            #if path.endswith(".iso"):
            #    if not self.iso:
            #        self.iso = IsoSupport(path)
            #    name = self.iso and self.iso.getIsoName()
            #    if name and len(name):
            #        path = "/home/root/dvd-" + name
            #el

            exts = [".eit"]
            #fpath = getInfoFile(path, exts)[1]
            #path = os.path.splitext(fpath)[0]

            #if not os.path.exists(path + ".eit"):
            #    # Strip existing cut number
            #    if path[-4:-3] == "_" and path[-3:].isdigit():
            #        path = path[:-4]
            #path += ".eit"
            if self.eit_file != path:
                self.eit_file = path
                self.eit_mtime = 0

    def __mk_int(self, s):
        return int(s) if s else 0

    def __toDate(self, d, t):
        if d and t:
            #TODO Is there another fast and safe way to get the datetime
            try:
                return datetime(int(d[0]), int(d[1]), int(d[2]), int(t[0]), int(t[1]))
            except ValueError:
                return None
        else:
            return None

    ##############################################################################
    ## Get Functions
    def getEitsid(self):
        return self.eit.get('service', "") #TODO

    def getEitTsId(self):
        return self.eit.get('transportstream', "") #TODO

    def getEitWhen(self):
        return self.eit.get('when', "")

    def getEitStartDate(self):
        return self.eit.get('startdate', "")

    def getEitStartTime(self):
        return self.eit.get('starttime', "")

    def getEitDuration(self):
        return self.eit.get('duration', "")

    def getEitName(self):
        return self.eit.get('name', "").strip()

    def getEitDescription(self):
        return self.eit.get('description', "").strip()

    def getEitShortDescription(self):
        return self.eit.get('short_description', "").strip()

    def getEitExtendedDescription(self):
        return self.getEitDescription()

    def getEitLengthInSeconds(self):
        length = self.eit.get('duration', "")
        #TODO Is there another fast and safe way to get the length
        if len(length)>2:
            return self.__mk_int((length[0]*60 + length[1])*60 + length[2])
        elif len(length)>1:
            return self.__mk_int(length[0]*60 + length[1])
        else:
            return self.__mk_int(length)

    def getEitDate(self):
        return self.__toDate(self.getEitStartDate(), self.getEitStartTime())

    ##############################################################################
    ## File IO Functions
    def __readEitFile(self,lang='de'):
        data = ""
        path = self.eit_file

        lang = (language_iso639_2to3(lang)).upper()

        if path and os.path.exists(path):
            mtime = os.path.getmtime(path)
            if self.eit_mtime == mtime:
                # File has not changed
                pass

            else:
                #print "EMC TEST count Eit " + str(path)

                # New path or file has changed
                self.eit_mtime = mtime

                # Read data from file
                # OE1.6 with Pyton 2.6
                #with open(self.eit_file, 'r') as file: lines = file.readlines()
                f = None
                try:
                    f = open(path, 'rb')
                    #lines = f.readlines()
                    data = f.read()
                except Exception as e:
                    emcDebugOut("[META] Exception in readEitFile: " + str(e))
                finally:
                    if f is not None:
                        f.close()

                # Parse the data
                if data and 12 <= len(data):
                    # go through events
                    pos = 0
                    e = struct.unpack(">HHBBBBBBH", data[pos:pos+12])
                    event_id = e[0]
                    date     = parseMJD(e[1])                         # Y, M, D
                    time     = unBCD(e[2]), unBCD(e[3]), unBCD(e[4])  # HH, MM, SS
                    duration = unBCD(e[5]), unBCD(e[6]), unBCD(e[7])  # HH, MM, SS
                    running_status  = (e[8] & 0xe000) >> 13
                    free_CA_mode    = e[8] & 0x1000
                    descriptors_len = e[8] & 0x0fff

                    if running_status in [1,2]:
                        self.eit['when'] = "NEXT"
                    elif running_status in [3,4]:
                        self.eit['when'] = "NOW"

                    self.eit['startdate'] = date
                    self.eit['starttime'] = time
                    self.eit['duration'] = duration

                    pos = pos + 12
                    name_event=Event("name")
                    short_event=Event("short")
                    extended_event=Event("extended")
            
                    component_descriptor = []
                    content_descriptor = []
                    linkage_descriptor = []
                    parental_rating_descriptor = []
                    endpos = len(data) - 1
                    prev1_ISO_639_language_code = "x"
                    prev2_ISO_639_language_code = "x"
                    while pos < endpos:
                        rec = bord(data[pos])
                        if pos+1>=endpos:
                            break
                        length = bord(data[pos+1]) + 2
                        #if pos+length>=endpos:
                        #    break
                        if rec == 0x4D:
                            descriptor_tag = bord(data[pos+1])
                            descriptor_length = bord(data[pos+2])
                            ISO_639_language_code = str(data[pos+2:pos+5]).upper()
                          
                            name_event.readDescription(data,pos+5)        
                            name_event.readCodepage(data,pos+6)
                            short_event.readCodepage(data, pos+7+name_event.event_name_length)
                            short_event.readDescription(data, pos+7+name_event.event_name_length,pos+length)
                            short_event.appendDescription(lang, ISO_639_language_code,prev1_ISO_639_language_code)
                            name_event.appendDescription(lang, ISO_639_language_code,prev1_ISO_639_language_code," ")
                            prev1_ISO_639_language_code = ISO_639_language_code
                        elif rec == 0x4E:
                            ISO_639_language_code = Event.readLanguageCode(data,pos+3)
                            extended_event.readCodepage(data, pos+8)
                            extended_event.readDescription(data, pos+8,pos+length)
                            extended_event.appendDescription(lang, ISO_639_language_code, prev2_ISO_639_language_code)
                            prev2_ISO_639_language_code = ISO_639_language_code
                        elif rec == 0x50:
                            component_descriptor.append(data[pos+8:pos+length])
                        elif rec == 0x54:
                            content_descriptor.append(data[pos+8:pos+length])
                        elif rec == 0x4A:
                            linkage_descriptor.append(data[pos+8:pos+length])
                        elif rec == 0x55:
                            parental_rating_descriptor.append(data[pos+2:pos+length])
                        else:
#                            print "unsupported descriptor: %x %x" %(rec, pos + 12)
#                            print data[pos:pos+length]
                            pass
                        pos += length
                    
                    name_event.joinDescriptor()
                    short_event.joinDescriptor()
                    extended_event.joinDescriptor()

                    if not(extended_event.descriptor):
                        extended_event.descriptor = short_event.descriptor
                        extended_event.codepage = short_event.codepage

                    self.eit['name'] = name_event.fixEncoding()
                    self.eit['short_description'] = short_event.fixEncoding()

                    # This will fix EIT data of RTL group with missing line breaks in extended event description
                    description=extended_event.fixEncoding()
                    if description:
                        description = re.sub('((?:Moderat(?:ion:|or(?:in){0,1})|Vorsitz: |Jur(?:isten|y): |G(?:\xC3\xA4|a)st(?:e){0,1}: |Mit (?:Staatsanwalt|Richter(?:in){0,1}|den Schadenregulierern) |Julia Leisch).*?[a-z]+)(\'{0,1}[0-9A-Z\'])', r'\1\n\n\2', description)
                    self.eit['description'] = description

                else:
                    # No date clear all
                    self.eit = {}

        else:
            # No path or no file clear all
            self.eit = {}
 

"""Module docstring.

Read Eit File and show the information.
"""
import getopt


def main():
    # parse command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
    except getopt.error as msg:
        print(msg)
        print("for help use --help")
        sys.exit(2)
    # process options
    for o, a in opts:
        if o in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
    # process arguments
    for arg in args:
        EitList.readeit(arg) # process() is defined elsewhere

if __name__ == "__main__":
    main()