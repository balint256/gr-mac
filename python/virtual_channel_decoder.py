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
import pmt

class virtual_channel_decoder(gr.basic_block):
    """
    docstring for block virtual_channel_decoder
    """
    def __init__(self, channel_count, channel_map):
        gr.basic_block.__init__(self,
            name="virtual_channel_encoder",
            in_sig=None,
            out_sig=None)
        
        if len(channel_map) > channel_count:
            channel_map = channel_map[:channel_count]
        elif channel_count > len(channel_map):
            channel_count = len(channel_map) + 1
        
        self.channel_count = channel_count
        self.channel_map = {}
        
        for i in range(channel_count):
            out_name = 'out%d' % (i)
            if i < len(channel_map):
                self.channel_map[channel_map[i]] = out_name
            #print "[%s] Registered '%s'" % (self.name, out_name)
            self.message_port_register_out(pmt.intern(out_name))
        
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), self.demux)
    
    def demux(self, msg):
        data = pmt.cdr(msg)
        meta = pmt.car(msg)
        if not pmt.is_u8vector(data):
            #raise NameError("Data is no u8 vector")
            return "Message data is not u8vector"
        
        buf = pmt.u8vector_elements(data)
        chan_id = buf[0]
        buf = buf[1:]
        
        if chan_id in self.channel_map.keys():
            out_name = self.channel_map[chan_id]
        else:
            out_name = 'out%d' % ((self.channel_count - 1))
        
        meta_dict = pmt.to_python(meta)
        if not (type(meta_dict) is dict):
            meta_dict = {}
        
        #lets append some metadata to the pdu
        meta_dict['EM_CHAN_ID'] = chan_id
        
        #print chan_id, out_name, meta_dict
        
        #print "[virtual_channel_decoder]", meta_dict
        
        #convert dictionary back to a pmt
        meta = pmt.to_pmt(meta_dict)
        
        data = pmt.init_u8vector(len(buf),buf)
        self.message_port_pub(pmt.intern(out_name), pmt.cons(meta, data))
