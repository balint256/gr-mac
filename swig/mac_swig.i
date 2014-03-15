/* -*- c++ -*- */

#define MAC_API

%include "gnuradio.i"	// the common stuff

//load generated python docstrings
%include "mac_swig_doc.i"

%{
//#include "mac/square_ff.h"
#include "mac/burst_tagger.h"
%}

//%include "mac/square_ff.h"
//GR_SWIG_BLOCK_MAGIC2(mac, square_ff);

%include "mac/burst_tagger.h"
GR_SWIG_BLOCK_MAGIC2(mac, burst_tagger);
