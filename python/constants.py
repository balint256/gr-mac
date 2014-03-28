#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  constants.py
#  
#  Copyright 2014 Balint Seeber <balint256@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

CHAN_FLAG_NONE  = 0x00
CHAN_FLAG_ID    = 0x01
CHAN_FLAG_FRAG  = 0x02

# ARQ definitions
#ARQ_FALSE   = 0
#ARQ_TRUE    = 1

#OTA_OUT = 'U'
#USER_DATA = 'D'
#USER_DATA_MULTIPLEXED = 'E'

#OTA_IN = 'V'
#INTERNAL = 'W'

HEARTBEAT = 'H'

ARQ_REQ = 85
ARQ_NO_REQ = 86

ARQ_PROTOCOL_ID = 90
BROADCAST_PROTOCOL_ID = 91
USER_IO_PROTOCOL_ID = 92
#USER_IO_MULTIPLEXED_ID = 93
DUMMY_PROTOCOL_ID = 94

BROADCAST_ADDR = 255

#block port definitions
#RADIO_PORT = 0
#APP_PORT = 1
#CTRL_PORT = 2

#msg key indexes for radio outbound blobs
#KEY_INDEX_CTRL = 0
#KEY_INDEX_DEST_ADDR = 1

#msg key indexes for internal control messages
#KEY_INT_MSG_TYPE = 0    

#Packet index definitions
PKT_INDEX_MAX = 5   # Packet length
PKT_INDEX_CTRL = 4
PKT_INDEX_PROT_ID = 3
PKT_INDEX_DEST = 2
PKT_INDEX_SRC = 1
PKT_INDEX_CNT = 0

#ARQ Channel States
ARQ_CHANNEL_BUSY = 1
ARQ_CHANNEL_IDLE = 0
