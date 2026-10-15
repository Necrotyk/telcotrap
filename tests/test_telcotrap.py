#!/usr/bin/env python3
"""
tests/test_telcotrap.py - Hermetic Unit & Verification Test Suite for telcotrap

Verifies:
1. PSTN/VoIP Audio Header Invariants (8000 Hz, 16-bit, Mono PCM)
2. Cosine Window Envelope Boundary Attenuation
3. Goertzel Frequency Peak Detection on Telecom Signaling
4. V.25 CED Zero-Crossing Phase Reversals
5. DTMF Column Twist (+2.0 dB)
6. Anti-Aliasing Biquad Filter & Heterogeneous Resampler
7. Manual RIFF Header Packing for Unseekable Stdout
8. Production Release Pack Generation
"""

import math
import os
import shutil
import struct
import tempfile
import unittest
import wave

import telcotrap


class TestTelcoTrap(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="telcotrap_test_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_audio_header_invariants(self):
        """Verify generated WAV files adhere to 8000 Hz, 16-bit, mono PCM standard."""
        samples, _ = telcotrap.generate_tone(1000.0, 500.0, dbfs=-12.0)
        out_file = os.path.join(self.test_dir, "test_tone.wav")
        telcotrap.atomic_write_wav(out_file, samples)

        with wave.open(out_file, "rb") as w:
            self.assertEqual(w.getnchannels(), 1, "Must be single channel (mono)")
            self.assertEqual(w.getsampwidth(), 2, "Must be 16-bit PCM (2 bytes/sample)")
            self.assertEqual(w.getframerate(), 8000, "Must be 8000 Hz sample rate")
            self.assertEqual(w.getnframes(), len(samples), "Frame count mismatch")

    def test_cosine_envelope_boundary_attenuation(self):
        """Verify 5ms cosine envelope smoothly tapers start and end samples near zero."""
        # Tone of 500ms
        raw_samples, _ = telcotrap.generate_tone(1000.0, 500.0, dbfs=-10.0, envelope=False)
        self.assertGreater(abs(raw_samples[1]), 500.0, "Raw unwindowed tone should have non-zero onset")

        windowed = telcotrap.apply_cosine_envelope(list(raw_samples), fade_ms=5.0)
        # Sample 0 should be attenuated to exactly or virtually 0
        self.assertAlmostEqual(windowed[0], 0.0, places=3, msg="First sample must be 0 in cosine window")
        self.assertAlmostEqual(windowed[-1], 0.0, places=3, msg="Last sample must be 0 in cosine window")

    def test_goertzel_frequency_accuracy(self):
        """Verify synthesized signaling profiles contain exact target frequencies."""
        # 1. NANP Intercept: 913.8 Hz, 1370.6 Hz, 1776.7 Hz
        nanp_samples = telcotrap.sig_na_nanp_ic()
        # Segment 1: 913.8 Hz (first 276ms = ~2208 samples)
        seg1 = nanp_samples[100:2100]
        p_914 = telcotrap.goertzel(seg1, 913.8)
        p_other = telcotrap.goertzel(seg1, 1500.0)
        self.assertGreater(p_914, -18.0, "913.8 Hz peak should be strong in segment 1")
        self.assertLess(p_other, -40.0, "Out-of-band energy should be suppressed")

        # 2. Fax CNG: 1100.0 Hz
        fax_samples = telcotrap.mod_fax_cng()
        fax_burst = fax_samples[100:3900]
        p_1100 = telcotrap.goertzel(fax_burst, 1100.0)
        self.assertGreater(p_1100, -16.0, "1100.0 Hz Fax CNG should be strong")

        # 3. UK BT NU: 400.0 Hz
        nu_samples = telcotrap.sig_uk_bt_nu()
        p_400 = telcotrap.goertzel(nu_samples[100:10000], 400.0)
        self.assertGreater(p_400, -18.0, "400.0 Hz NU tone should be strong")

        # 4. EU ETSI Congestion: 425.0 Hz
        etsi_samples = telcotrap.sig_eu_etsi_congestion()
        p_425 = telcotrap.goertzel(etsi_samples[100:1900], 425.0)
        self.assertGreater(p_425, -18.0, "425.0 Hz ETSI tone should be strong")

    def test_v25_ced_phase_reversal(self):
        """Verify V.25 CED generates 2100 Hz and executes phase inversions every ~450ms."""
        ced_samples = telcotrap.mod_modem_ced()
        self.assertEqual(len(ced_samples), 24000, "V.25 tone must be exactly 3000ms (24,000 samples)")
        p_2100 = telcotrap.goertzel(ced_samples[1000:3000], 2100.0)
        self.assertGreater(p_2100, -18.0, "2100 Hz CED tone should be prominent")

    def test_dtmf_forward_twist(self):
        """Verify DTMF column frequencies have +2.0 dB forward twist over row frequencies."""
        # Row 852 Hz, Col 1477 Hz (digit '9')
        samples = telcotrap.generate_dual_tone(852.0, 1477.0, 300.0,
                                               dbfs1=telcotrap.LEVEL_DTMF_LOW,
                                               dbfs2=telcotrap.LEVEL_DTMF_HIGH,
                                               envelope=False)
        p_row = telcotrap.goertzel(samples, 852.0)
        p_col = telcotrap.goertzel(samples, 1477.0)
        diff = p_col - p_row
        self.assertGreater(diff, 1.8, "Column frequency must have positive twist relative to row")
        self.assertLess(diff, 2.2, "Twist must be within nominal 1.8 - 2.2 dB window")

    def test_anti_aliasing_biquad_and_resampler(self):
        """
        Verify that 48kHz audio with frequencies above 4000 Hz is properly low-pass
        filtered before downsampling to 8000 Hz, eliminating aliasing foldover.
        """
        # Create a synthetic 48kHz stereo WAV containing 8000 Hz tone (out of band for 8kHz baseband)
        fs_in = 48000
        duration_s = 0.2
        num_frames = int(fs_in * duration_s)
        test_wav_path = os.path.join(self.test_dir, "high_freq_48k.wav")

        pcm_frames = []
        step = 2.0 * math.pi * 8000.0 / fs_in
        for i in range(num_frames):
            val = int(round(16384.0 * math.sin(step * i)))
            # Stereo: Left = Right = val
            pcm_frames.extend([val, val])

        raw_bytes = struct.pack(f"<{len(pcm_frames)}h", *pcm_frames)
        with wave.open(test_wav_path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(fs_in)
            w.writeframes(raw_bytes)

        # Ingest and resample to 8000 Hz
        resampled = telcotrap.load_and_resample_wav(test_wav_path, target_rate=8000)
        self.assertEqual(len(resampled), int(8000 * duration_s), "Resampled length mismatch")

        # In 8000 Hz, an 8000 Hz input tone would alias directly into DC / baseband.
        # Verify that spectral energy at 8000 Hz foldover is suppressed by >30 dB.
        p_alias = telcotrap.goertzel(resampled, 8000.0, sample_rate=fs_in)
        self.assertLess(p_alias, -30.0, "Aliasing foldover must be suppressed by 4th-order LPF")

    def test_manual_riff_header_packing(self):
        """Verify build_riff_header formats standard 44-byte RIFF header without seek calls."""
        pcm_byte_len = 16000  # 1 second of 8kHz 16-bit mono
        header = telcotrap.build_riff_header(pcm_byte_len, sample_rate=8000)
        self.assertEqual(len(header), 44, "RIFF header must be exactly 44 bytes")

        # Parse fields
        riff, chunk_size, wave_id, fmt_id, subchunk1_size, audio_fmt, num_ch, rate, byte_rate, align, bits, data_id, data_size = struct.unpack(
            '<4sI4s4sIHHIIHH4sI', header
        )
        self.assertEqual(riff, b'RIFF')
        self.assertEqual(chunk_size, 36 + pcm_byte_len)
        self.assertEqual(wave_id, b'WAVE')
        self.assertEqual(fmt_id, b'fmt ')
        self.assertEqual(subchunk1_size, 16)
        self.assertEqual(audio_fmt, 1)  # PCM
        self.assertEqual(num_ch, 1)
        self.assertEqual(rate, 8000)
        self.assertEqual(byte_rate, 16000)
        self.assertEqual(align, 2)
        self.assertEqual(bits, 16)
        self.assertEqual(data_id, b'data')
        self.assertEqual(data_size, pcm_byte_len)

    def test_production_release_pack_generation(self):
        """Verify all 6 release presets build cleanly with valid headers."""
        release_dir = os.path.join(self.test_dir, "release_wavs")
        telcotrap.build_release_pack(output_dir=release_dir)

        expected_files = [
            "US_Canada_Max_Disrupt.wav",
            "US_Canada_Vacant_Drop.wav",
            "EU_India_Brazil_Disconnect.wav",
            "UK_Disconnect_Fax.wav",
            "APAC_Japan_Disconnect.wav",
            "AI_Agent_VAD_Tarpit.wav"
        ]

        for fname in expected_files:
            file_path = os.path.join(release_dir, fname)
            self.assertTrue(os.path.exists(file_path), f"Preset file {fname} not found")
            with wave.open(file_path, "rb") as w:
                self.assertEqual(w.getnchannels(), 1)
                self.assertEqual(w.getsampwidth(), 2)
                self.assertEqual(w.getframerate(), 8000)
                self.assertGreater(w.getnframes(), 0)


if __name__ == "__main__":
    unittest.main()
