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
from constants import *

class fragment():
    def __init__(self, id, num):
        self.id = id
        self.parts = {}
        self.num = num
    def get_buf(self):
        buf = []
        for k in sorted(self.parts.keys()):
            buf += self.parts[k]
        return buf
    def update(self, idx, num, buf):
        if num != self.num:
            print "Total fragment count mismatch for fragment ID %d (expecting: %d, received: %d)" % (self.id, self.num, num)
            return None
        if idx in self.parts.keys():
            print "Already received fragment %d in fragment ID %d" % (idx, self.id)
            return None
        if idx >= self.num:
            print "Received fragment index %d greater than total %d for fragment ID %d" % (idx, self.num, self.id)
            return None
        self.parts[idx] = buf
        for i in range(self.num):
            if i not in self.parts.keys():
                return False
        return True

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
        
        self.frags = {}
        self.frag_age = 128
        
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
    
    def add_frag(self, frag_id, frag_idx, frag_num, buf):
        if frag_id not in self.frags.keys():
            self.frags[frag_id] = fragment(frag_id, frag_num)
        
        frag = self.frags[frag_id]
        result = frag.update(frag_idx, frag_num, buf)
        if result is None:
            del self.frags[frag_id]
            return None
        elif not result:
            return None
        
        buf = frag.get_buf()
        del self.frags[frag_id]
        #print "Re-assembled fragment %d (%d bytes total)" % (frag_id, len(buf))
        return buf
    
    def clean_frags(self, frag_id):
        old_id = frag_id - self.frag_age
        if old_id >= 0:
            lt_id = old_id
            gt_id = frag_id
        else:
            gt_id = frag_id
            lt_id = 256 + old_id
        for k in self.frags.keys():
            k_del = None
            if (lt_id < gt_id) and ((k < lt_id) or (k > gt_id)):
                k_del = k
            elif (lt_id > gt_id) and ((k < lt_id) and (k > gt_id)):
                k_del = k
            if k_del is not None:
                del self.frags[k_del]
                print "Deleted old fragment %d (received: %d)" % (k_del, frag_id)
    
    def demux(self, msg):
        data = pmt.cdr(msg)
        meta = pmt.car(msg)
        if not pmt.is_u8vector(data):
            #raise NameError("Data is no u8 vector")
            return "Message data is not u8vector"
        
        buf = pmt.u8vector_elements(data)
        if len(buf) <= 1:
            return
        
        meta_dict = pmt.to_python(meta)
        if not (type(meta_dict) is dict):
            meta_dict = {}
        
        self._demux(buf, meta_dict)
    
    def _demux(self, buf, meta_dict):
        header = []
        
        chan_flags = buf[0]
        # Added manually to reconstructed header
        buf = buf[1:]
        
        chan_id = None
        frag_id, frag_idx, frag_num = None, -1, 0
        
        try:
            if chan_flags & CHAN_FLAG_ID:
                chan_id = buf[0]
                header += buf[:1]
                buf = buf[1:]
            
            if chan_flags & CHAN_FLAG_FRAG:
                frag_id, frag_idx, frag_num = buf[0], buf[1], buf[2]
                # Ignore for header reconstruction
                buf = buf[3:]
        except:
            print "Exception parsing packet channel header"
            return
        
        if frag_id is not None:
            self.clean_frags(frag_id)
            
            frag_result = self.add_frag(frag_id, frag_idx, frag_num, buf)
            if frag_result is not None:
                chan_flags = (chan_flags & ~CHAN_FLAG_FRAG) & 0xFF
                buf = [chan_flags] + header + frag_result
                self._demux(buf, meta_dict)
            return
        
        if chan_id in self.channel_map.keys():
            out_name = self.channel_map[chan_id]
        else:
            out_name = 'out%d' % ((self.channel_count - 1))
        
        #lets append some metadata to the pdu
        meta_dict['EM_CHAN_ID'] = chan_id
        
        #print chan_id, out_name, meta_dict
        
        #print "[virtual_channel_decoder]", meta_dict
        
        #convert dictionary back to a pmt
        meta = pmt.to_pmt(meta_dict)
        
        data = pmt.init_u8vector(len(buf),buf)
        self.message_port_pub(pmt.intern(out_name), pmt.cons(meta, data))
