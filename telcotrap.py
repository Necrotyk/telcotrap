#!/usr/bin/env python3
"""
telcotrap.py - Telephony Trap & Anti-Robocall Audio Synthesis Engine

Zero-dependency Python toolkit generating telecom supervisory signaling,
machine handshakes, and DSP/AI countermeasures designed to disrupt predictive
dialers, Answering Machine Detection (AMD) systems, and conversational AI voice bots.

Standards:
- Output: 8000 Hz, 16-bit PCM Mono WAV (PSTN/VoIP standard)
- Telcordia GR-506-CORE / ITU-T E.180 / BT SIN 350 / T.30 / ITU-T V.25 compliance
- 5ms cosine window envelopes for click and spectral splatter elimination
- Pure Python standard library (no third-party dependencies)
"""

import argparse
import json
import math
import os
import pathlib
import random
import struct
import sys
import wave

SAMPLE_RATE = 8000
BITS_PER_SAMPLE = 16
NUM_CHANNELS = 1

# Telcordia GR-506-CORE calibrated transmission levels (dBFS)
LEVEL_SINGLE_TONE = -12.0
LEVEL_FAX_CNG = -11.0
LEVEL_CED = -12.0
LEVEL_SUPERVISORY = -12.0
LEVEL_DTMF_LOW = -15.0
LEVEL_DTMF_HIGH = -13.0  # +2.0 dB forward twist
LEVEL_PINK_BURST = -22.0
LEVEL_COMFORT_NOISE = -45.0


def dbfs_to_linear(dbfs: float, max_val: float = 32767.0) -> float:
    """Convert decibels relative to full scale (dBFS) to linear amplitude."""
    return max_val * (10.0 ** (dbfs / 20.0))


def clamp16(sample: float) -> int:
    """Strictly clamp sample value to signed 16-bit PCM integer range."""
    val = int(round(sample))
    if val > 32767:
        return 32767
    elif val < -32768:
        return -32768
    return val


def apply_cosine_envelope(samples: list, fade_ms: float = 5.0, sample_rate: int = SAMPLE_RATE) -> list:
    """
    Apply a cosine fade-in and fade-out envelope to eliminate spectral splatter
    and click artifacts on tone onset and termination.
    w(i) = 0.5 * (1 - cos(pi * i / N))
    """
    length = len(samples)
    if length == 0:
        return samples

    fade_samples = int(round((fade_ms / 1000.0) * sample_rate))
    # Adaptively clamp envelope length if segment is very short
    fade_samples = max(1, min(fade_samples, length // 2))

    for i in range(fade_samples):
        # 0.5 * (1 - cos(pi * i / N)) ranges smoothly from 0.0 to 1.0
        factor = 0.5 * (1.0 - math.cos(math.pi * i / fade_samples))
        samples[i] *= factor
        samples[length - 1 - i] *= factor

    return samples


class BiquadFilter:
    """
    Direct Form II Transposed 2nd-order Biquad IIR Filter.
    Supports low-pass and band-pass filtering with bilinear transform pre-warping.
    Numerically stable in pure standard-library double-precision Python.
    """

    def __init__(self, filter_type: str, fc: float, fs: float, q: float = 0.70710678):
        self.s1 = 0.0
        self.s2 = 0.0
        omega = 2.0 * math.pi * fc / fs
        alpha = math.sin(omega) / (2.0 * q)
        cos_w = math.cos(omega)

        if filter_type == "lpf":
            b0 = (1.0 - cos_w) / 2.0
            b1 = 1.0 - cos_w
            b2 = (1.0 - cos_w) / 2.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w
            a2 = 1.0 - alpha
        elif filter_type == "bpf":
            b0 = alpha
            b1 = 0.0
            b2 = -alpha
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w
            a2 = 1.0 - alpha
        else:
            raise ValueError(f"Unsupported filter type: {filter_type}")

        self.b0 = b0 / a0
        self.b1 = b1 / a0
        self.b2 = b2 / a0
        self.a1 = a1 / a0
        self.a2 = a2 / a0

    def process_sample(self, x: float) -> float:
        y = self.b0 * x + self.s1
        self.s1 = self.b1 * x - self.a1 * y + self.s2
        self.s2 = self.b2 * x - self.a2 * y
        return y

    def process(self, samples: list) -> list:
        return [self.process_sample(x) for x in samples]


class KelletPinkNoise:
    """
    Paul Kellet's 3-pole IIR pink noise generator.
    Produces an exact -3 dB/octave spectral slope from white Gaussian input.
    """

    def __init__(self):
        self.b0 = 0.0
        self.b1 = 0.0
        self.b2 = 0.0
        self.b3 = 0.0
        self.b4 = 0.0
        self.b5 = 0.0
        self.b6 = 0.0

    def generate(self, count: int) -> list:
        output = []
        for _ in range(count):
            white = random.gauss(0.0, 1.0)
            self.b0 = 0.99886 * self.b0 + white * 0.0555179
            self.b1 = 0.99332 * self.b1 + white * 0.0750759
            self.b2 = 0.96900 * self.b2 + white * 0.1538520
            self.b3 = 0.86650 * self.b3 + white * 0.3104856
            self.b4 = 0.55000 * self.b4 + white * 0.5329522
            self.b5 = -0.76160 * self.b5 - white * 0.0168980
            pink = self.b0 + self.b1 + self.b2 + self.b3 + self.b4 + self.b5 + self.b6 + white * 0.5362
            self.b6 = white * 0.115926
            output.append(pink)
        return output


# -------------------------------------------------------------------------
# Core Synthesizer Functions
# -------------------------------------------------------------------------

def generate_tone(freq: float, duration_ms: float, dbfs: float = LEVEL_SINGLE_TONE,
                  phase_in: float = 0.0, envelope: bool = True) -> tuple:
    """Synthesize a continuous sine wave tone with optional 5ms cosine envelope."""
    amp = dbfs_to_linear(dbfs)
    count = int(round((duration_ms / 1000.0) * SAMPLE_RATE))
    phase = phase_in
    phase_step = 2.0 * math.pi * freq / SAMPLE_RATE

    samples = []
    for _ in range(count):
        samples.append(amp * math.sin(phase))
        phase = (phase + phase_step) % (2.0 * math.pi)

    if envelope:
        samples = apply_cosine_envelope(samples, fade_ms=5.0)

    return samples, phase


def generate_silence(duration_ms: float) -> list:
    """Generate pure digital silence of specified duration."""
    count = int(round((duration_ms / 1000.0) * SAMPLE_RATE))
    return [0.0] * count


def generate_dual_tone(freq1: float, freq2: float, duration_ms: float,
                       dbfs1: float = LEVEL_DTMF_LOW, dbfs2: float = LEVEL_DTMF_HIGH,
                       envelope: bool = True) -> list:
    """Synthesize a dual-frequency tone with individual level control."""
    amp1 = dbfs_to_linear(dbfs1)
    amp2 = dbfs_to_linear(dbfs2)
    count = int(round((duration_ms / 1000.0) * SAMPLE_RATE))
    step1 = 2.0 * math.pi * freq1 / SAMPLE_RATE
    step2 = 2.0 * math.pi * freq2 / SAMPLE_RATE

    samples = []
    for i in range(count):
        s = amp1 * math.sin(step1 * i) + amp2 * math.sin(step2 * i)
        samples.append(s)

    if envelope:
        samples = apply_cosine_envelope(samples, fade_ms=5.0)

    return samples


def generate_comfort_noise(duration_ms: float, dbfs: float = LEVEL_COMFORT_NOISE) -> list:
    """
    Generate band-limited (300-3000 Hz) pseudo-Gaussian comfort noise
    to simulate an active analog/VoIP PSTN line without digital zero-silence drops.
    """
    count = int(round((duration_ms / 1000.0) * SAMPLE_RATE))
    if count == 0:
        return []

    # 300-3000 Hz bandpass filter: center freq ~948 Hz, Q ~ 0.351
    bpf = BiquadFilter("bpf", fc=948.68, fs=SAMPLE_RATE, q=0.351)
    raw = [random.gauss(0.0, 1.0) for _ in range(count)]
    filtered = bpf.process(raw)

    # Scale to target RMS dBFS
    rms = math.sqrt(sum(x * x for x in filtered) / count) if count > 0 else 1.0
    if rms < 1e-6:
        rms = 1e-6
    target_amp = dbfs_to_linear(dbfs)
    scale = target_amp / rms

    return [x * scale for x in filtered]


# -------------------------------------------------------------------------
# Signaling Profiles (PSTN Standards)
# -------------------------------------------------------------------------

def gen_sit_sequence(tones: list) -> list:
    """
    Helper to synthesize standard 3-tone Special Information Tone sequences.
    tones format: [(freq, duration_ms), ...]
    """
    seq = []
    for freq, duration in tones:
        burst, _ = generate_tone(freq, duration, dbfs=LEVEL_SINGLE_TONE, envelope=True)
        seq.extend(burst)
    return seq


def sig_na_nanp_ic() -> list:
    """North American Bellcore/Telcordia Intercept SIT: 913.8Hz, 1370.6Hz, 1776.7Hz."""
    return gen_sit_sequence([(913.8, 276.0), (1370.6, 276.0), (1776.7, 380.0)])


def sig_na_nanp_nc() -> list:
    """North American Bellcore/Telcordia No Circuit SIT: 985.2Hz, 1370.6Hz, 1776.7Hz."""
    return gen_sit_sequence([(985.2, 380.0), (1370.6, 276.0), (1776.7, 380.0)])


def sig_na_nanp_vacant() -> list:
    """North American Bellcore/Telcordia Vacant Code SIT: 985.2Hz, 1428.5Hz, 1776.7Hz."""
    return gen_sit_sequence([(985.2, 276.0), (1428.5, 380.0), (1776.7, 380.0)])


def sig_itu_e180_sit() -> list:
    """Global ITU-T E.180 Standard SIT: 950Hz, 1400Hz, 1800Hz with 30ms gaps."""
    seq = []
    for freq in [950.0, 1400.0, 1800.0]:
        burst, _ = generate_tone(freq, 330.0, dbfs=LEVEL_SINGLE_TONE, envelope=True)
        seq.extend(burst)
        seq.extend(generate_silence(30.0))
    return seq


def sig_uk_bt_sit() -> list:
    """United Kingdom BT SIN 350 SIT: 950Hz, 1400Hz, 1800Hz followed by 1000ms silence."""
    seq = []
    for freq in [950.0, 1400.0, 1800.0]:
        burst, _ = generate_tone(freq, 330.0, dbfs=LEVEL_SINGLE_TONE, envelope=True)
        seq.extend(burst)
    seq.extend(generate_silence(1000.0))
    return seq


def sig_uk_bt_nu() -> list:
    """United Kingdom BT Number Unobtainable: Continuous 400.0 Hz tone (2500ms)."""
    samples, _ = generate_tone(400.0, 2500.0, dbfs=LEVEL_SUPERVISORY, envelope=True)
    return samples


def sig_eu_etsi_congestion() -> list:
    """EU/ETSI Fast Busy / Congestion: 425.0 Hz alternating 250ms ON / 250ms OFF (6 cycles)."""
    seq = []
    for _ in range(6):
        burst, _ = generate_tone(425.0, 250.0, dbfs=LEVEL_SUPERVISORY, envelope=True)
        seq.extend(burst)
        seq.extend(generate_silence(250.0))
    return seq


def sig_jp_ntt_busy() -> list:
    """Japan NTT Howler / Busy Tone: 400.0 Hz alternating 500ms ON / 500ms OFF (3 cycles)."""
    seq = []
    for _ in range(3):
        burst, _ = generate_tone(400.0, 500.0, dbfs=LEVEL_SUPERVISORY, envelope=True)
        seq.extend(burst)
        seq.extend(generate_silence(500.0))
    return seq


# -------------------------------------------------------------------------
# Advanced Countermeasures (Fax, V.25, FSK, AMD, VAD, DTMF)
# -------------------------------------------------------------------------

def mod_fax_cng() -> list:
    """
    T.30 Fax Calling Tone (CNG): 1100.0 Hz tone (500ms ON, 3000ms OFF).
    Causes enterprise dialers (Asterisk, Vicidial, Genesys) to tag line as fax and scrub.
    """
    burst, _ = generate_tone(1100.0, 500.0, dbfs=LEVEL_FAX_CNG, envelope=True)
    silence = generate_silence(3000.0)
    return burst + silence


def mod_modem_ced() -> list:
    """
    ITU-T V.25 Answer Tone (CED) with Echo Canceller Disabler:
    2100.0 Hz continuous tone (3000ms) with 180-degree phase reversals every 450ms.
    Reversals occur strictly at zero crossings with 8-sample micro-crossfade.
    """
    total_samples = int(round((3000.0 / 1000.0) * SAMPLE_RATE))  # 24,000 samples
    amp = dbfs_to_linear(LEVEL_CED)
    step = 2.0 * math.pi * 2100.0 / SAMPLE_RATE

    samples = []
    phase = 0.0
    invert_stride = int(round((450.0 / 1000.0) * SAMPLE_RATE))  # 3600 samples
    next_invert_sample = invert_stride
    inverting = False

    for n in range(total_samples):
        # Trigger inversion near zero crossing around the 450ms boundary
        if not inverting and n >= next_invert_sample:
            # Check for zero crossing: sin(phase) close to 0
            if abs(math.sin(phase)) < 0.15 or n >= next_invert_sample + 16:
                phase = (phase + math.pi) % (2.0 * math.pi)
                next_invert_sample += invert_stride

        val = amp * math.sin(phase)
        samples.append(val)
        phase = (phase + step) % (2.0 * math.pi)

    # Apply 5ms cosine envelope to entry and exit of the 3-second block
    samples = apply_cosine_envelope(samples, fade_ms=5.0)
    return samples


def mod_bell_202_fsk() -> list:
    """
    Bell 202 Continuous-Phase Frequency Shift Keying (CPFSK) Simulation:
    Alternating 1200 Hz (Mark) and 2200 Hz (Space) at 15ms symbol intervals for 1.5s.
    Confuses speech-to-text frontends (Whisper/Deepgram) into dropping frames.
    """
    total_duration_ms = 1500.0
    symbol_ms = 15.0
    num_symbols = int(total_duration_ms // symbol_ms)  # 100 symbols
    amp = dbfs_to_linear(LEVEL_SINGLE_TONE)

    samples = []
    phase = 0.0
    samples_per_symbol = int(round((symbol_ms / 1000.0) * SAMPLE_RATE))  # 120 samples

    for symbol_idx in range(num_symbols):
        freq = 1200.0 if (symbol_idx % 2 == 0) else 2200.0
        step = 2.0 * math.pi * freq / SAMPLE_RATE
        for _ in range(samples_per_symbol):
            samples.append(amp * math.sin(phase))
            phase = (phase + step) % (2.0 * math.pi)

    samples = apply_cosine_envelope(samples, fade_ms=5.0)
    return samples


def mod_amd_spoof() -> list:
    """
    Answering Machine Detection (AMD) Human Spoof:
    Synthesizes a 250ms voiced formant burst (120 Hz fundamental + 240/360/720 Hz harmonics)
    followed by exactly 3.2 seconds of dead air.
    Tricks AMD algorithms into classifying the line as a live human greeting ("Hello?").
    """
    duration_ms = 250.0
    count = int(round((duration_ms / 1000.0) * SAMPLE_RATE))

    # Calibrated harmonic levels: f0 at -16 dBFS, harmonics scaled downward
    amp_f0 = dbfs_to_linear(-16.0)
    amp_f1 = dbfs_to_linear(-19.0)
    amp_f2 = dbfs_to_linear(-22.0)
    amp_f3 = dbfs_to_linear(-26.0)

    step_f0 = 2.0 * math.pi * 120.0 / SAMPLE_RATE
    step_f1 = 2.0 * math.pi * 240.0 / SAMPLE_RATE
    step_f2 = 2.0 * math.pi * 360.0 / SAMPLE_RATE
    step_f3 = 2.0 * math.pi * 720.0 / SAMPLE_RATE

    burst = []
    for i in range(count):
        s = (amp_f0 * math.sin(step_f0 * i) +
             amp_f1 * math.sin(step_f1 * i) +
             amp_f2 * math.sin(step_f2 * i) +
             amp_f3 * math.sin(step_f3 * i))
        burst.append(s)

    burst = apply_cosine_envelope(burst, fade_ms=5.0)
    silence = generate_silence(3200.0)
    return burst + silence


def mod_vad_thrash() -> list:
    """
    AI Voice Agent Turn-Taking Jammer:
    5 cycles of pink noise bursts (-22 dBFS) separated by randomized 2.2s-4.1s silence intervals.
    Randomized duration (160-220ms) and spacing defeat WebRTC RNNoise adaptive filters,
    forcing LLM voice agents with barge-in VAD to perpetually interrupt their own TTS.
    """
    kellet = KelletPinkNoise()
    seq = []

    for _ in range(5):
        burst_ms = random.uniform(160.0, 220.0)
        burst_count = int(round((burst_ms / 1000.0) * SAMPLE_RATE))
        raw_pink = kellet.generate(burst_count)

        # Scale pink noise to -22 dBFS RMS
        rms = math.sqrt(sum(x * x for x in raw_pink) / burst_count) if burst_count > 0 else 1.0
        if rms < 1e-6:
            rms = 1e-6
        scale = dbfs_to_linear(LEVEL_PINK_BURST) / rms
        pink_burst = [x * scale for x in raw_pink]
        pink_burst = apply_cosine_envelope(pink_burst, fade_ms=5.0)
        seq.extend(pink_burst)

        # Randomized inter-burst silence
        silence_ms = random.uniform(2200.0, 4100.0)
        seq.extend(generate_silence(silence_ms))

    return seq


def mod_dtmf_fuzz() -> list:
    """
    IVR / Dialer Keypress Trap:
    Emits rapid dual-tone sequence: '9', '*', '#', '0', '2'
    (70ms tone, 50ms gap) with +2.0 dB forward column twist.
    Triggers automated carrier 'do-not-call' / opt-out macros.
    """
    dtmf_map = {
        '9': (852.0, 1477.0),
        '*': (941.0, 1209.0),
        '#': (941.0, 1477.0),
        '0': (941.0, 1336.0),
        '2': (697.0, 1336.0),
    }
    sequence = ['9', '*', '#', '0', '2']
    seq = []

    for digit in sequence:
        row_freq, col_freq = dtmf_map[digit]
        burst = generate_dual_tone(
            row_freq, col_freq, duration_ms=70.0,
            dbfs1=LEVEL_DTMF_LOW, dbfs2=LEVEL_DTMF_HIGH,
            envelope=True
        )
        seq.extend(burst)
        seq.extend(generate_silence(50.0))

    return seq


# -------------------------------------------------------------------------
# Module Registry
# -------------------------------------------------------------------------

MODULE_REGISTRY = {
    # Regional Signaling
    "na_nanp_ic": (sig_na_nanp_ic, "North American Bellcore Intercept SIT (913.8/1370.6/1776.7 Hz)"),
    "na_nanp_nc": (sig_na_nanp_nc, "North American No Circuit / Reorder SIT (985.2/1370.6/1776.7 Hz)"),
    "na_nanp_vacant": (sig_na_nanp_vacant, "North American Vacant Code SIT (985.2/1428.5/1776.7 Hz)"),
    "itu_e180_sit": (sig_itu_e180_sit, "ITU-T E.180 Standard SIT (EU/India/Brazil/Global GSM: 950/1400/1800 Hz)"),
    "uk_bt_sit": (sig_uk_bt_sit, "UK BT SIN 350 Standard SIT (950/1400/1800 Hz + 1000ms silence)"),
    "uk_bt_nu": (sig_uk_bt_nu, "UK BT Number Unobtainable (400.0 Hz continuous, 2500ms)"),
    "eu_etsi_congestion": (sig_eu_etsi_congestion, "EU/ETSI Fast Busy / Congestion (425.0 Hz 250ms ON/OFF x6)"),
    "jp_ntt_busy": (sig_jp_ntt_busy, "Japan NTT Howler / Busy Tone (400.0 Hz 500ms ON/OFF x3)"),
    # Advanced Anti-Automation & AI Countermeasures
    "fax_cng": (mod_fax_cng, "T.30 Fax Calling Tone (1100.0 Hz, 500ms ON / 3000ms OFF)"),
    "modem_ced": (mod_modem_ced, "ITU-T V.25 Answer Tone (2100.0 Hz with 180° phase reversals @ 450ms)"),
    "bell_202_fsk": (mod_bell_202_fsk, "Bell 202 CPFSK Data Burst (1200/2200 Hz, 15ms baud, 1500ms)"),
    "amd_spoof": (mod_amd_spoof, "AMD Formant Speech Spoof (120/240/360/720 Hz burst + 3.2s dead air)"),
    "vad_thrash": (mod_vad_thrash, "AI Voice Agent VAD Jammer (5x jittered pink noise bursts -22 dBFS)"),
    "dtmf_fuzz": (mod_dtmf_fuzz, "IVR / Dialer Opt-Out Macro Trap (DTMF 9, *, #, 0, 2 with +2dB twist)"),
    "comfort_noise": (lambda: generate_comfort_noise(2000.0), "300-3000 Hz Band-Limited Line Comfort Noise (-45 dBFS, 2s)"),
    "silence": (lambda: generate_silence(500.0), "Digital Silence Gap (500ms)"),
}


# -------------------------------------------------------------------------
# Audio Ingest, Resampling, and Anti-Aliasing
# -------------------------------------------------------------------------

def load_and_resample_wav(path: str, target_rate: int = SAMPLE_RATE) -> list:
    """
    Read an arbitrary WAV file, downmix multi-channel audio to mono,
    apply a 2nd-order Butterworth low-pass anti-aliasing filter (fc = 3600 Hz),
    and resample to 8000 Hz via linear interpolation.
    """
    with wave.open(path, 'rb') as w:
        channels = w.getnchannels()
        sampwidth = w.getsampwidth()
        framerate = w.getframerate()
        nframes = w.getnframes()
        raw_bytes = w.readframes(nframes)

    # Unpack samples into normalized floats [-1.0, 1.0]
    unpacked_samples = []
    if sampwidth == 1:
        # 8-bit unsigned PCM
        fmt = f"{len(raw_bytes)}B"
        raw_vals = struct.unpack(fmt, raw_bytes)
        for val in raw_vals:
            unpacked_samples.append((val - 128) / 128.0)
    elif sampwidth == 2:
        # 16-bit signed PCM
        num_shorts = len(raw_bytes) // 2
        fmt = f"<{num_shorts}h"
        raw_vals = struct.unpack(fmt, raw_bytes)
        for val in raw_vals:
            unpacked_samples.append(val / 32768.0)
    else:
        raise ValueError(f"Unsupported WAV sample width: {sampwidth * 8}-bit (only 8-bit and 16-bit supported)")

    # Downmix to mono
    mono_samples = []
    if channels == 1:
        mono_samples = unpacked_samples
    else:
        for i in range(0, len(unpacked_samples), channels):
            frame_vals = unpacked_samples[i:i + channels]
            mono_samples.append(sum(frame_vals) / channels)

    # Anti-Aliasing Low-Pass Filter
    # If source sample rate is higher than target, filter frequencies above 3600 Hz
    # using a 4th-order Butterworth filter (2 cascaded biquads) to prevent foldover into baseband.
    if framerate > target_rate:
        lpf1 = BiquadFilter("lpf", fc=3600.0, fs=framerate, q=0.54119610)
        lpf2 = BiquadFilter("lpf", fc=3600.0, fs=framerate, q=1.3065630)
        mono_samples = lpf2.process(lpf1.process(mono_samples))

    # Linear Interpolation Resampler
    if framerate == target_rate:
        target_floats = mono_samples
    else:
        num_target = int(round(len(mono_samples) * (target_rate / framerate)))
        target_floats = []
        ratio = framerate / target_rate
        src_len = len(mono_samples)

        for j in range(num_target):
            src_pos = j * ratio
            idx = int(src_pos)
            frac = src_pos - idx
            if idx >= src_len - 1:
                val = mono_samples[-1] if src_len > 0 else 0.0
            else:
                val = (1.0 - frac) * mono_samples[idx] + frac * mono_samples[idx + 1]
            target_floats.append(val)

    # Convert back to signed 16-bit linear scale
    return [x * 32767.0 for x in target_floats]


# -------------------------------------------------------------------------
# Output Writers (File & Unseekable Stdout)
# -------------------------------------------------------------------------

def samples_to_pcm16_bytes(samples: list) -> bytes:
    """Pack list of float samples into 16-bit signed little-endian PCM byte string."""
    clamped = [clamp16(x) for x in samples]
    fmt = f"<{len(clamped)}h"
    return struct.pack(fmt, *clamped)


def build_riff_header(pcm_byte_len: int, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Manually pack standard 44-byte RIFF/WAVE header for unseekable stdout streams."""
    byte_rate = sample_rate * NUM_CHANNELS * (BITS_PER_SAMPLE // 8)
    block_align = NUM_CHANNELS * (BITS_PER_SAMPLE // 8)
    return struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + pcm_byte_len,
        b'WAVE',
        b'fmt ',
        16,  # Subchunk1Size (16 for PCM)
        1,   # AudioFormat (1 = PCM)
        NUM_CHANNELS,
        sample_rate,
        byte_rate,
        block_align,
        BITS_PER_SAMPLE,
        b'data',
        pcm_byte_len
    )


def atomic_write_wav(output_path: str, samples: list, sample_rate: int = SAMPLE_RATE):
    """
    Atomically write audio samples to a WAV file via a temporary file
    and atomic rename (os.replace) to prevent partial corruption.
    """
    path = pathlib.Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".wav.tmp")

    pcm_bytes = samples_to_pcm16_bytes(samples)
    with wave.open(str(tmp_path), 'wb') as w:
        w.setnchannels(NUM_CHANNELS)
        w.setsampwidth(BITS_PER_SAMPLE // 8)
        w.setframerate(sample_rate)
        w.writeframes(pcm_bytes)

    os.replace(str(tmp_path), str(path))


def write_stdout_stream(samples: list, sample_rate: int = SAMPLE_RATE):
    """Write WAV stream directly to sys.stdout.buffer without calling seek()."""
    pcm_bytes = samples_to_pcm16_bytes(samples)
    header = build_riff_header(len(pcm_bytes), sample_rate=sample_rate)
    sys.stdout.buffer.write(header)
    sys.stdout.buffer.write(pcm_bytes)
    sys.stdout.buffer.flush()


# -------------------------------------------------------------------------
# Goertzel Spectral Inspector & Diagnostics
# -------------------------------------------------------------------------

def goertzel(samples: list, target_freq: float, sample_rate: int = SAMPLE_RATE) -> float:
    """
    Pure-Python Generalized Goertzel algorithm to compute relative spectral power (dBFS)
    at an exact continuous target frequency without requiring FFT/SciPy.
    """
    n = len(samples)
    if n == 0:
        return -100.0

    omega = 2.0 * math.pi * target_freq / sample_rate
    coeff = 2.0 * math.cos(omega)

    s_prev = 0.0
    s_prev2 = 0.0
    for sample in samples:
        s = sample + coeff * s_prev - s_prev2
        s_prev2 = s_prev
        s_prev = s

    power = s_prev2 * s_prev2 + s_prev * s_prev - coeff * s_prev * s_prev2
    ref = (32767.0 * n / 2.0) ** 2
    if ref <= 0.0 or power <= 1e-12:
        return -100.0

    ratio = power / ref
    return 10.0 * math.log10(ratio) if ratio > 0 else -100.0


def inspect_wav(path: str):
    """Analyze a WAV file and print audio metrics and detected telecom signaling frequencies."""
    if not os.path.exists(path):
        print(f"Error: file '{path}' does not exist.")
        sys.exit(1)

    with wave.open(path, 'rb') as w:
        channels = w.getnchannels()
        sampwidth = w.getsampwidth()
        framerate = w.getframerate()
        nframes = w.getnframes()
        raw_bytes = w.readframes(nframes)

    duration_s = nframes / framerate if framerate > 0 else 0.0
    num_samples = len(raw_bytes) // sampwidth
    if sampwidth == 2:
        samples = list(struct.unpack(f"<{num_samples}h", raw_bytes))
    elif sampwidth == 1:
        samples = [(b - 128) * 256 for b in struct.unpack(f"{num_samples}B", raw_bytes)]
    else:
        print(f"Warning: unsupported sample width {sampwidth * 8}-bit for inspection.")
        samples = []

    # Calculate Peak & RMS dBFS
    if samples:
        peak = max(abs(s) for s in samples)
        peak_dbfs = 20.0 * math.log10(peak / 32767.0) if peak > 0 else -100.0
        rms = math.sqrt(sum(s * s for s in samples) / len(samples))
        rms_dbfs = 20.0 * math.log10(rms / 32767.0) if rms > 0 else -100.0
    else:
        peak_dbfs = -100.0
        rms_dbfs = -100.0

    print("=" * 64)
    print(f"TELCOTRAP AUDIO INSPECTOR: {path}")
    print("=" * 64)
    print(f"Channels         : {channels} ({'Mono' if channels == 1 else 'Stereo'})")
    print(f"Sample Rate      : {framerate} Hz")
    print(f"Bit Depth        : {sampwidth * 8}-bit PCM")
    print(f"Frame Count      : {nframes} samples")
    print(f"Duration         : {duration_s:.3f} seconds")
    print(f"Peak Amplitude   : {peak_dbfs:.2f} dBFS")
    print(f"RMS Energy       : {rms_dbfs:.2f} dBFS")
    print("-" * 64)
    print("Detected Telecom & Supervisory Frequencies (Goertzel Peak Detection):")

    test_freqs = [
        (400.0, "UK NU / Japan NTT"),
        (425.0, "EU ETSI Congestion"),
        (697.0, "DTMF Row 1"),
        (770.0, "DTMF Row 2"),
        (852.0, "DTMF Row 3"),
        (913.8, "NANP Intercept Low"),
        (941.0, "DTMF Row 4"),
        (950.0, "ITU E.180 / BT SIT Low"),
        (985.2, "NANP Vacant/NC Low"),
        (1100.0, "T.30 Fax CNG"),
        (1200.0, "Bell 202 Mark / DTMF Col 1"),
        (1336.0, "DTMF Col 2"),
        (1370.6, "NANP SIT Mid"),
        (1400.0, "ITU E.180 / BT SIT Mid"),
        (1428.5, "NANP Vacant Mid"),
        (1477.0, "DTMF Col 3"),
        (1776.7, "NANP SIT High"),
        (1800.0, "ITU E.180 / BT SIT High"),
        (2100.0, "ITU V.25 CED"),
        (2200.0, "Bell 202 Space"),
    ]

    detected = []
    # Analyze middle slice to avoid edge effects
    slice_samples = samples[min(len(samples), 400):max(0, len(samples) - 400)] if len(samples) > 800 else samples
    for f, desc in test_freqs:
        p = goertzel(slice_samples, f, sample_rate=framerate)
        if p >= -25.0:
            detected.append((f, desc, p))

    if detected:
        for f, desc, p in detected:
            print(f"  * {f:7.1f} Hz [{desc:24s}] : {p:6.1f} dBFS")
    else:
        print("  (No prominent standard signaling frequencies detected above -25 dBFS)")
    print("=" * 64)


# -------------------------------------------------------------------------
# Production Release Packs
# -------------------------------------------------------------------------

RELEASE_PACK_PRESETS = {
    "US_Canada_Max_Disrupt.wav": [
        "na_nanp_ic", "silence", "fax_cng", "amd_spoof"
    ],
    "US_Canada_Vacant_Drop.wav": [
        "na_nanp_vacant", "silence", "fax_cng"
    ],
    "EU_India_Brazil_Disconnect.wav": [
        "itu_e180_sit", "silence", "eu_etsi_congestion", "fax_cng"
    ],
    "UK_Disconnect_Fax.wav": [
        "uk_bt_sit", "uk_bt_nu", "fax_cng"
    ],
    "APAC_Japan_Disconnect.wav": [
        "jp_ntt_busy", "itu_e180_sit", "fax_cng"
    ],
    "AI_Agent_VAD_Tarpit.wav": [
        "amd_spoof", "vad_thrash", "dtmf_fuzz", "comfort_noise"
    ],
}


def build_release_pack(output_dir: str = "./release_wavs"):
    """Generate all production regional preset combinations into output directory."""
    out_path = pathlib.Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"Building telcotrap Production Release Pack into: {out_path.resolve()}")
    for filename, modules in RELEASE_PACK_PRESETS.items():
        combined_samples = []
        for mod_name in modules:
            func, _ = MODULE_REGISTRY[mod_name]
            combined_samples.extend(func())

        dest_file = out_path / filename
        atomic_write_wav(str(dest_file), combined_samples)
        duration = len(combined_samples) / SAMPLE_RATE
        size_kb = (len(combined_samples) * 2 + 44) / 1024.0
        print(f"  [+] Generated: {filename:<32} ({duration:5.2f}s | {size_kb:6.1f} KB)")

    print(f"\nAll 6 production presets generated successfully.")


# -------------------------------------------------------------------------
# CLI Dispatcher
# -------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="telcotrap: Zero-Dependency Telephony Trap & Anti-Robocall Audio Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate US/Canada SIT Intercept followed by Fax CNG:
  python3 telcotrap.py --sequence na_nanp_ic,fax_cng --output intercept_fax.wav

  # Prepend US SIT Vacant tone to an existing voice message:
  python3 telcotrap.py --sequence na_nanp_vacant --mix-voice my_greeting.wav --output greeting_trap.wav

  # Generate the full production release pack:
  python3 telcotrap.py --build-release-pack

  # Pipe raw audio directly to player:
  python3 telcotrap.py --sequence na_nanp_ic,fax_cng --output - | aplay

  # Inspect audio file parameters and detect telecom signaling:
  python3 telcotrap.py --inspect release_wavs/US_Canada_Max_Disrupt.wav
        """
    )

    parser.add_argument("--sequence", type=str, help="Comma-separated list of modules to chain")
    parser.add_argument("--output", "-o", type=str, default="output.wav",
                        help="Output WAV path (use '-' for stdout streaming, default: output.wav)")
    parser.add_argument("--mix-voice", type=str, help="Path to input voice WAV to append after trap sequence")
    parser.add_argument("--mix-lead-in", type=float, default=300.0,
                        help="Silence duration (ms) between trap sequence and mixed voice (default: 300ms)")
    parser.add_argument("--inspect", type=str, help="Inspect a WAV file and detect telecom signaling frequencies")
    parser.add_argument("--build-release-pack", action="store_true",
                        help="Build all standard regional preset WAV files into ./release_wavs/")
    parser.add_argument("--release-dir", type=str, default="./release_wavs",
                        help="Destination directory for release pack (default: ./release_wavs)")
    parser.add_argument("--list-modules", action="store_true", help="List all available modules in JSON format")

    args = parser.parse_args()

    if args.list_modules:
        dump = {name: desc for name, (_, desc) in MODULE_REGISTRY.items()}
        print(json.dumps(dump, indent=2))
        return

    if args.inspect:
        inspect_wav(args.inspect)
        return

    if args.build_release_pack:
        build_release_pack(args.release_dir)
        return

    if not args.sequence and not args.mix_voice:
        parser.print_help()
        sys.exit(1)

    # Build sequence
    samples = []
    if args.sequence:
        mod_names = [m.strip() for m in args.sequence.split(",") if m.strip()]
        for name in mod_names:
            if name not in MODULE_REGISTRY:
                print(f"Error: Unknown module '{name}'. Run with --list-modules to see available modules.", file=sys.stderr)
                sys.exit(1)
            func, _ = MODULE_REGISTRY[name]
            samples.extend(func())

    # Prepend to mixed voice if specified
    if args.mix_voice:
        if not os.path.exists(args.mix_voice):
            print(f"Error: Voice file '{args.mix_voice}' not found.", file=sys.stderr)
            sys.exit(1)
        voice_samples = load_and_resample_wav(args.mix_voice)
        if samples:
            samples.extend(generate_silence(args.mix_lead_in))
        samples.extend(voice_samples)

    if not samples:
        print("Error: No audio generated.", file=sys.stderr)
        sys.exit(1)

    # Dispatch to stdout or file
    if args.output == "-":
        write_stdout_stream(samples)
    else:
        atomic_write_wav(args.output, samples)
        duration = len(samples) / SAMPLE_RATE
        size_kb = (len(samples) * 2 + 44) / 1024.0
        print(f"Success: Wrote {args.output} ({duration:.2f}s | {size_kb:.1f} KB | 8000 Hz 16-bit Mono)")


if __name__ == "__main__":
    main()
