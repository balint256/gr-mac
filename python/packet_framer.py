#
# Copyright 1980-2012 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 
import time, threading, traceback
import Queue
from math import pi
from gnuradio import gr
from gnuradio.digital import packet_utils
import gnuradio.digital as gr_digital
import pmt

# /////////////////////////////////////////////////////////////////////////////
#                   mod/demod with packets as i/o
# /////////////////////////////////////////////////////////////////////////////

class packet_framer(gr.basic_block):
    """
    The input is a pmt message blob.
    Non-blob messages will be ignored.
    The output is a byte stream for the modulator
    """
    def __init__(
        self,
        #samples_per_symbol,
        #bits_per_symbol,
        access_code=None,
        whitener_offset=0,
        rotate_whitener_offset=False,
        whiten=True,
        preamble='',
        postamble=''
    ):
        """
        Create a new packet framer.
        @param access_code: AKA sync vector
        @type access_code: string of 1's and 0's between 1 and 64 long
        @param use_whitener_offset: If true, start of whitener XOR string is incremented each packet
        """
        gr.basic_block.__init__(
            self,
            name="packet_framer",
            in_sig=None,
            out_sig=None)
        
        self.message_port_register_out(pmt.intern('out'))
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), self.packetise)
        
        if not access_code:
            access_code = packet_utils.default_access_code
        if not packet_utils.is_1_0_string(access_code):
            raise ValueError, "Invalid access_code %r. Must be string of 1's and 0's" % (access_code,)

        #self._bits_per_symbol = bits_per_symbol
        #self._samples_per_symbol = samples_per_symbol
        self.rotate_whitener_offset = rotate_whitener_offset
        self.whitener_offset = whitener_offset
        self.whiten = whiten
        self.access_code = access_code
        self.preamble = preamble
        self.postamble = postamble
    
    def packetise(self, msg):
        data = pmt.cdr(msg)
        meta = pmt.car(msg)
        if not pmt.is_u8vector(data):
            #raise NameError("Data is no u8 vector")
            return "Message data is not u8vector"
        
        buf = pmt.u8vector_elements(data)
        buf_str = "".join(map(chr, buf))
        
        # FIXME: Max: 4096-header-crc
        
        meta_dict = pmt.to_python(meta)
        if not (type(meta_dict) is dict):
            meta_dict = {}
        
        pkt = ""
        pkt += self.preamble
        pkt += packet_utils.make_packet(
            buf_str,
            0,#self._samples_per_symbol,
            0,#self._bits_per_symbol,
            #preamble=<default>
            access_code=self.access_code,
            pad_for_usrp=False,#pad_for_usrp,
            whitener_offset=self.whitener_offset,
            whitening=self.whiten
            )
        pkt += self.postamble
        pkt = map(ord, list(pkt))
        if self.rotate_whitener_offset:
            self.whitener_offset = (self.whitener_offset + 1) % 16
        meta = pmt.to_pmt(meta_dict)
        data = pmt.init_u8vector(len(pkt), pkt)
        self.message_port_pub(pmt.intern('out'), pmt.cons(meta, data))
        '''
        if len(self._pkt) == 0 :
            item_index = num_items #which output item gets the tag?
            offset = self.nitems_written(0) + item_index
            source = pmt.pmt_string_to_symbol("framer")                
            if self.has_tx_time:
                key = pmt.pmt_string_to_symbol("tx_sob")
                self.add_item_tag(0, self.nitems_written(0), key, pmt.PMT_T, source)
                key = pmt.pmt_string_to_symbol("tx_time")
                self.add_item_tag(0, self.nitems_written(0), key, pmt.from_python(self.tx_time), source)
       
            if self.more_frame_cnt == 0:
                key = pmt.pmt_string_to_symbol("tx_eob")
                self.add_item_tag(0, offset - 1, key, pmt.PMT_T, source)
            else:
                self.more_frame_cnt -= 1
        '''


class msg_to_pdu_thread(threading.Thread):
    def __init__(self, msgq, post_fn, **kwds):
        threading.Thread.__init__(self, **kwds)
        self.setDaemon(True)
        self.msgq = msgq
        self.keep_running = True
        self.stop_event = threading.Event()
        self.post_fn = post_fn
    def start(self):
        #print "Starting..."
        threading.Thread.start(self)
    def stop(self):
        #print "Stopping..."
        self.keep_running = False
        msg = gr.message()  # Empty message to signal end
        self.msgq.insert_tail(msg)
        self.stop_event.wait()
        #print "Stopped"
    #def __del__(self):
    #    print "DTOR"
    def run(self):
        if self.msgq:
            while self.keep_running:
                msg = self.msgq.delete_head()
                if self.keep_running == False:
                    break
                try:
                    msg_str = msg.to_string()
                    if len(msg_str) == 0:
                        continue
                    if self.post_fn:
                        self.post_fn(msg_str, msg.type(), msg.arg1(), msg.arg2())
                except Exception, e:
                    print e
                    traceback.print_exc()
        self.stop_event.set()


class packet_to_pdu(gr.basic_block):
    def __init__(self, msgq, dewhiten=True, output_invalid=False):
        gr.basic_block.__init__(self, name="packet_to_pdu", in_sig=None, out_sig=None)
        self.message_port_register_out(pmt.intern('pdu'))
        self.msgq = msgq
        self.dewhiten = dewhiten
        self.output_invalid = output_invalid
        self.thread = None
        self.start()
    def post_data(self, data, type=None, arg1=None, arg2=None):
        ok, payload = packet_utils.unmake_packet(data, int(arg1), self.dewhiten)
        if not ok:
            #print "Packet of length %d failed CRC" % (len(data))    # Max len is 4095
            if not self.output_invalid:
                return
        payload = map(ord, list(payload))
        buf = pmt.init_u8vector(len(payload), payload)
        meta_dict = {'CRC_OK': ok}
        meta = pmt.to_pmt(meta_dict)
        self.message_port_pub(pmt.intern('pdu'), pmt.cons(meta, buf))
    def start(self):
        if self.thread is None:
            self.thread = msg_to_pdu_thread(self.msgq, self.post_data)
            self.thread.start()
    def stop(self):
        if self.thread:
            self.thread.stop()
            self.thread = None
    def __del__(self):
        self.stop()


class packet_deframer(gr.hier_block2):
    """
    Hierarchical block for demodulating and deframing packets.

    The input is a byte stream from the demodulator.
    The output is a pmt message blob.
    """
    def __init__(
        self,
        msgq,
        access_code=None,
        threshold=0
        ):
        """
        Create a new packet deframer.
        @param access_code: AKA sync vector
        @type access_code: string of 1's and 0's
        @param threshold: detect access_code with up to threshold bits wrong
        @type threshold: int
        """
        gr.hier_block2.__init__(
            self,
            "packet_deframer",
            gr.io_signature(1, 1, 1),
            gr.io_signature(0, 0, 0)
        )
        
        if not access_code:
            access_code = packet_utils.default_access_code
        if not packet_utils.is_1_0_string(access_code):
            raise ValueError, "Invalid access_code %r. Must be string of 1's and 0's" % (access_code,)
        
        if threshold < 0:
            raise ValueError, "Invalid threshold value %d" % (threshold)
        
        #default_access_code = conv_packed_binary_string_to_1_0_string('\xAC\xDD\xA4\xE2\xF2\x8C\x20\xFC')
        #default_preamble = conv_packed_binary_string_to_1_0_string('\xA4\xF2')
        
        self.msgq = msgq
        self.correlator = gr_digital.correlate_access_code_bb(access_code, threshold)
        self.framer_sink = gr_digital.framer_sink_1(self.msgq)
        self.connect(self, self.correlator, self.framer_sink)

'''
class _queue_to_blob(gr.block):
    """
    Helper for the deframer, reads queue, unpacks packets, posts.
    It would be nicer if the framer_sink output'd messages.
    """
    def __init__(self, msgq):
        gr.block.__init__(
            self, name = "_queue_to_blob",
            in_sig = None, out_sig = None,
            num_msg_outputs = 1
        )
        self._msgq = msgq
        self._mgr = pmt.pmt_mgr()
        for i in range(64):
            self._mgr.set(pmt.pmt_make_blob(10000))

    def work(self, input_items, output_items):
        while True:
            try: msg = self._msgq.delete_head()
            except: return -1
            ok, payload = packet_utils.unmake_packet(msg.to_string(), int(msg.arg1()))
            if ok:
                payload = numpy.fromstring(payload, numpy.uint8)
                try: blob = self._mgr.acquire(True) #block
                except: return -1
                pmt.pmt_blob_resize(blob, len(payload))
                pmt.pmt_blob_rw_data(blob)[:] = payload
                self.post_msg(0, pmt.pmt_string_to_symbol("ok"), blob)
            else:
                a = 0
'''
