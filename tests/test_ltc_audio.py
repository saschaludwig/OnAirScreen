#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for ltc_audio.py (synthetic biphase LTC, no hardware).
"""

import numpy as np

from ltc_audio import (
    SYNC_WORD,
    LtcDecodeState,
    _hunt_phase,
    _reset_pll,
    encode_ltc_bits,
    parse_ltc_frame_bits,
    parse_ltc_samples,
    synthesize_ltc_audio,
)


def _decode_with_phase_hunt(audio, sample_rate=48000, hunt_every=5760):
    """Decode in capture-sized blocks; flip phase / reset PLL after ~120 ms without a frame."""
    state = LtcDecodeState()
    found = []
    silent = 0
    hunts = 0
    block = 1024
    for start in range(0, len(audio), block):
        state, frames = parse_ltc_samples(audio[start:start + block], sample_rate, state)
        found.extend(frames)
        if frames:
            silent = 0
            hunts = 0
        else:
            silent += min(block, len(audio) - start)
            if silent >= hunt_every and state.half_bit > 0.0:
                hunts += 1
                if hunts % 3 == 0:
                    _reset_pll(state)
                    state.prev_sign = 0
                    state.interval = 0
                else:
                    _hunt_phase(state)
                silent = 0
    return found


class TestEncodeLtcBits:
    def test_sync_word_at_end(self):
        bits = encode_ltc_bits(1, 2, 3, 4)
        assert len(bits) == 80
        assert bits[-16:] == SYNC_WORD

    def test_round_trip_parse_bits(self):
        bits = encode_ltc_bits(12, 34, 56, 10)
        frame = parse_ltc_frame_bits(bits)
        assert frame is not None
        assert frame.hours == 12
        assert frame.minutes == 34
        assert frame.seconds == 56
        assert frame.frames == 10

    def test_invalid_bcd_rejected(self):
        bits = list(encode_ltc_bits(0, 0, 0, 0))
        # Minutes tens = 6 → 60 minutes, which is invalid.
        bits[40] = 0
        bits[41] = 1
        bits[42] = 1
        assert parse_ltc_frame_bits(bits) is None


class TestParseLtcSamples:
    def test_25_fps_waveform(self):
        audio = synthesize_ltc_audio(1, 2, 3, 4, fps=25, sample_rate=48000, frame_count=5)
        _state, frames = parse_ltc_samples(audio, 48000)
        assert len(frames) >= 3
        assert frames[0].hours == 1
        assert frames[0].minutes == 2
        assert frames[0].seconds == 3
        assert frames[0].frames == 4
        assert frames[1].frames == 5

    def test_30_fps_waveform(self):
        audio = synthesize_ltc_audio(0, 0, 0, 0, fps=30, sample_rate=48000, frame_count=4)
        _state, frames = parse_ltc_samples(audio, 48000)
        assert len(frames) >= 2
        assert frames[0].hours == 0
        assert frames[0].frames == 0
        assert {frame.frames for frame in frames} <= {0, 1, 2, 3}

    def test_sync_in_the_middle_of_stream(self):
        audio = synthesize_ltc_audio(9, 8, 7, 6, fps=25, sample_rate=48000, frame_count=3)
        prefix = np.zeros(700, dtype=np.float32)
        _state, frames = parse_ltc_samples(np.concatenate([prefix, audio]), 48000)
        assert len(frames) >= 1
        assert frames[0].hours == 9
        assert frames[0].frames == 6

    def test_silence_yields_no_frames(self):
        silence = np.zeros(48000, dtype=np.float32)
        _state, frames = parse_ltc_samples(silence, 48000)
        assert frames == []

    def test_state_persists_across_blocks(self):
        audio = synthesize_ltc_audio(0, 0, 1, 0, fps=25, sample_rate=48000, frame_count=3)
        mid = len(audio) // 2
        state, first = parse_ltc_samples(audio[:mid], 48000)
        state, second = parse_ltc_samples(audio[mid:], 48000, state)
        assert len(first) + len(second) >= 2

    def test_recovers_after_silence_in_one_block(self):
        first = synthesize_ltc_audio(1, 0, 0, 0, fps=25, sample_rate=48000, frame_count=3)
        silence = np.zeros(4800, dtype=np.float32)
        second = synthesize_ltc_audio(2, 0, 0, 0, fps=25, sample_rate=48000, frame_count=3)
        _state, frames = parse_ltc_samples(np.concatenate([first, silence, second]), 48000)
        hours = {frame.hours for frame in frames}
        assert 1 in hours
        assert 2 in hours

    def test_recovers_after_silence_across_blocks(self):
        first = synthesize_ltc_audio(1, 0, 0, 0, fps=25, sample_rate=48000, frame_count=3)
        second = synthesize_ltc_audio(2, 0, 0, 0, fps=25, sample_rate=48000, frame_count=3)
        state, before = parse_ltc_samples(first, 48000)
        state, during = parse_ltc_samples(np.zeros(4800, dtype=np.float32), 48000, state)
        state, after = parse_ltc_samples(second, 48000, state)
        assert during == []
        assert any(frame.hours == 1 for frame in before)
        assert any(frame.hours == 2 for frame in after)

    def test_recovers_from_inflated_half_bit(self):
        audio = synthesize_ltc_audio(0, 0, 5, 0, fps=25, sample_rate=48000, frame_count=4)
        stale = LtcDecodeState(
            half_bit=200.0,
            pending_half=True,
            prev_sign=1,
            bits=[1] * 40,
            interval=50,
        )
        _state, frames = parse_ltc_samples(audio, 48000, stale)
        assert len(frames) >= 1
        assert frames[0].seconds == 5

    def test_locks_when_starting_mid_bit(self):
        audio = synthesize_ltc_audio(3, 4, 5, 6, fps=25, sample_rate=48000, frame_count=8)
        frames = _decode_with_phase_hunt(audio[12:])
        assert len(frames) >= 2
        assert any(frame.hours == 3 and frame.minutes == 4 for frame in frames)

    def test_locks_after_hard_cut_to_new_phase(self):
        first = synthesize_ltc_audio(1, 0, 0, 0, fps=25, sample_rate=48000, frame_count=3)
        second = synthesize_ltc_audio(9, 0, 0, 0, fps=25, sample_rate=48000, frame_count=8)
        frames = _decode_with_phase_hunt(np.concatenate([first, second[12:]]))
        hours = {frame.hours for frame in frames}
        assert 1 in hours
        assert 9 in hours

    def test_inverted_polarity_still_decodes(self):
        audio = synthesize_ltc_audio(0, 1, 2, 3, fps=25, sample_rate=48000, frame_count=4)
        _state, frames = parse_ltc_samples(-audio, 48000)
        assert len(frames) >= 2
        assert frames[0].minutes == 1
        assert frames[0].seconds == 2

    def test_low_amplitude_still_decodes(self):
        audio = synthesize_ltc_audio(4, 5, 6, 7, fps=25, sample_rate=48000, frame_count=5, amplitude=0.05)
        _state, frames = parse_ltc_samples(audio, 48000)
        assert len(frames) >= 1
        assert any(frame.hours == 4 and frame.minutes == 5 for frame in frames)

    def test_dc_offset_still_decodes(self):
        audio = synthesize_ltc_audio(8, 0, 0, 1, fps=25, sample_rate=48000, frame_count=4, amplitude=0.5)
        audio = audio + 0.2
        _state, frames = parse_ltc_samples(audio, 48000)
        assert len(frames) >= 2
        assert frames[0].hours == 8


class TestLtcAudioReader:
    def test_channel_and_kind(self):
        import sys

        from PySide6.QtWidgets import QApplication

        from ltc_audio import LtcAudioReader

        if not QApplication.instance():
            QApplication(sys.argv)
        reader = LtcAudioReader(device_name="Mic", channel=2)
        assert reader.device_name == "Mic"
        assert reader.channel == 1
        assert reader.input_kind == "audio"
        assert reader.is_running is False
