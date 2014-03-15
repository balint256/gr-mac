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

import numpy
from gnuradio import gr
from math import pi
import pmt

# ARQ definitions
#ARQ_FALSE   = 0
#ARQ_TRUE    = 1

class virtual_channel_encoder(gr.basic_block):
    """
    docstring for block virtual_channel_encoder
    Default MTU of 0 means data will not be fragmented.
    """
    def __init__(self, dest_addr, arq=False, mtu=0, chan_id=-1, prepend_dummy=False, chan_tracker=None):
        gr.basic_block.__init__(self,
            name="virtual_channel_encoder",
            in_sig=None,
            out_sig=None)
        
        self.dest_addr = dest_addr
        self.chan_id = chan_id
        self.arq = arq
        self.mtu = mtu
        self.prepend_dummy = prepend_dummy
        #self.blocking = False
        self.chan_tracker = chan_tracker
        
        self.message_port_register_out(pmt.intern('out'))
        try:
            self.message_port_register_in(pmt.intern('in'), True)
            print "Virtual channel encoder in blocking mode"
        except:
            self.message_port_register_in(pmt.intern('in'))
            #self.set_msg_handler(pmt.intern('in'), self.format)
            print "Virtual channel encoder in non-blocking mode"
        self.set_msg_handler(pmt.intern('in'), self.format)
        
        #if prepend_dummy:
        #    self.dummy_meta = pmt.to_pmt({'EM_USE_ARQ': False, 'EM_DUMMY': True})
        #    self.dummy_data = pmt.init_u8vector(0, [])
        
        #unique_id
        #name
    
    #def general_work(self, input_items, output_items):
    #    if not self.blocking:
    #        #msg = self.delete_head_nowait(pmt.intern('in'))
    #        msg = self.pop_msg_queue(pmt.intern('in'))
    #        if pmt.is_null(msg):
    #            return 0
    #        self.format(msg)
    #    else:
    #        print "Blocking"
    #    return 0
    
    def format(self, msg):
        data = pmt.cdr(msg)
        meta = pmt.car(msg)
        if not pmt.is_u8vector(data):
            #raise NameError("Data is no u8 vector")
            return "Message data is not u8vector"
        
        buf = list(pmt.u8vector_elements(data))   # returns a tuple
        
        meta_dict = pmt.to_python(meta)
        if not (type(meta_dict) is dict):
            meta_dict = {}
        
        #lets append some metadata to the pdu
        meta_dict['EM_USE_ARQ'] = self.arq
        meta_dict['EM_DEST_ADDR'] = self.dest_addr
        
        if self.chan_tracker:
            dest_addr = self.chan_tracker.get_addr(buf)
            if dest_addr != -1:
                meta_dict['EM_DEST_ADDR'] = dest_addr
        
        if self.prepend_dummy:
            meta_dict['EM_PREPEND_DUMMY'] = True
        
        if self.chan_id > -1:   # Actually layer 3
            meta_dict['EM_CHAN_ID'] = self.chan_id
        
        #print "[virtual_channel_encoder]", meta_dict
        
        #convert dictionary back to a pmt
        meta = pmt.to_pmt(meta_dict)
        
        #if self.prepend_dummy:
        #    self.message_port_pub(pmt.intern('out'), pmt.cons(self.dummy_meta, self.dummy_data))
        
        #self.blocking = True
        
        if self.mtu <= 0 or len(buf) <= self.mtu:
            if self.chan_id > -1:
                buf = [self.chan_id] + buf
                data = pmt.init_u8vector(len(buf), buf)
            #self.message_port_pub(pmt.intern('out'), pmt.cons(meta, data))
            self.post_msg(pmt.intern('out'), pmt.cons(meta, data))
        else:
            i = 0
            while len(buf) > 0:
                data = buf[:min(self.mtu,len(buf))]
                print "Forming fragment %d (%d bytes) with MTU %d" % ((i+1), len(data), self.mtu)
                if self.chan_id > -1:
                    data = [self.chan_id] + data
                data = pmt.init_u8vector(len(data), data)
                #self.message_port_pub(pmt.intern('out'), pmt.cons(meta, data))
                self.post_msg(pmt.intern('out'), pmt.cons(meta, data))
                buf = buf[min(self.mtu,len(buf)):]
                i += 1
        
        #self.blocking = False
