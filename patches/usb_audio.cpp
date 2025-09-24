/* Teensyduino Core Library
 * http://www.pjrc.com/teensy/
 * Copyright (c) 2017 PJRC.COM, LLC.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * 1. The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * 2. If the Software is incorporated into a build system that allows
 * selection among a list of target devices, then similar target
 * devices manufactured by PJRC.COM must be included in the list of
 * target devices and selectable in the same manner.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
 * BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
 * ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#include <Arduino.h>
#include "usb_dev.h"
#include "usb_audio.h"
#include "debug/printf.h"

#ifdef AUDIO_INTERFACE

bool AudioInputUSB::update_responsibility;
audio_block_t * AudioInputUSB::incoming_left;
audio_block_t * AudioInputUSB::incoming_right;
audio_block_t * AudioInputUSB::incoming_left2;
audio_block_t * AudioInputUSB::incoming_right2;
audio_block_t * AudioInputUSB::ready_left;
audio_block_t * AudioInputUSB::ready_right;
audio_block_t * AudioInputUSB::ready_left2;
audio_block_t * AudioInputUSB::ready_right2;
uint16_t AudioInputUSB::incoming_count;
uint8_t AudioInputUSB::receive_flag;

struct usb_audio_features_struct AudioInputUSB::features = {0,0,FEATURE_MAX_VOLUME/2};

extern volatile uint8_t usb_high_speed;
static void rx_event(transfer_t *t);
static void tx_event(transfer_t *t);

/*static*/ transfer_t rx_transfer __attribute__ ((used, aligned(32)));
/*static*/ transfer_t sync_transfer __attribute__ ((used, aligned(32)));
/*static*/ transfer_t tx_transfer __attribute__ ((used, aligned(32)));
DMAMEM static uint8_t rx_buffer[AUDIO_RX_SIZE] __attribute__ ((aligned(32)));
DMAMEM static uint8_t tx_buffer[AUDIO_RX_SIZE] __attribute__ ((aligned(32)));
DMAMEM uint32_t usb_audio_sync_feedback __attribute__ ((aligned(32)));

uint8_t usb_audio_receive_setting=0;
uint8_t usb_audio_transmit_setting=0;
uint8_t usb_audio_sync_nbytes;
uint8_t usb_audio_sync_rshift;

uint32_t feedback_accumulator;

volatile uint32_t usb_audio_underrun_count;
volatile uint32_t usb_audio_overrun_count;


static void rx_event(transfer_t *t)
{
	if (t) {
		int len = AUDIO_RX_SIZE - ((rx_transfer.status >> 16) & 0x7FFF);
		printf("rx %u\n", len);
		usb_audio_receive_callback(len);
	}
	usb_prepare_transfer(&rx_transfer, rx_buffer, AUDIO_RX_SIZE, 0);
	arm_dcache_delete(&rx_buffer, AUDIO_RX_SIZE);
	usb_receive(AUDIO_RX_ENDPOINT, &rx_transfer);
}

static void sync_event(transfer_t *t)
{
	// USB 2.0 Specification, 5.12.4.2 Feedback, pages 73-75
	//printf("sync %x\n", sync_transfer.status); // too slow, can't print this much
	usb_audio_sync_feedback = feedback_accumulator >> usb_audio_sync_rshift;
	usb_prepare_transfer(&sync_transfer, &usb_audio_sync_feedback, usb_audio_sync_nbytes, 0);
	arm_dcache_flush(&usb_audio_sync_feedback, usb_audio_sync_nbytes);
	usb_transmit(AUDIO_SYNC_ENDPOINT, &sync_transfer);
}

void usb_audio_configure(void)
{
	printf("usb_audio_configure\n");
	usb_audio_underrun_count = 0;
	usb_audio_overrun_count = 0;
	feedback_accumulator = 739875226; // 44.1 * 2^24
	if (usb_high_speed) {
		usb_audio_sync_nbytes = 4;
		usb_audio_sync_rshift = 8;
	} else {
		usb_audio_sync_nbytes = 3;
		usb_audio_sync_rshift = 10;
	}
	memset(&rx_transfer, 0, sizeof(rx_transfer));
	usb_config_rx_iso(AUDIO_RX_ENDPOINT, AUDIO_RX_SIZE, 1, rx_event);
	rx_event(NULL);
	memset(&sync_transfer, 0, sizeof(sync_transfer));
	usb_config_tx_iso(AUDIO_SYNC_ENDPOINT, usb_audio_sync_nbytes, 1, sync_event);
	sync_event(NULL);
	memset(&tx_transfer, 0, sizeof(tx_transfer));
	usb_config_tx_iso(AUDIO_TX_ENDPOINT, AUDIO_TX_SIZE, 1, tx_event);
	tx_event(NULL);
}

void AudioInputUSB::begin(void)
{
	incoming_count = 0;
	incoming_left = NULL;
	incoming_right = NULL;
	incoming_left2 = NULL;
	incoming_right2 = NULL;
	ready_left = NULL;
	ready_right = NULL;
	ready_left2 = NULL;
	ready_right2 = NULL;
	receive_flag = 0;
	// update_responsibility = update_setup();
	// TODO: update responsibility is tough, partly because the USB
	// interrupts aren't sychronous to the audio library block size,
	// but also because the PC may stop transmitting data, which
	// means we no longer get receive callbacks from usb.c
	update_responsibility = false;
}

static void copy_to_buffers_4ch(const uint32_t *src, int16_t *left1, int16_t *right1,
                                 int16_t *left2, int16_t *right2, unsigned int len)
{
	// 4-channel data format: L1, R1, L2, R2 (16-bit each)
	// Two 32-bit words contain all 4 channels
	while (len > 0) {
		uint32_t n1 = *src++;  // L1, R1
		uint32_t n2 = *src++;  // L2, R2
		*left1++ = n1 & 0xFFFF;
		*right1++ = n1 >> 16;
		*left2++ = n2 & 0xFFFF;
		*right2++ = n2 >> 16;
		len--;
	}
}

// Called from the USB interrupt when an isochronous packet arrives
// we must completely remove it from the receive buffer before returning
//
#if 1
void usb_audio_receive_callback(unsigned int len)
{
	unsigned int count, avail;
	audio_block_t *left1, *right1, *left2, *right2;
	const uint32_t *data;

	AudioInputUSB::receive_flag = 1;
	len >>= 3; // 1 sample = 8 bytes: 4 channels x 2 bytes each
	data = (const uint32_t *)rx_buffer;

	count = AudioInputUSB::incoming_count;
	left1 = AudioInputUSB::incoming_left;
	right1 = AudioInputUSB::incoming_right;
	left2 = AudioInputUSB::incoming_left2;
	right2 = AudioInputUSB::incoming_right2;

	if (left1 == NULL) {
		left1 = AudioStream::allocate();
		if (left1 == NULL) return;
		AudioInputUSB::incoming_left = left1;
	}
	if (right1 == NULL) {
		right1 = AudioStream::allocate();
		if (right1 == NULL) return;
		AudioInputUSB::incoming_right = right1;
	}
	if (left2 == NULL) {
		left2 = AudioStream::allocate();
		if (left2 == NULL) return;
		AudioInputUSB::incoming_left2 = left2;
	}
	if (right2 == NULL) {
		right2 = AudioStream::allocate();
		if (right2 == NULL) return;
		AudioInputUSB::incoming_right2 = right2;
	}

	while (len > 0) {
		avail = AUDIO_BLOCK_SAMPLES - count;
		if (len < avail) {
			copy_to_buffers_4ch(data, left1->data + count, right1->data + count,
			                    left2->data + count, right2->data + count, len);
			AudioInputUSB::incoming_count = count + len;
			return;
		} else if (avail > 0) {
			copy_to_buffers_4ch(data, left1->data + count, right1->data + count,
			                    left2->data + count, right2->data + count, avail);
			data += avail * 2;  // 2 words per sample for 4 channels
			len -= avail;
			if (AudioInputUSB::ready_left || AudioInputUSB::ready_right ||
			    AudioInputUSB::ready_left2 || AudioInputUSB::ready_right2) {
				// buffer overrun, PC sending too fast
				AudioInputUSB::incoming_count = count + avail;
				if (len > 0) {
					usb_audio_overrun_count++;
					printf("!");
				}
				return;
			}
			send:
			AudioInputUSB::ready_left = left1;
			AudioInputUSB::ready_right = right1;
			AudioInputUSB::ready_left2 = left2;
			AudioInputUSB::ready_right2 = right2;

			left1 = AudioStream::allocate();
			if (left1 == NULL) {
				AudioInputUSB::incoming_left = NULL;
				AudioInputUSB::incoming_right = NULL;
				AudioInputUSB::incoming_left2 = NULL;
				AudioInputUSB::incoming_right2 = NULL;
				AudioInputUSB::incoming_count = 0;
				return;
			}
			right1 = AudioStream::allocate();
			if (right1 == NULL) {
				AudioStream::release(left1);
				AudioInputUSB::incoming_left = NULL;
				AudioInputUSB::incoming_right = NULL;
				AudioInputUSB::incoming_left2 = NULL;
				AudioInputUSB::incoming_right2 = NULL;
				AudioInputUSB::incoming_count = 0;
				return;
			}
			left2 = AudioStream::allocate();
			if (left2 == NULL) {
				AudioStream::release(left1);
				AudioStream::release(right1);
				AudioInputUSB::incoming_left = NULL;
				AudioInputUSB::incoming_right = NULL;
				AudioInputUSB::incoming_left2 = NULL;
				AudioInputUSB::incoming_right2 = NULL;
				AudioInputUSB::incoming_count = 0;
				return;
			}
			right2 = AudioStream::allocate();
			if (right2 == NULL) {
				AudioStream::release(left1);
				AudioStream::release(right1);
				AudioStream::release(left2);
				AudioInputUSB::incoming_left = NULL;
				AudioInputUSB::incoming_right = NULL;
				AudioInputUSB::incoming_left2 = NULL;
				AudioInputUSB::incoming_right2 = NULL;
				AudioInputUSB::incoming_count = 0;
				return;
			}
			AudioInputUSB::incoming_left = left1;
			AudioInputUSB::incoming_right = right1;
			AudioInputUSB::incoming_left2 = left2;
			AudioInputUSB::incoming_right2 = right2;
			count = 0;
		} else {
			if (AudioInputUSB::ready_left || AudioInputUSB::ready_right ||
			    AudioInputUSB::ready_left2 || AudioInputUSB::ready_right2) return;
			goto send; // recover from buffer overrun
		}
	}
	AudioInputUSB::incoming_count = count;
}
#endif

void AudioInputUSB::update(void)
{
	audio_block_t *left1, *right1, *left2, *right2;

	__disable_irq();
	left1 = ready_left;
	ready_left = NULL;
	right1 = ready_right;
	ready_right = NULL;
	left2 = ready_left2;
	ready_left2 = NULL;
	right2 = ready_right2;
	ready_right2 = NULL;
	uint16_t c = incoming_count;
	uint8_t f = receive_flag;
	receive_flag = 0;
	__enable_irq();
	if (f) {
		int diff = AUDIO_BLOCK_SAMPLES/2 - (int)c;
		feedback_accumulator += diff * 1;
		//uint32_t feedback = (feedback_accumulator >> 8) + diff * 100;
		//usb_audio_sync_feedback = feedback;

		//printf(diff >= 0 ? "." : "^");
	}
	//serial_phex(c);
	//serial_print(".");
	if (!left1 || !right1 || !left2 || !right2) {
		usb_audio_underrun_count++;
		//printf("#"); // buffer underrun - PC sending too slow
		if (f) feedback_accumulator += 3500;
	}
	if (left1) {
		transmit(left1, 0);  // Channel 0 - Left 1
		release(left1);
	}
	if (right1) {
		transmit(right1, 1); // Channel 1 - Right 1
		release(right1);
	}
	if (left2) {
		transmit(left2, 2);  // Channel 2 - Left 2
		release(left2);
	}
	if (right2) {
		transmit(right2, 3); // Channel 3 - Right 2
		release(right2);
	}
}

















#if 1
bool AudioOutputUSB::update_responsibility;
audio_block_t * AudioOutputUSB::left_1st;
audio_block_t * AudioOutputUSB::left_2nd;
audio_block_t * AudioOutputUSB::right_1st;
audio_block_t * AudioOutputUSB::right_2nd;
audio_block_t * AudioOutputUSB::left2_1st;
audio_block_t * AudioOutputUSB::left2_2nd;
audio_block_t * AudioOutputUSB::right2_1st;
audio_block_t * AudioOutputUSB::right2_2nd;
uint16_t AudioOutputUSB::offset_1st;

/*DMAMEM*/ uint16_t usb_audio_transmit_buffer[AUDIO_TX_SIZE/2] __attribute__ ((used, aligned(32)));


static void tx_event(transfer_t *t)
{
	int len = usb_audio_transmit_callback();
	usb_audio_sync_feedback = feedback_accumulator >> usb_audio_sync_rshift;
	usb_prepare_transfer(&tx_transfer, usb_audio_transmit_buffer, len, 0);
	arm_dcache_flush_delete(usb_audio_transmit_buffer, len);
	usb_transmit(AUDIO_TX_ENDPOINT, &tx_transfer);
}


void AudioOutputUSB::begin(void)
{
	update_responsibility = false;
	left_1st = NULL;
	right_1st = NULL;
	left2_1st = NULL;
	right2_1st = NULL;
	left_2nd = NULL;
	right_2nd = NULL;
	left2_2nd = NULL;
	right2_2nd = NULL;
	offset_1st = 0;
}

static void copy_from_buffers_4ch(uint32_t *dst, int16_t *left1, int16_t *right1,
                                   int16_t *left2, int16_t *right2, unsigned int len)
{
	// Pack 4 channels: L1, R1, L2, R2
	while (len > 0) {
		*dst++ = (*right1++ << 16) | (*left1++ & 0xFFFF);  // L1, R1
		*dst++ = (*right2++ << 16) | (*left2++ & 0xFFFF);  // L2, R2
		len--;
	}
}

void AudioOutputUSB::update(void)
{
	audio_block_t *left1, *right1, *left2, *right2;

	// Get audio from all 4 input channels
	left1 = receiveWritable(0);  // input 0 = channel 1 (L1)
	right1 = receiveWritable(1); // input 1 = channel 2 (R1)
	left2 = receiveWritable(2);  // input 2 = channel 3 (L2)
	right2 = receiveWritable(3); // input 3 = channel 4 (R2)

	if (usb_audio_transmit_setting == 0) {
		if (left1) release(left1);
		if (right1) release(right1);
		if (left2) release(left2);
		if (right2) release(right2);
		if (left_1st) { release(left_1st); left_1st = NULL; }
		if (left_2nd) { release(left_2nd); left_2nd = NULL; }
		if (right_1st) { release(right_1st); right_1st = NULL; }
		if (right_2nd) { release(right_2nd); right_2nd = NULL; }
		if (left2_1st) { release(left2_1st); left2_1st = NULL; }
		if (left2_2nd) { release(left2_2nd); left2_2nd = NULL; }
		if (right2_1st) { release(right2_1st); right2_1st = NULL; }
		if (right2_2nd) { release(right2_2nd); right2_2nd = NULL; }
		offset_1st = 0;
		return;
	}

	// Create silence for any missing channel
	if (left1 == NULL) {
		left1 = allocate();
		if (left1) memset(left1->data, 0, sizeof(left1->data));
	}
	if (right1 == NULL) {
		right1 = allocate();
		if (right1) memset(right1->data, 0, sizeof(right1->data));
	}
	if (left2 == NULL) {
		left2 = allocate();
		if (left2) memset(left2->data, 0, sizeof(left2->data));
	}
	if (right2 == NULL) {
		right2 = allocate();
		if (right2) memset(right2->data, 0, sizeof(right2->data));
	}

	// If any allocation failed, release all and return
	if (!left1 || !right1 || !left2 || !right2) {
		if (left1) release(left1);
		if (right1) release(right1);
		if (left2) release(left2);
		if (right2) release(right2);
		return;
	}

	__disable_irq();
	if (left_1st == NULL) {
		left_1st = left1;
		right_1st = right1;
		left2_1st = left2;
		right2_1st = right2;
		offset_1st = 0;
	} else if (left_2nd == NULL) {
		left_2nd = left1;
		right_2nd = right1;
		left2_2nd = left2;
		right2_2nd = right2;
	} else {
		// buffer overrun - PC is consuming too slowly
		audio_block_t *discard1 = left_1st;
		audio_block_t *discard2 = right_1st;
		audio_block_t *discard3 = left2_1st;
		audio_block_t *discard4 = right2_1st;
		left_1st = left_2nd;
		right_1st = right_2nd;
		left2_1st = left2_2nd;
		right2_1st = right2_2nd;
		left_2nd = left1;
		right_2nd = right1;
		left2_2nd = left2;
		right2_2nd = right2;
		offset_1st = 0;
		release(discard1);
		release(discard2);
		release(discard3);
		release(discard4);
	}
	__enable_irq();
}


// Called from the USB interrupt when ready to transmit another
// isochronous packet.  If we place data into the transmit buffer,
// the return is the number of bytes.  Otherwise, return 0 means
// no data to transmit
unsigned int usb_audio_transmit_callback(void)
{
	static uint32_t count=5;
	uint32_t avail, num, target, offset, len=0;
	audio_block_t *left1, *right1, *left2, *right2;

	if (++count < 10) {   // TODO: dynamic adjust to match USB rate
		target = 44;
	} else {
		count = 0;
		target = 45;
	}
	while (len < target) {
		num = target - len;
		left1 = AudioOutputUSB::left_1st;
		if (left1 == NULL) {
			// buffer underrun - PC is consuming too quickly
			memset(usb_audio_transmit_buffer + len*2, 0, num * 8);  // 4 channels * 2 bytes
			break;
		}
		right1 = AudioOutputUSB::right_1st;
		left2 = AudioOutputUSB::left2_1st;
		right2 = AudioOutputUSB::right2_1st;
		offset = AudioOutputUSB::offset_1st;

		avail = AUDIO_BLOCK_SAMPLES - offset;
		if (num > avail) num = avail;

		copy_from_buffers_4ch((uint32_t *)usb_audio_transmit_buffer + len*2,
			left1->data + offset, right1->data + offset,
			left2->data + offset, right2->data + offset, num);
		len += num;
		offset += num;
		if (offset >= AUDIO_BLOCK_SAMPLES) {
			AudioStream::release(left1);
			AudioStream::release(right1);
			AudioStream::release(left2);
			AudioStream::release(right2);
			AudioOutputUSB::left_1st = AudioOutputUSB::left_2nd;
			AudioOutputUSB::left_2nd = NULL;
			AudioOutputUSB::right_1st = AudioOutputUSB::right_2nd;
			AudioOutputUSB::right_2nd = NULL;
			AudioOutputUSB::left2_1st = AudioOutputUSB::left2_2nd;
			AudioOutputUSB::left2_2nd = NULL;
			AudioOutputUSB::right2_1st = AudioOutputUSB::right2_2nd;
			AudioOutputUSB::right2_2nd = NULL;
			AudioOutputUSB::offset_1st = 0;
		} else {
			AudioOutputUSB::offset_1st = offset;
		}
	}
	return target * 8;  // 4 channels * 2 bytes per sample
}
#endif




struct setup_struct {
  union {
    struct {
	uint8_t bmRequestType;
	uint8_t bRequest;
	union {
		struct {
			uint8_t bChannel;  // 0=main, 1=left, 2=right
			uint8_t bCS;       // Control Selector
		};
		uint16_t wValue;
	};
	union {
		struct {
			uint8_t bIfEp;     // type of entity
			uint8_t bEntityId; // UnitID, TerminalID, etc.
		};
		uint16_t wIndex;
	};
	uint16_t wLength;
    };
  };
};

int usb_audio_get_feature(void *stp, uint8_t *data, uint32_t *datalen)
{
	struct setup_struct setup = *((struct setup_struct *)stp);
	if (setup.bmRequestType==0xA1) { // should check bRequest, bChannel, and UnitID
			if (setup.bCS==0x01) { // mute
				data[0] = AudioInputUSB::features.mute;  // 1=mute, 0=unmute
				*datalen = 1;
				return 1;
			}
			else if (setup.bCS==0x02) { // volume
				if (setup.bRequest==0x81) { // GET_CURR
					data[0] = AudioInputUSB::features.volume & 0xFF;
					data[1] = (AudioInputUSB::features.volume>>8) & 0xFF;
				}
				else if (setup.bRequest==0x82) { // GET_MIN
					//serial_print("vol get_min\n");
					data[0] = 0;     // min level is 0
					data[1] = 0;
				}
				else if (setup.bRequest==0x83) { // GET_MAX
					data[0] = FEATURE_MAX_VOLUME;  // max level, for range of 0 to MAX
					data[1] = 0;
				}
				else if (setup.bRequest==0x84) { // GET_RES
					data[0] = 1; // increment vol by by 1
					data[1] = 0;
				}
				else { // pass over SET_MEM, etc.
					return 0;
				}
				*datalen = 2;
				return 1;
			}
	}
	return 0;
}

int usb_audio_set_feature(void *stp, uint8_t *buf) 
{
	struct setup_struct setup = *((struct setup_struct *)stp);
	if (setup.bmRequestType==0x21) { // should check bRequest, bChannel and UnitID
			if (setup.bCS==0x01) { // mute
				if (setup.bRequest==0x01) { // SET_CUR
					AudioInputUSB::features.mute = buf[0]; // 1=mute,0=unmute
					AudioInputUSB::features.change = 1;
					return 1;
				}
			}
			else if (setup.bCS==0x02) { // volume
				if (setup.bRequest==0x01) { // SET_CUR
					AudioInputUSB::features.volume = buf[0];
					AudioInputUSB::features.change = 1;
					return 1;
				}
			}
	}
	return 0;
}


#endif // AUDIO_INTERFACE
