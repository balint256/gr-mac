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

#arq definitions
ARQ_FALSE = 0
ARQ_TRUE = 1

class virtual_channel_encoder(gr.basic_block):
    """
    docstring for block virtual_channel_encoder
    """
    def __init__(self,channel,arq):
        gr.basic_block.__init__(self,
            name="virtual_channel_encoder",
            in_sig=None,
            out_sig=None)
            
        self.channel = channel
        self.arq = arq

        self.message_port_register_out(pmt.intern('out'))
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'),self.format)
        
    def format(self,msg):
        data = pmt.cdr(msg)
        meta = pmt.car(msg)
        if not pmt.is_u8vector(data):
            raise NameError("Data is no u8 vector")
        
        meta_dict = pmt.to_python(meta)
        if not (type(meta_dict) is dict):
            meta_dict = {}
            
        #lets append some metadata to the pdu
        if self.arq == ARQ_TRUE:       
            meta_dict['EM_USE_ARQ'] = True
        else:
            meta_dict['EM_USE_ARQ'] = False
            
        meta_dict['EM_DEST_ADDR'] = self.channel    
        
        print meta_dict
        
        #convert dictionary back to a pmt
        meta = pmt.to_pmt(meta_dict)
        
        self.message_port_pub(pmt.intern('out'),pmt.cons(meta,data))       
