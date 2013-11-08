#!/usr/bin/env python
##################################################
# Gnuradio Python Flow Graph
# Title: Simple Trx
# Generated: Thu Nov  7 16:31:24 2013
##################################################

from gnuradio import blocks
from gnuradio import digital
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio import uhd
from gnuradio import wxgui
from gnuradio.eng_option import eng_option
from gnuradio.fft import window
from gnuradio.filter import firdes
from gnuradio.wxgui import fftsink2
from grc_gnuradio import wxgui as grc_wxgui
from optparse import OptionParser
import mac
import pmt
import time
import wx

class simple_trx(grc_wxgui.top_block_gui):

    def __init__(self, args="", max_arq_attempts=10, dest_addr=86, arq_timeout=.10, radio_addr=0, samp_per_sym=4, rate=1e6, freq=915e6, port="12347", rx_freq=915e6, tx_freq=915e6, rx_antenna="TX/RX", rx_gain=5, ampl=0.5, tx_gain=5):
        grc_wxgui.top_block_gui.__init__(self, title="Simple Trx")
        _icon_path = "/usr/share/icons/hicolor/32x32/apps/gnuradio-grc.png"
        self.SetIcon(wx.Icon(_icon_path, wx.BITMAP_TYPE_ANY))

        ##################################################
        # Parameters
        ##################################################
        self.args = args
        self.max_arq_attempts = max_arq_attempts
        self.dest_addr = dest_addr
        self.arq_timeout = arq_timeout
        self.radio_addr = radio_addr
        self.samp_per_sym = samp_per_sym
        self.rate = rate
        self.freq = freq
        self.port = port
        self.rx_freq = rx_freq
        self.tx_freq = tx_freq
        self.rx_antenna = rx_antenna
        self.rx_gain = rx_gain
        self.ampl = ampl
        self.tx_gain = tx_gain

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = rate

        ##################################################
        # Blocks
        ##################################################
        self.wxgui_fftsink2_0 = fftsink2.fft_sink_c(
        	self.GetWin(),
        	baseband_freq=0,
        	y_per_div=10,
        	y_divs=10,
        	ref_level=0,
        	ref_scale=2.0,
        	sample_rate=samp_rate,
        	fft_size=1024,
        	fft_rate=15,
        	average=False,
        	avg_alpha=None,
        	title="FFT Plot",
        	peak_hold=False,
        )
        self.Add(self.wxgui_fftsink2_0.win)
        self.uhd_usrp_source_0 = uhd.usrp_source(
        	device_addr="",
        	stream_args=uhd.stream_args(
        		cpu_format="fc32",
        		channels=range(1),
        	),
        )
        self.uhd_usrp_source_0.set_samp_rate(samp_rate)
        self.uhd_usrp_source_0.set_center_freq(uhd.tune_request(rx_freq, 10e6), 0)
        self.uhd_usrp_source_0.set_gain(rx_gain, 0)
        self.uhd_usrp_source_0.set_antenna("TX/RX", 0)
        self.uhd_usrp_sink_0 = uhd.usrp_sink(
        	device_addr="",
        	stream_args=uhd.stream_args(
        		cpu_format="fc32",
        		channels=range(1),
        	),
        )
        self.uhd_usrp_sink_0.set_samp_rate(samp_rate)
        self.uhd_usrp_sink_0.set_center_freq(uhd.tune_request(tx_freq, 10e6), 0)
        self.uhd_usrp_sink_0.set_gain(tx_gain, 0)
        self.uhd_usrp_sink_0.set_antenna("TX/RX", 0)
        self.simple_mac_1 = mac.simple_mac(radio_addr,arq_timeout,max_arq_attempts)
        self.mac_virtual_channel_encoder_0 = mac.virtual_channel_encoder(dest_addr,0)
        self.digital_ofdm_tx_0 = digital.ofdm_tx(
        	  fft_len=64, cp_len=16,
        	  packet_length_tag_key="length",
        	  bps_header=1,
        	  bps_payload=1,
        	  rolloff=0,
        	  debug_log=False,
        	  scramble_bits=False
        	 )
        self.digital_ofdm_rx_1 = digital.ofdm_rx(
        	  fft_len=64, cp_len=16,
        	  frame_length_tag_key='frame_'+"length",
        	  packet_length_tag_key="length",
        	  bps_header=1,
        	  bps_payload=1,
        	  debug_log=False,
        	  scramble_bits=False
        	 )
        self.blocks_tagged_stream_to_pdu_0 = blocks.tagged_stream_to_pdu(blocks.byte_t, "length")
        self.blocks_socket_pdu_0 = blocks.socket_pdu("UDP_SERVER", "", port, 10000)
        self.blocks_pdu_to_tagged_stream_0 = blocks.pdu_to_tagged_stream(blocks.byte_t, "length")
        self.blocks_message_strobe_0 = blocks.message_strobe(pmt.intern("T"), 1)
        self.blocks_message_debug_0 = blocks.message_debug()

        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_pdu_to_tagged_stream_0, 0), (self.digital_ofdm_tx_0, 0))
        self.connect((self.digital_ofdm_rx_1, 0), (self.blocks_tagged_stream_to_pdu_0, 0))
        self.connect((self.digital_ofdm_tx_0, 0), (self.uhd_usrp_sink_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.wxgui_fftsink2_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.digital_ofdm_rx_1, 0))

        ##################################################
        # Asynch Message Connections
        ##################################################
        self.msg_connect(self.blocks_message_strobe_0, "strobe", self.simple_mac_1, "ctrl_in")
        self.msg_connect(self.simple_mac_1, "to_radio", self.blocks_pdu_to_tagged_stream_0, "pdus")
        self.msg_connect(self.blocks_tagged_stream_to_pdu_0, "pdus", self.simple_mac_1, "from_radio")
        self.msg_connect(self.blocks_tagged_stream_to_pdu_0, "pdus", self.blocks_message_debug_0, "print_pdu")
        self.msg_connect(self.blocks_socket_pdu_0, "pdus", self.mac_virtual_channel_encoder_0, "in")
        self.msg_connect(self.mac_virtual_channel_encoder_0, "out", self.simple_mac_1, "from_app")
        self.msg_connect(self.simple_mac_1, "to_app", self.blocks_socket_pdu_0, "pdus")

# QT sink close method reimplementation

    def get_args(self):
        return self.args

    def set_args(self, args):
        self.args = args

    def get_max_arq_attempts(self):
        return self.max_arq_attempts

    def set_max_arq_attempts(self, max_arq_attempts):
        self.max_arq_attempts = max_arq_attempts

    def get_dest_addr(self):
        return self.dest_addr

    def set_dest_addr(self, dest_addr):
        self.dest_addr = dest_addr

    def get_arq_timeout(self):
        return self.arq_timeout

    def set_arq_timeout(self, arq_timeout):
        self.arq_timeout = arq_timeout

    def get_radio_addr(self):
        return self.radio_addr

    def set_radio_addr(self, radio_addr):
        self.radio_addr = radio_addr

    def get_samp_per_sym(self):
        return self.samp_per_sym

    def set_samp_per_sym(self, samp_per_sym):
        self.samp_per_sym = samp_per_sym

    def get_rate(self):
        return self.rate

    def set_rate(self, rate):
        self.rate = rate
        self.set_samp_rate(self.rate)

    def get_freq(self):
        return self.freq

    def set_freq(self, freq):
        self.freq = freq

    def get_port(self):
        return self.port

    def set_port(self, port):
        self.port = port

    def get_rx_freq(self):
        return self.rx_freq

    def set_rx_freq(self, rx_freq):
        self.rx_freq = rx_freq
        self.uhd_usrp_source_0.set_center_freq(uhd.tune_request(self.rx_freq, 10e6), 0)

    def get_tx_freq(self):
        return self.tx_freq

    def set_tx_freq(self, tx_freq):
        self.tx_freq = tx_freq
        self.uhd_usrp_sink_0.set_center_freq(uhd.tune_request(self.tx_freq, 10e6), 0)

    def get_rx_antenna(self):
        return self.rx_antenna

    def set_rx_antenna(self, rx_antenna):
        self.rx_antenna = rx_antenna

    def get_rx_gain(self):
        return self.rx_gain

    def set_rx_gain(self, rx_gain):
        self.rx_gain = rx_gain
        self.uhd_usrp_source_0.set_gain(self.rx_gain, 0)

    def get_ampl(self):
        return self.ampl

    def set_ampl(self, ampl):
        self.ampl = ampl

    def get_tx_gain(self):
        return self.tx_gain

    def set_tx_gain(self, tx_gain):
        self.tx_gain = tx_gain
        self.uhd_usrp_sink_0.set_gain(self.tx_gain, 0)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.wxgui_fftsink2_0.set_sample_rate(self.samp_rate)
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)
        self.uhd_usrp_sink_0.set_samp_rate(self.samp_rate)

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
    parser.add_option("", "--args", dest="args", type="string", default="",
        help="Set args [default=%default]")
    parser.add_option("", "--max-arq-attempts", dest="max_arq_attempts", type="intx", default=10,
        help="Set max_arq_attempts [default=%default]")
    parser.add_option("", "--dest-addr", dest="dest_addr", type="intx", default=86,
        help="Set dest_addr [default=%default]")
    parser.add_option("", "--arq-timeout", dest="arq_timeout", type="eng_float", default=eng_notation.num_to_str(.10),
        help="Set arq_timeout [default=%default]")
    parser.add_option("", "--radio-addr", dest="radio_addr", type="intx", default=0,
        help="Set radio_addr [default=%default]")
    parser.add_option("", "--samp-per-sym", dest="samp_per_sym", type="intx", default=4,
        help="Set sps [default=%default]")
    parser.add_option("", "--rate", dest="rate", type="eng_float", default=eng_notation.num_to_str(1e6),
        help="Set S [default=%default]")
    parser.add_option("", "--freq", dest="freq", type="eng_float", default=eng_notation.num_to_str(915e6),
        help="Set freq [default=%default]")
    parser.add_option("", "--port", dest="port", type="string", default="12347",
        help="Set port [default=%default]")
    parser.add_option("", "--rx-freq", dest="rx_freq", type="eng_float", default=eng_notation.num_to_str(915e6),
        help="Set rx_freq [default=%default]")
    parser.add_option("", "--tx-freq", dest="tx_freq", type="eng_float", default=eng_notation.num_to_str(915e6),
        help="Set tx_freq [default=%default]")
    parser.add_option("", "--rx-antenna", dest="rx_antenna", type="string", default="TX/RX",
        help="Set rx_antenna [default=%default]")
    parser.add_option("", "--rx-gain", dest="rx_gain", type="eng_float", default=eng_notation.num_to_str(5),
        help="Set rx_gain [default=%default]")
    parser.add_option("", "--ampl", dest="ampl", type="eng_float", default=eng_notation.num_to_str(0.5),
        help="Set a [default=%default]")
    parser.add_option("", "--tx-gain", dest="tx_gain", type="eng_float", default=eng_notation.num_to_str(5),
        help="Set tx_gain [default=%default]")
    (options, args) = parser.parse_args()
    tb = simple_trx(args=options.args, max_arq_attempts=options.max_arq_attempts, dest_addr=options.dest_addr, arq_timeout=options.arq_timeout, radio_addr=options.radio_addr, samp_per_sym=options.samp_per_sym, rate=options.rate, freq=options.freq, port=options.port, rx_freq=options.rx_freq, tx_freq=options.tx_freq, rx_antenna=options.rx_antenna, rx_gain=options.rx_gain, ampl=options.ampl, tx_gain=options.tx_gain)
    tb.Start(True)
    tb.Wait()

