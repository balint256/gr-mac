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
from gnuradio.digital import packet_utils
import gnuradio.digital as gr_digital
import Queue
import time

OTA_OUT = 'U'
USER_DATA = 'D'
USER_DATA_MULTIPLEXED = 'E'

OTA_IN = 'V'
INTERNAL = 'W'

HEARTBEAT = 'H'


ARQ_REQ = 85
ARQ_NO_REQ = 86

ARQ_PROTOCOL_ID = 90
BROADCAST_PROTOCOL_ID = 91
USER_IO_PROTOCOL_ID = 92
USER_IO_MULTIPLEXED_ID = 93

BROADCAST_ADDR = 255

#block port definitions
RADIO_PORT = 0
APP_PORT = 1
CTRL_PORT = 2

#msg key indexes for radio outbound blobs
KEY_INDEX_CTRL = 0
KEY_INDEX_DEST_ADDR = 1

#msg key indexes for internal control messages
KEY_INT_MSG_TYPE = 0    

#Packet index definitions
PKT_INDEX_CTRL = 4
PKT_INDEX_PROT_ID = 3     
PKT_INDEX_DEST = 2
PKT_INDEX_SRC = 1
PKT_INDEX_CNT = 0

#ARQ Channel States
ARQ_CHANNEL_BUSY = 1
ARQ_CHANNEL_IDLE = 0

# /////////////////////////////////////////////////////////////////////////////
#                   Simple MAC w/ ARQ
# /////////////////////////////////////////////////////////////////////////////

class simple_mac(gr.basic_block):
    """
    docstring for block mac
    """
    def __init__( self,addr,timeout,max_attempts):
        gr.basic_block.__init__(self,
            name="simple_mac",
            in_sig=None,
            out_sig=None)
        
        self.addr = addr                                #MAC's address
        
        self.pkt_cnt_arq = 0                            #pkt_cnt for arq channel
        self.pkt_cnt_no_arq = 0                            #pkt_cnt for non_arq channel
        
        self.arq_expected_sequence_number = 0            #keep track for sequence error detection
        self.no_arq_expected_sequence_number = 0        #keep track for sequence error detection

        self.arq_sequence_error_cnt = 0                    #arq channel seq errors - VERY BAD
        self.no_arq_sequence_error_cnt = 0                #non-arq channel seq error count
        self.arq_pkts_txed = 0                            #how many arq packets we've transmitted
        self.arq_retxed = 0                                #how many times we've retransmitted
        self.failed_arq = 0
        self.max_attempts = max_attempts
        self.throw_away = False
                                
        self.arq_channel_state = ARQ_CHANNEL_IDLE
        self.expected_arq_id = 0                        #arq id we're expected to get ack for      
        self.timeout = timeout                            #arq timeout parameter
        self.time_of_tx = 0.0                            #time of last arq transmission
        
        self.queue = Queue.Queue()                        #queue for msg destined for ARQ path
        
        
        #message i/o for radio interface
        self.message_port_register_out(pmt.intern('to_radio'))
        self.message_port_register_in(pmt.intern('from_radio'))
        self.set_msg_handler(pmt.intern('from_radio'),self.radio_rx)

        #message i/o for app interface
        self.message_port_register_out(pmt.intern('to_app'))
        self.message_port_register_in(pmt.intern('from_app'))
        self.set_msg_handler(pmt.intern('from_app'),self.app_rx)

        #message i/o for ctrl interface
        self.message_port_register_out(pmt.intern('ctrl_out'))
        self.message_port_register_in(pmt.intern('ctrl_in'))
        self.set_msg_handler(pmt.intern('ctrl_in'),self.ctrl_rx)
    
    #transmit layer 3 broadcast packet
    def send_bcast_pkt(self):
        msg = ''
        self.send_pkt_radio_2(msg,BROADCAST_ADDR,BROADCAST_PROTOCOL_ID,ARQ_NO_REQ)
    
    

    
    #transmit ack packet
    def send_ack(self,ack_addr,ack_pkt_cnt):
       data = (ack_pkt_cnt,)
       meta_dict = {}
       meta_dict['EM_DEST_ADDR'] = ack_addr
       pdu_tuple = ( data, meta_dict )
       self.tx_no_arq(pdu_tuple,ARQ_PROTOCOL_ID)
       return
    
    #transmit data through non-arq path    
    def tx_no_arq(self,pdu_tuple,protocol_id):
        self.send_pkt_radio(pdu_tuple,self.pkt_cnt_no_arq,protocol_id,ARQ_NO_REQ)
        self.pkt_cnt_no_arq = ( self.pkt_cnt_no_arq + 1 ) % 255
        return
    
    #transmit data - msg is numpy array
    def send_pkt_radio(self,pdu_tuple,pkt_cnt,protocol_id,control):

        #create header, merge with payload, convert to pmt for message_pub
        data = (pkt_cnt,self.addr,pdu_tuple[1]['EM_DEST_ADDR'],protocol_id,control) + pdu_tuple[0]

        data = pmt.init_u8vector(len(data),data)
        
        meta = pmt.to_pmt({})
        
        #construct pdu and publish to radio port
        pdu = pmt.cons(meta,data)
        
        #publish to msg port
        self.message_port_pub(pmt.intern('to_radio'),pdu)       
        return   
    
    
    #transmit data through arq path
    def tx_arq(self,pdu_tuple,protocol_id):
        self.send_pkt_radio(pdu_tuple,self.pkt_cnt_arq,protocol_id,ARQ_REQ)
        return
        

        
    def output_user_data(self,pdu_tuple):
        if (len(pdu_tuple[0])  > 5):
            data = pdu_tuple[0][5:]
            
        data = pmt.init_u8vector(len(data),data)

        #pass through metadata if there is any
        meta = pmt.to_pmt(pdu_tuple[1])

        self.message_port_pub(pmt.intern('to_app'),pmt.cons(meta,data))
        
        

    def radio_rx(self,msg):
        try:            
            meta = pmt.car(msg)
            data =  pmt.cdr(msg)
        except:
            raise NameError("mac - input not a PDU")
            
        if pmt.is_u8vector(data):
            data = pmt.u8vector_elements(data)
        else:
            raise NameError("Data is not u8 vector")
            
        incoming_pkt = data    #get data
        if ( len(incoming_pkt) > 5 ): #check for weird header only stuff
            if( ( incoming_pkt[PKT_INDEX_DEST] == self.addr or incoming_pkt[PKT_INDEX_DEST] == 255)  and not incoming_pkt[PKT_INDEX_SRC] == self.addr):    #for us?  
                   
                #check to see if we must ACK this packet
                if(incoming_pkt[PKT_INDEX_CTRL] == ARQ_REQ): #TODO, stuff CTRL and Protocol in one field
                    self.send_ack(incoming_pkt[PKT_INDEX_SRC],incoming_pkt[PKT_INDEX_CNT])                        #Then send ACK then
                    if not (self.arq_expected_sequence_number == incoming_pkt[PKT_INDEX_CNT]):
                        self.arq_sequence_error_cnt += 1
                        self.throw_away = True
                        #print "Throw away"
                    else:
                        self.throw_away = False
                    self.arq_expected_sequence_number =  ( incoming_pkt[PKT_INDEX_CNT] + 1 ) % 255 
                    
                else:
                    if not (self.no_arq_expected_sequence_number == incoming_pkt[PKT_INDEX_CNT]):
                        self.no_arq_sequence_error_cnt += 1
                        #print self.no_arq_sequence_error_cnt
                        #print self.no_arq_sequence_error_cnt,incoming_pkt[PKT_INDEX_CNT],self.no_arq_expected_sequence_number
                    self.no_arq_expected_sequence_number =  ( incoming_pkt[PKT_INDEX_CNT] + 1 ) % 255 

                incoming_protocol_id = incoming_pkt[PKT_INDEX_PROT_ID]
                
                #check to see if this is an ACK packet
                if(incoming_protocol_id == ARQ_PROTOCOL_ID):
                    if incoming_pkt[5] == self.expected_arq_id:
                        self.arq_channel_state = ARQ_CHANNEL_IDLE
                        self.pkt_cnt_arq = ( self.pkt_cnt_arq + 1 ) % 255
                    else:
                        print 'received out of sequence ack',incoming_pkt[5],self.expected_arq_id
                
                #do something with incoming user data
                elif(incoming_protocol_id == USER_IO_PROTOCOL_ID):
                    if not self.throw_away:
                        data = incoming_pkt
                        meta_dict = {}
                        pdu_tuple = (data,meta_dict)
                        self.output_user_data(pdu_tuple)   
                    self.throw_away = False
                        
                else:
                    print 'unknown protocol'
            
        self.run_arq_fsm()

        
    def app_rx(self,msg):
        try:            
            meta = pmt.car(msg)
            data =  pmt.cdr(msg)
        except:
            raise NameError("mac - input not a PDU")
            
        if pmt.is_u8vector(data):
            data = pmt.u8vector_elements(data)
        else:
            raise NameError("Data is not u8 vector")

        meta_dict = pmt.to_python(meta)
        if not (type(meta_dict) is dict):
            meta_dict = {}
        
        #double check to make sure correct meta data was in pdu
        if 'EM_USE_ARQ' in meta_dict.keys() and 'EM_DEST_ADDR' in meta_dict.keys():
            #assign tx path depending on whether PMT_BOOL EM_USE_ARQ is true or false
            if(meta_dict['EM_USE_ARQ']):
                self.queue.put( (data,meta_dict) )
            else:
                self.tx_no_arq(( data,meta_dict) ,USER_IO_PROTOCOL_ID)
        else:
            raise NameError("EM_USE_ARQ and/or EM_DEST_ADDR not specified in PDU")
            
        self.run_arq_fsm()
        
    def ctrl_rx(self,msg):
        self.run_arq_fsm()

    
    def run_arq_fsm(self):
        #check to see if we have any outgoing messages from arq buffer we should send
        #or pending re-transmissions
        if self.arq_channel_state == ARQ_CHANNEL_IDLE: #channel ready for next arq msg
            if not self.queue.empty(): #we have an arq msg to send, so lets send it
                #print self.queue.qsize()
                self.arq_pdu_tuple = self.queue.get() #get msg
                
                self.expected_arq_id = self.pkt_cnt_arq #store it for re-use
                
                self.tx_arq(self.arq_pdu_tuple,USER_IO_PROTOCOL_ID)
                
                self.time_of_tx = time.time() # note time for arq timeout recognition
                self.arq_channel_state = ARQ_CHANNEL_BUSY #remember that the channel is busy
                self.arq_pkts_txed += 1
                self.retries = 0
        else: #if channel is busy, lets check to see if its time to re-transmit
            if ( time.time() - self.time_of_tx ) > self.timeout: #check for ack timeout
                if self.retries == self.max_attempts:            #know when to quit
                    self.retries = 0 
                    self.arq_channel_state = ARQ_CHANNEL_IDLE
                    self.failed_arq += 1
                    self.pkt_cnt_arq = ( self.pkt_cnt_arq + 1 ) % 255   #start on next pkt
                    print 'pkt failed arq'
                else:    
                    self.tx_arq(self.arq_pdu_tuple,USER_IO_PROTOCOL_ID)
                    self.time_of_tx = time.time()
                    self.arq_retxed += 1
                    self.retries += 1
                    print "Retry"
                    #TODO: implement exponential back-off
