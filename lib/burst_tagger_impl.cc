/*
 * Copyright 2014 Balint Seeber <balint256@gmail.com>.
 * Copyright 2013 Bastian Bloessl <bloessl@ccs-labs.org>.
 *
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#include "burst_tagger_impl.h"

#include <gnuradio/io_signature.h>
#include <boost/format.hpp>
#include <cstdio>

namespace gr {
namespace mac {

burst_tagger_impl::burst_tagger_impl(const std::string& tag_name /*= "length"*/, unsigned int mult/* = 1*/, unsigned int pad_front/* = 0*/, unsigned int pad_rear/* = 0*/, bool drop_residue/* = true*/)
		: gr::block("burst_tagger",
			gr::io_signature::make(1, 1, sizeof(gr_complex)),	// FIXME: Custom type
			gr::io_signature::make(1, 1, sizeof(gr_complex)))
		, d_tag_name(pmt::intern(tag_name))
		, d_copy(0)
		, d_mult(mult)
		, d_in_burst(false)
		, d_pad_front(pad_front)
		, d_pad_rear(pad_rear)
		, d_drop_residue(drop_residue)
		, d_to_pad_front(0)
		//, d_to_pad_rear(0)
		, d_current_length(0)
{
	if(!d_mult)
		throw std::out_of_range("multiplier must be > 0");
	
	fprintf(stderr, "<%s[%d]> tag name: %s, multiplier: %d, tag front: %d, tag rear: %d, drop residue: %s\n", name().c_str(), unique_id(), tag_name.c_str(), mult, pad_front, pad_rear, (drop_residue ? "yes" : "no"));
	
	set_relative_rate(1);
	set_tag_propagation_policy(block::TPP_DONT);
}

burst_tagger_impl::~burst_tagger_impl()
{
}

void burst_tagger_impl::add_sob(uint64_t item)
{
	if (d_in_burst)
		fprintf(stderr, "Already in burst!\n");
	static const pmt::pmt_t sob_key = pmt::string_to_symbol("tx_sob");
	static const pmt::pmt_t value = pmt::PMT_T;
	static const pmt::pmt_t srcid = pmt::string_to_symbol(alias());
	add_item_tag(0, item, sob_key, value, srcid);
	d_in_burst = true;
}

void burst_tagger_impl::add_eob(uint64_t item)
{
	if (d_in_burst == false)
		fprintf(stderr, "Not in burst!\n");
	static const pmt::pmt_t eob_key = pmt::string_to_symbol("tx_eob");
	static const pmt::pmt_t value = pmt::PMT_T;
	static const pmt::pmt_t srcid = pmt::string_to_symbol(alias());
	add_item_tag(0, item, eob_key, value, srcid);
	d_in_burst = false;
}

void burst_tagger_impl::forecast (int noutput_items, gr_vector_int &ninput_items_required)
{
	if ((d_to_pad_front) || ((d_pad_rear) && (d_copy > 0) && (d_copy <= d_pad_rear)))
	{
		ninput_items_required[0] = 0;
	}
	else
	{
		ninput_items_required[0] = noutput_items;
	}
}

int burst_tagger_impl::general_work(int noutput_items, gr_vector_int& ninput_items, gr_vector_const_void_star &input_items, gr_vector_void_star &output_items)
{
	const gr_complex *in = (const gr_complex*)input_items[0];
	gr_complex *out = (gr_complex*)output_items[0];

	if (d_copy == 0)
	{
		std::vector<gr::tag_t> tags;
		const uint64_t nread = nitems_read(0);
		
		get_tags_in_range(tags, 0, nread, nread + noutput_items - 1, d_tag_name);
		std::sort(tags.begin(), tags.end(), tag_t::offset_compare);
		
		if (tags.size() > 0)
		{
			tag_t tag = tags.front();
			
			if (tag.offset == nitems_read(0))
			{
				if (d_in_burst)
				{
					fprintf(stderr, "Starting burst when already in one!\n");
				}
				
				d_current_length = pmt::to_uint64(tag.value) * d_mult;
				d_copy = d_current_length + d_pad_rear;
				
				//fprintf(stderr, "Starting %llu items\n", d_copy);
				
				add_sob(nitems_written(0));
				
				if (d_pad_front)
					d_to_pad_front = d_pad_front;
			}
			else	// Copy until the first tag
			{
				uint64_t cpy = std::min((uint64_t)noutput_items, tag.offset - nitems_written(0));
				std::memcpy(out, in, cpy * sizeof(gr_complex));
				
				consume(0, cpy);
				
				if (d_in_burst == false)
				{
					if (d_drop_residue)
					{
						fprintf(stderr, "Dropping %llu items outside burst waiting for tag\n", cpy);
						return 0;
					}
					
					fprintf(stderr, "Copied %llu items outside burst waiting for tag\n", cpy);
				}
				
				return cpy;
			}
		}
		else
		{
			// If no tags, will consume below
		}
	}
	
	if (d_to_pad_front)
	{
		int cpy = std::min((int)d_to_pad_front, noutput_items);
		//fprintf(stderr, "Padding front: %d\n", cpy);
		std::memset(out, 0x00, cpy * sizeof(gr_complex));
		d_to_pad_front -= cpy;
		
		// Nothing consumed
		
		return cpy;	// FIXME: If output buffer space remains, begin copying into that below in same call to work
	}
	
	if (d_copy)
	{
		int cpy = std::min(d_copy, noutput_items);
		
		if ((d_copy > d_pad_rear) && ((d_copy - cpy) < d_pad_rear))
		{
			//fprintf(stderr, ">>> %d,%d - ", d_copy, cpy);
			
			cpy -= (d_pad_rear - (d_copy - cpy));
			
			//fprintf(stderr, "%d\n", cpy);
		}
		
		if (d_copy > d_pad_rear)
		{
			//fprintf(stderr, "Copying: %d (d_copy = %d)\n", cpy, d_copy);
			std::memcpy(out, in, cpy * sizeof(gr_complex));
			consume(0, cpy);
		}
		else
		{
			//fprintf(stderr, "Padding rear: %d (d_copy = %d)\n", cpy, d_copy);
			
			std::memset(out, 0x00, cpy * sizeof(gr_complex));
		}
		
		d_copy -= cpy;
		
		if (d_copy == 0)
		{
			//fprintf(stderr, "EOB\n");
			
			add_eob(nitems_written(0) + cpy - 1);
		}
		
		return cpy;
	}
	else
	{
		consume(0, noutput_items);
		
		if (d_in_burst == false)
		{
			if (d_drop_residue)
			{
				fprintf(stderr, "Copied %d items outside burst waiting for tag\n", noutput_items);
				return 0;
			}
			
			fprintf(stderr, "Copied %lu items outside burst\n", noutput_items);
		}
		
		std::memcpy(out, in, noutput_items * sizeof(gr_complex));
		
		return noutput_items;
	}
}

burst_tagger::sptr burst_tagger::make(const std::string& tag_name /*= "length"*/, unsigned int mult/* = 1*/, unsigned int pad_front/* = 0*/, unsigned int pad_rear/* = 0*/, bool drop_residue/* = true*/)
{
	return gnuradio::get_initial_sptr(new burst_tagger_impl(tag_name, mult, pad_front, pad_rear, drop_residue));
}

} /* namespace mac */
} /* namespace gr */
