#!/usr/bin/env python
##################################################
# Gnuradio Python Flow Graph
# Title: Top Block
# Generated: Tue Nov  5 14:22:33 2013
##################################################

from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from grc_gnuradio import wxgui as grc_wxgui
from optparse import OptionParser
import mac
import pmt
import wx

class top_block(grc_wxgui.top_block_gui):

    def __init__(self):
        grc_wxgui.top_block_gui.__init__(self, title="Top Block")
        _icon_path = "/usr/share/icons/hicolor/32x32/apps/gnuradio-grc.png"
        self.SetIcon(wx.Icon(_icon_path, wx.BITMAP_TYPE_ANY))

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 32000

        ##################################################
        # Blocks
        ##################################################
        self.simple_mac_0_0 = mac.simple_mac(1,0.1,10)
        self.simple_mac_0 = mac.simple_mac(0,0.1,10)
        self.mac_virtual_channel_encoder_0 = mac.virtual_channel_encoder(0,0)
        self.blocks_random_pdu_0 = blocks.random_pdu(5, 5)
        self.blocks_message_strobe_0 = blocks.message_strobe(pmt.intern("TEST"), 1000)
        self.blocks_message_debug_0 = blocks.message_debug()

        ##################################################
        # Asynch Message Connections
        ##################################################
        self.msg_connect(self.simple_mac_0, "to_radio", self.simple_mac_0_0, "from_radio")
        self.msg_connect(self.simple_mac_0_0, "to_radio", self.simple_mac_0, "from_radio")
        self.msg_connect(self.blocks_message_strobe_0, "strobe", self.blocks_random_pdu_0, "generate")
        self.msg_connect(self.blocks_random_pdu_0, "pdus", self.mac_virtual_channel_encoder_0, "in")
        self.msg_connect(self.mac_virtual_channel_encoder_0, "out", self.simple_mac_0_0, "from_app")
        self.msg_connect(self.simple_mac_0, "to_app", self.blocks_message_debug_0, "print_pdu")

# QT sink close method reimplementation

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate

if __name__ == '__main__':
    import ctypes
    import os
    if os.name == 'posix':
        try:
            x11 = ctypes.cdll.LoadLibrary('libX11.so')
            x11.XInitThreads()
        except:
            print "Warning: failed to XInitThreads()"
    parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
    (options, args) = parser.parse_args()
    tb = top_block()
    tb.Start(True)
    tb.Wait()

