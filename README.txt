================================================================================
telcotrap: Telephony Trap & Anti-Robocall Audio Synthesis Toolkit
================================================================================

A zero-dependency, public-ready Python audio synthesis engine and countermeasure
toolkit designed to disrupt predictive dialers, Answering Machine Detection (AMD)
DSPs, and conversational AI voice agents across global telecommunications networks.

Output Standard: 8000 Hz, 16-bit Signed Little-Endian PCM Mono WAV (PSTN/VoIP).
Signal Standards: Telcordia GR-506-CORE, ITU-T E.180, BT SIN 350, T.30, ITU-T V.25.
Envelope: 5ms raised cosine window on all tone boundaries to eliminate clicks.


================================================================================
1. REGIONAL PRESET SELECTION MATRIX & THREAT MODELS
================================================================================

Threat Model A: Robocall & Autodialer Database Scrubbing
Target: Predictive dialers (Asterisk, Vicidial, FreeSWITCH, Genesys, Five9).
Mechanism: Dialers employ DSP tone detectors to classify outbound call outcomes
in real time. When a Special Information Tone (SIT) or Fax CNG tone is detected
during call setup, the dialer automatically marks the recipient as "Disconnected",
"Vacant Number", or "Fax Machine", immediately dropping the call and purging
the phone number from active telemarketing databases.

Threat Model B: Conversational AI Voice Bot Tarpitting
Target: LLM speech agents with Voice Activity Detection (VAD) (Whisper, Deepgram,
Cartesia, LiveKit, OpenAI Realtime API).
Mechanism: Conversational AI bots rely on barge-in VAD thresholds to know when a
human has started speaking. telcotrap's VAD thrashing engine emits intermittent,
jittered pink noise bursts and rapid Bell 202 FSK data bursts, forcing the AI bot
to repeatedly interrupt its own text-to-speech output, discard its inference state,
and stall in infinite turn-taking loops without ever delivering a scam pitch.


REGIONAL PRESET ASSIGNMENT:

1. North America (United States, Canada):
   - Primary Disconnect: US_Canada_Max_Disrupt.wav
     Contains: Bellcore Intercept SIT (913.8 / 1370.6 / 1776.7 Hz) + Fax CNG
     (1100 Hz) + AMD Human Formant Spoof.
     Use Case: Best all-around defensive greeting for US/Canadian mobile lines.
   - Clean Disconnect: US_Canada_Vacant_Drop.wav
     Contains: Bellcore Vacant Code SIT (985.2 / 1428.5 / 1776.7 Hz) + Fax CNG.
     Use Case: Aggressive number scrubbing for lines receiving heavy telemarketing.

2. European Union, India, Brazil, Latin America, Global GSM:
   - Recommended: EU_India_Brazil_Disconnect.wav
     Contains: ITU-T E.180 Standard SIT (950 / 1400 / 1800 Hz) + ETSI Congestion
     Fast Busy (425 Hz 250ms ON/OFF) + T.30 Fax CNG (1100 Hz).
     Use Case: Standard telecommunications disconnect tone recognized by European,
     Indian, and South American carriers.

3. United Kingdom:
   - Recommended: UK_Disconnect_Fax.wav
     Contains: BT SIN 350 Standard SIT (950 / 1400 / 1800 Hz) + BT Number
     Unobtainable continuous tone (400 Hz) + T.30 Fax CNG.
     Use Case: Configured for British Telecom (BT), EE, O2, Vodafone UK networks.

4. Asia-Pacific & Japan:
   - Recommended: APAC_Japan_Disconnect.wav
     Contains: NTT Howler/Busy tone (400 Hz 500ms ON/OFF) + ITU-T E.180 SIT + Fax CNG.
     Use Case: Japan, Australia, Singapore, and regional Pacific carrier networks.

5. AI Voice Agent & Robocall Tarpit (Global):
   - Recommended: AI_Agent_VAD_Tarpit.wav
     Contains: AMD Formant Speech Spoof (120 Hz fundamental + harmonics) + 5-cycle
     jittered pink noise VAD thrashing + DTMF IVR opt-out sequence ('9', '*', '#',
     '0', '2' with +2dB forward twist) + 300-3000 Hz line comfort noise.
     Use Case: Maximum disruption of conversational voice bots, AI agents, and
     interactive telemarketing voice systems.


================================================================================
2. CARRIER VOICEMAIL SETUP & DIRECT DIAL-IN DIRECTORY
================================================================================

To deploy a trap preset as your voicemail greeting, use your carrier's direct
voicemail system access number. Dial the code, navigate to the greeting settings
menu, hold your audio playback source to the microphone, and record the preset.

UNITED STATES:
- Verizon Wireless:
  1. Dial *86 (or call your own 10-digit number and press #).
  2. Enter your voicemail PIN followed by #.
  3. Press 4 for Personal Options -> Press 3 for Greetings -> Press 1 to record
     a Personal Greeting.
  4. Play the preset WAV file and press # when finished, then press 1 to save.
- AT&T Mobility:
  1. Press and hold 1 on your dialpad (or dial your own 10-digit number).
  2. If prompted, enter your password followed by #.
  3. Press 4 for Personal Options -> Press 3 for Greetings -> Press 2 to record
     a new personal greeting.
  4. Play the preset WAV file and press # when finished, then press 1 to save.
- T-Mobile US:
  1. Dial 123 (or press and hold 1).
  2. Enter your voicemail password followed by #.
  3. Press * to reach the main menu -> Press 4 for Personal Options -> Press 3 for
     Greetings -> Press 1 to record a new greeting.
  4. Play the preset WAV file, press # to stop recording, then press 1 to save.

CANADA:
- Rogers Wireless:
  1. Press and hold 1 on your phone dialpad.
  2. Enter your voicemail password.
  3. Press 4 for Personal Options -> Press 3 for Greetings -> Press 1 for Personal.
  4. Play the preset WAV file, press # when finished, then press 1 to confirm.
- Bell Mobility:
  1. Dial *98 (or press and hold 1).
  2. Enter your password.
  3. Press 4 for Personal Options -> Press 3 for Greetings -> Press 1 to record.
  4. Play the preset WAV file and save.
- Telus Mobility:
  1. Press and hold 1 on your phone dialpad.
  2. Enter your password followed by #.
  3. Press 4 for Personal Options -> Press 1 to change your greeting.
  4. Play the preset WAV file and confirm.

UNITED KINGDOM:
- EE (Everything Everywhere):
  1. Dial 222 from your handset.
  2. Press 2 for Greetings -> Press 1 to change your personal greeting.
  3. Play UK_Disconnect_Fax.wav into the mic and press # to save.
- O2 UK:
  1. Dial 901 from your mobile.
  2. Press * for the main menu -> Press 4 for Mailbox Settings -> Press 3 for
     Greetings -> Press 1 to record.
  4. Play UK_Disconnect_Fax.wav and press # to save.
- Vodafone UK:
  1. Dial 121 from your handset.
  2. Press 4 for Personal Settings -> Press 1 for Greetings.
  3. Play UK_Disconnect_Fax.wav and confirm.
- Three UK:
  1. Dial 123 from your mobile.
  2. Press 4 for Options -> Press 2 for Greetings.
  3. Play UK_Disconnect_Fax.wav and save.

EUROPEAN UNION:
- Telekom Deutschland (Germany):
  1. Dial 3311 from your handset.
  2. Press 3 for Mailbox Settings -> Press 1 for Greeting Menu.
  3. Play EU_India_Brazil_Disconnect.wav and save.
- Vodafone Germany:
  1. Dial 5500 from your handset.
  2. Press 2 for Options -> Press 1 for Greetings.
  3. Play EU_India_Brazil_Disconnect.wav and save.
- Orange France:
  1. Dial 888 from your mobile.
  2. Press 2 for Personal Greeting -> Press 1 to record.
  3. Play EU_India_Brazil_Disconnect.wav and confirm.

BRAZIL & LATIN AMERICA:
- Vivo (Brazil):
  1. Dial *555 from your mobile.
  2. Access greeting customization (Saudacao Personalizada).
  3. Play EU_India_Brazil_Disconnect.wav and confirm.
- Claro (Brazil):
  1. Dial *555 from your mobile.
  2. Follow voice prompt to change greeting (Opcoes da Caixa Postal).
  3. Play EU_India_Brazil_Disconnect.wav and save.
- TIM (Brazil):
  1. Dial *100 from your handset.
  2. Access menu 4 (Configuracoes) -> Option 2 (Mensagem de Saudacao).
  3. Play EU_India_Brazil_Disconnect.wav and save.

INDIA (Jio, Airtel, Vi):
In India, carrier voicemail is rarely enabled by default. Most spam protection
relies on Call Forwarding / Missed Call Alerts or On-Device Screening:
- Jio / Airtel / Vi Conditional Call Forwarding:
  To forward incoming calls when busy or unanswered to an external PBX or voicemail
  line loaded with telcotrap audio:
  * Forward When Unanswered: Dial *61*<Voicemail_Number>*11*30#
  * Forward When Busy: Dial *67*<Voicemail_Number>#
  * Forward When Unreachable: Dial *62*<Voicemail_Number>#
  * Deactivate All Forwarding: Dial ##002#
- On-Device Native Screening (Pixel / Galaxy / iPhone) in India:
  See Section 3 for on-device greeting injection instructions.


================================================================================
3. HARDWARE & SOFTWARE AUDIO INJECTION GUIDE
================================================================================

Playing audio through a phone's built-in microphone using free-air acoustic
speaker playback often suffers from room reverberation, background noise, and
high-frequency distortion. Use one of the three verified methods below for a
crystal-clear, laboratory-grade injection:

METHOD A: Hardware 3.5mm TRRS Patch Cable (Highest Fidelity)
Equipment:
- Computer or audio player with 3.5mm headphone jack.
- Smartphone with 3.5mm headphone jack (or Apple/Samsung USB-C/Lightning to 3.5mm
  headphone adapter).
- 4-pole 3.5mm TRRS to TRRS auxiliary cable (CTIA standard).
- Inline attenuator pad (-20 dB to -30 dB) or TRRS breakout splitter (Headphone + Mic).

Procedure:
1. Connect the TRRS breakout adapter into the smartphone.
2. Plug a 3.5mm male-to-male cable from the PC headphone output into the
   adapter's microphone input jack.
   CAUTION: Audio line-out levels (approx. 1.0 V RMS) are much higher than
   microphone levels (approx. 10-50 mV RMS). Set the PC output volume to 10%
   to avoid overdriving the phone's microphone preamplifier.
3. Dial your carrier voicemail number on the smartphone.
4. When the prompt asks you to record your greeting, play the preset WAV file
   from your PC using any audio player.
5. Press # on the phone dialpad when playback completes.

METHOD B: Softphone & Virtual Audio Loopback (VoIP / PBX Systems)
If you manage your telephone lines via Asterisk, FreeSWITCH, 3CX, or a desktop
softphone (Linphone, MicroSIP, Zoiper):

On Linux (PipeWire / PulseAudio):
1. Create a virtual loopback device:
   pw-loopback --capture-props='media.class=Audio/Sink' --playback-props='media.class=Audio/Source'
2. Route the virtual sink into your softphone's microphone input.
3. Play the trap WAV directly into the virtual sink:
   pw-play -d <Sink_ID> release_wavs/US_Canada_Max_Disrupt.wav

On Windows:
1. Install VB-Audio Virtual Cable (free).
2. Set your softphone's microphone device to "CABLE Output (VB-Audio Virtual Cable)".
3. Open Windows Sound Settings and set your media player's output to "CABLE Input".
4. Play the WAV file while recording your greeting in the softphone.

On macOS:
1. Install BlackHole 2ch (free virtual audio driver).
2. Set your softphone microphone to BlackHole 2ch.
3. Route your audio player output to BlackHole 2ch and play the WAV file.

METHOD C: Acoustic Headphone-Cup Coupling (Zero-Equipment Method)
If you do not have patch cables or a softphone:
1. Put on a pair of closed-back, over-ear headphones connected to your PC.
2. Set PC playback volume to a normal, clear listening level (approx. 40-50%).
3. Place one headphone ear cup directly against the bottom microphone of your
   smartphone, ensuring a snug seal with no air gap.
4. Perform the procedure in a completely silent room.
5. Dial your carrier voicemail, wait for the record prompt, and play the WAV file.


================================================================================
4. ON-DEVICE VOICEMAIL (iOS LIVE VOICEMAIL & ANDROID CALL SCREEN)
================================================================================

Apple iOS 17+ Live Voicemail:
iOS 17 and later features on-device Live Voicemail that answers calls locally
without routing them to carrier servers.
To inject a custom telcotrap greeting:
1. Open the Phone app -> Tap Voicemail -> Tap Greeting in the top-left corner.
2. Tap "Custom".
3. Tap "Record", immediately start playback of your chosen telcotrap preset
   (e.g., US_Canada_Max_Disrupt.wav) using Method A, B, or C.
4. Tap "Stop" when the audio finishes, tap "Play" to review, then tap "Save".
Result: When unknown or scam numbers call your iPhone, iOS answers locally and
broadcasts the SIT tone and Fax CNG payload, forcing the predictive dialer to
drop the line and remove your number from its database.

Google Pixel Assistant Call Screen / Samsung Bixby Text Call:
1. Android devices with automated screening can play custom audio responses
   during screening.
2. If using a third-party screening app (YouMail, Truecaller, Hiya), navigate
   to Settings -> Voicemail Greeting -> Upload/Record Custom Greeting, and
   select the telcotrap WAV file from your device storage.


================================================================================
5. CLI SYNTHESIS & CUSTOM PIPELINE REFERENCE
================================================================================

telcotrap is a fully self-contained Python 3 script requiring zero external
dependencies. It runs anywhere Python 3.8+ is installed.

Basic Usage:
  python3 telcotrap.py --sequence <modules> --output <file.wav>

List All Available Signaling Modules:
  python3 telcotrap.py --list-modules

Generate Regional Release Pack:
  python3 telcotrap.py --build-release-pack

Inspect Audio Parameters & Detect Signaling:
  python3 telcotrap.py --inspect release_wavs/US_Canada_Max_Disrupt.wav

Prepend Trap to Your Own Voice Greeting:
  python3 telcotrap.py --sequence na_nanp_ic --mix-voice my_greeting.wav --output custom_trap.wav
  (Automatically downmixes stereo to mono, applies 4th-order anti-aliasing low-pass
  filtering at 3600 Hz, and resamples to 8000 Hz).

Pipe Audio Directly to Linux ALSA Player (No Temporary Files):
  python3 telcotrap.py --sequence na_nanp_ic,fax_cng --output - | aplay

AVAILABLE MODULES:
- na_nanp_ic         : Bellcore Intercept SIT (913.8, 1370.6, 1776.7 Hz)
- na_nanp_nc         : Bellcore No Circuit SIT (985.2, 1370.6, 1776.7 Hz)
- na_nanp_vacant     : Bellcore Vacant Code SIT (985.2, 1428.5, 1776.7 Hz)
- itu_e180_sit       : ITU-T E.180 Standard SIT (950, 1400, 1800 Hz)
- uk_bt_sit          : UK BT SIN 350 Standard SIT (950, 1400, 1800 Hz + silence)
- uk_bt_nu           : UK BT Number Unobtainable continuous tone (400 Hz)
- eu_etsi_congestion : EU/ETSI Fast Busy Congestion (425 Hz 250ms ON/OFF x6)
- jp_ntt_busy        : Japan NTT Howler/Busy tone (400 Hz 500ms ON/OFF x3)
- fax_cng            : T.30 Fax Calling Tone (1100 Hz, 500ms ON / 3000ms OFF)
- modem_ced          : ITU-T V.25 Answer Tone (2100 Hz with 180-deg phase flips)
- bell_202_fsk       : Bell 202 CPFSK Data Burst (1200/2200 Hz, 15ms symbols)
- amd_spoof          : AMD Formant Speech Spoof (120/240/360/720 Hz + 3.2s silence)
- vad_thrash         : AI Voice Agent VAD Jammer (5x jittered pink noise bursts)
- dtmf_fuzz          : IVR Opt-Out Macro Sequence ('9', '*', '#', '0', '2')
- comfort_noise      : 300-3000 Hz Band-Limited Line Comfort Noise (-45 dBFS)
- silence            : Digital Silence Gap (500ms)


================================================================================
6. LEGAL & ETHICAL DEFENSIVE USE NOTICE
================================================================================

telcotrap is released strictly for lawful, defensive consumer protection and
telecommunications research under the GPL-3.0-or-later license.
It is intended for individuals, researchers, and enterprises seeking to protect
their private telephone infrastructure and personal privacy against unlawful
robocalls, fraudulent caller ID impersonation, and unauthorized automated dialers.
Users are responsible for ensuring compliance with applicable telecommunications
regulations in their jurisdiction.
================================================================================
