#!/usr/bin/env python
# 
# Copyright 2013 <+YOU OR YOUR COMPANY+>.
# 
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

from __future__ import with_statement

import threading
import numpy
from gnuradio import gr
import pmt

class tracker_802_3(gr.basic_block):
    """
    docstring for block virtual_channel_decoder
    """
    def __init__(self, verbose=False):
        gr.basic_block.__init__(self,
            name="802_3_tracker",
            in_sig=None,
            out_sig=None)
        
        self.verbose = verbose
        #self.chan_to_mac_map = {}
        self.mac_to_chan_map = {}
        self.lock = threading.Lock()
        
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), self.track)
    
    def track(self, msg):
        data = pmt.cdr(msg)
        meta = pmt.car(msg)
        if not pmt.is_u8vector(data):
            #raise NameError("Data is no u8 vector")
            return "Message data is not u8vector"
        
        buf = pmt.u8vector_elements(data)
        
        meta_dict = pmt.to_python(meta)
        if not (type(meta_dict) is dict):
            meta_dict = {}
        
        if not 'EM_SRC_ID' in meta_dict:
            if self.verbose:
                print "[%s] Packet without source channel ID" % (self.name)
            return
        src_id = meta_dict['EM_SRC_ID']
        
        if len(buf) < 18:
            if self.verbose:
                print "[%s] Packet is less than Ethernet minimum"
            return
        
        mac_dest = buf[0:6]
        mac_src = buf[6:12]
        
        mac_dest_str = ":".join(map(lambda x: ("%02X"%(x)), mac_dest))
        mac_src_str = ":".join(map(lambda x: ("%02X"%(x)), mac_src))
        
        #if self.verbose:
        #    print "[%s] (%02d) %s -> %s" % (self.name, src_id, mac_src_str, mac_dest_str)
        
        with self.lock:
            if mac_src_str in self.mac_to_chan_map and self.mac_to_chan_map[mac_src_str] != src_id:
                # Same MAC from different source ID
                if self.verbose:
                    print "[%s] Same MAC %s from different source ID %d (current mapping: %d)" % (self.name, mac_src_str, src_id, self.mac_to_chan_map[mac_src_str])
            elif not mac_src_str in self.mac_to_chan_map:
                print "[%s] %s -> %02d" % (self.name, mac_src_str, src_id)
            
            #if src_id in self.chan_to_mac_map and self.chan_to_mac_map[src_id] != mac_src_str:
            #    # Already have a MAC from a source ID, but now seeing a different MAC
            #    pass
            
            #self.chan_to_mac_map[src_id] = mac_src_str
            
            self.mac_to_chan_map[mac_src_str] = src_id
        
        #convert dictionary back to a pmt
        #meta = pmt.to_pmt(meta_dict)
        
        #data = pmt.init_u8vector(len(buf),buf)
        #self.message_port_pub(pmt.intern(out_name), pmt.cons(meta, data))
    
    def get_addr(self, buf):
        with self.lock:
            mac_str = None
            if (isinstance(buf, str) or isinstance(buf, list)) and len(buf) >= 6:
                mac_str = buf[0:6]
            if not mac_str:
                if self.verbose:
                    print "[%s:get_addr] Unknown argument type" % (self.name)
                return -1
            if not isinstance(buf, str):
                mac_str = ":".join(map(lambda x: ("%02X"%(x)), mac_str))
            if not mac_str in self.mac_to_chan_map:
                if self.verbose:
                    print "[%s:get_addr] MAC not in map: %s" % (self.name, mac_str)
                return -1
            return self.mac_to_chan_map[mac_str]
