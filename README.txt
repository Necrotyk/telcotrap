  _____ _____ _     ____ ___ _____ ____      _    ____  
 |_   _| ____| |   / ___/ _ \_   _|  _ \    / \  |  _ \ 
   | | |  _| | |  | |  | | | || | | |_) |  / _ \ | |_) |
   | | | |___| |__| |__| |_| || | |  _ <  / ___ \|  __/ 
   |_| |_____|_____\____\___/ |_| |_| \_\/_/   \_\_|    
  ======================================================
  Telephony Trap & Anti-Robocall DSP Audio Engine
  ======================================================

┌──────────────────────────────────────────────────────────────────────────────┐
│  CORE ARCHITECTURE & TELECOMMUNICATIONS STANDARDS                            │
├──────────────────────────────────────────────────────────────────────────────┤
│  ● Output Container : 8000 Hz, 16-Bit Signed Little-Endian PCM Mono WAV      │
│  ● Telecom Norms    : Telcordia GR-506-CORE, ITU-T E.180, BT SIN 350, T.30   │
│  ● Echo Protection  : ITU-T V.25 CED with Zero-Crossing Phase Reversal       │
│  ● Envelope Shaping : 5ms Raised Cosine Window on all Tone Boundaries        │
│  ● Level Headroom   : -12 dBFS Nominal (Prevents AMR-WB/G.711 AGC Ducking)   │
│  ● Portability      : Zero Dependencies (100% Python Standard Library)       │
└──────────────────────────────────────────────────────────────────────────────┘


────────────────────────────────────────────────────────────────────────────────
[ 01. SIGNALING ARCHITECTURE & TIMING CHARTS ]
────────────────────────────────────────────────────────────────────────────────

1. NORTH AMERICAN INTERCEPT SIT + FAX DISCONNECT:
   Preset: US_Canada_Max_Disrupt.wav

   0ms           276ms          552ms                    932ms         1432ms
   ┌─────────────┬──────────────┬────────────────────────┬─────────────┐
   │ 913.8 Hz    │ 1370.6 Hz    │ 1776.7 Hz              │ Silence Gap │
   │ (-12 dBFS)  │ (-12 dBFS)   │ (-12 dBFS)             │ (500ms)     │
   └─────────────┴──────────────┴────────────────────────┴─────────────┘
                                                         ▲
                                                         │
                                    Dialer Drops Call Here [SIT_INTERCEPT]

   Followed by:
   1432ms                 1932ms                                       4932ms
   ┌──────────────────────┬────────────────────────────────────────────┐
   │ 1100.0 Hz T.30 CNG   │ Carrier Dead-Air / Silence                 │
   │ (Fax Calling Tone)   │ (3000ms - Vicidial/Asterisk tags line FAX) │
   └──────────────────────┴────────────────────────────────────────────┘


2. AI AGENT VAD TARPIT & AMD HUMAN SPOOF:
   Preset: AI_Agent_VAD_Tarpit.wav

   0ms   250ms                                               3450ms
   ┌─────┬───────────────────────────────────────────────────┬─────────────────┐
   │ *** │ Comfort Silence / Dead-Air (3200ms)               │ Pink VAD Bursts │
   └─────┴───────────────────────────────────────────────────┴─────────────────┘
     ▲                                                         ▲
     │                                                         │
   AMD Formants (120Hz + 240/360/720Hz)           Jittered Pink Noise (-22 dBFS)
   Tricks dialer into classifying as live human;  Forces LLM VAD into perpetual
   routes call to bot just as silence ends.       barge-in interruption loops.

   Followed by:
   Rapid DTMF Keypress Macro: '9' -> '*' -> '#' -> '0' -> '2' (+2.0 dB twist)
   Triggers automated PBX carrier Do-Not-Call and opt-out macros.


────────────────────────────────────────────────────────────────────────────────
[ 02. REGIONAL PRESET SELECTION MATRIX ]
────────────────────────────────────────────────────────────────────────────────

┌────────────────────────────┬─────────────────────────────┬─────────────────────────────────────────┐
│ Target Region / Market     │ Recommended Preset File     │ Primary Telecom Mechanism               │
├────────────────────────────┼─────────────────────────────┼─────────────────────────────────────────┤
│ United States & Canada     │ US_Canada_Max_Disrupt.wav   │ Bellcore Intercept SIT + Fax CNG + AMD  │
│ US / Canada (Aggressive)   │ US_Canada_Vacant_Drop.wav   │ Bellcore Vacant Code SIT + Fax CNG      │
│ European Union & LatAm     │ EU_India_Brazil_Disconnect  │ ITU-T E.180 SIT + ETSI Congestion + Fax │
│ United Kingdom             │ UK_Disconnect_Fax.wav       │ BT SIN 350 SIT + BT NU 400Hz + Fax CNG │
│ Japan & Asia-Pacific       │ APAC_Japan_Disconnect.wav   │ NTT Busy 400Hz + ITU E.180 SIT + Fax    │
│ Global AI Voice Bot Trap   │ AI_Agent_VAD_Tarpit.wav     │ AMD Spoof + VAD Pink Thrash + DTMF Opt  │
└────────────────────────────┴─────────────────────────────┴─────────────────────────────────────────┘


────────────────────────────────────────────────────────────────────────────────
[ 03. CARRIER VOICEMAIL DIAL-IN & SETUP DIRECTORY ]
────────────────────────────────────────────────────────────────────────────────

To inject a preset greeting, dial your mobile carrier's direct access number,
authenticate with your voicemail PIN, and navigate to personal greeting options:

┌─────────────────────────┬──────────────┬───────────────────────────────────────────┐
│ Carrier / Network       │ Dial-In Code │ Automated Greeting Navigation Sequence    │
├─────────────────────────┼──────────────┼───────────────────────────────────────────┤
│ Verizon Wireless (US)   │ *86          │ PIN -> [4] Options -> [3] Greetings -> [1]│
│ AT&T Mobility (US)      │ Hold [1]     │ PIN -> [4] Options -> [3] Greetings -> [2]│
│ T-Mobile US (US)        │ 123          │ PIN -> [*] -> [4] Options -> [3] -> [1]   │
│ Rogers Wireless (CA)    │ Hold [1]     │ PIN -> [4] Personal Options -> [3] -> [1] │
│ Bell Mobility (CA)      │ *98          │ PIN -> [4] Personal Options -> [3] Record │
│ Telus Mobility (CA)     │ Hold [1]     │ PIN -> [4] Options -> [1] Change Greeting │
│ EE Mobile (UK)          │ 222          │ [2] Greetings -> [1] Change Greeting      │
│ O2 (UK)                 │ 901          │ [*] -> [4] Mailbox -> [3] Greetings -> [1]│
│ Vodafone (UK)           │ 121          │ [4] Personal Settings -> [1] Greetings    │
│ Three (UK)              │ 123          │ [4] Options -> [2] Greetings              │
│ Telekom (Germany)       │ 3311         │ [3] Mailbox Settings -> [1] Greeting Menu │
│ Vodafone (Germany)      │ 5500         │ [2] Options -> [1] Greetings              │
│ Orange (France)         │ 888          │ [2] Personal Greeting -> [1] Record       │
│ Vivo (Brazil)           │ *555         │ Saudacao Personalizada -> Record          │
│ Claro (Brazil)          │ *555         │ Opcoes da Caixa Postal -> Change Greeting │
│ TIM (Brazil)            │ *100         │ [4] Configuracoes -> [2] Saudacao         │
│ Jio / Airtel / Vi (IN)  │ *61*<num>#   │ Forward Unanswered to Voicemail / Screening│
└─────────────────────────┴──────────────┴───────────────────────────────────────────┘

INDIA CARRIER FORWARDING CODES (Jio, Airtel, Vodafone Idea):
  ● Forward When Unanswered : Dial *61*<Voicemail_Number>*11*30#
  ● Forward When Busy       : Dial *67*<Voicemail_Number>#
  ● Forward When Unreachable: Dial *62*<Voicemail_Number>#
  ● Cancel All Forwarding   : Dial ##002#


────────────────────────────────────────────────────────────────────────────────
[ 04. AUDIO INJECTION TECHNIQUES ]
────────────────────────────────────────────────────────────────────────────────

┌──────────────────────────────────────────────────────────────────────────────┐
│ METHOD A: HARDWARE 3.5mm TRRS ATTENUATED PATCH CABLE (LABORATORY FIDELITY)   │
├──────────────────────────────────────────────────────────────────────────────┤
│  PC Headphone Out ──► [ -20 dB Pad ] ──► TRRS Mic Input ──► Smartphone       │
│                                                                              │
│  1. Connect a 3.5mm TRRS breakout adapter to your phone's headphone jack     │
│     (or USB-C / Lightning to 3.5mm dongle).                                  │
│  2. Plug a 3.5mm patch cable from your PC audio output into the adapter's    │
│     microphone jack.                                                         │
│  3. IMPORTANT: Line-out (1.0V) will clip mic preamps (10-50mV). Insert an    │
│     attenuation pad or set PC master volume to 8-10% maximum.                │
│  4. Dial your voicemail access number, trigger recording, and play the WAV.  │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ METHOD B: SOFTPHONE & VIRTUAL AUDIO SINK (PBX / LINPHONE / MICROSIP)         │
├──────────────────────────────────────────────────────────────────────────────┤
│  Linux PipeWire Loopback:                                                    │
│    $ pw-loopback --capture-props='media.class=Audio/Sink' \                  │
│                  --playback-props='media.class=Audio/Source'                 │
│    $ pw-play -d <Sink_ID> release_wavs/US_Canada_Max_Disrupt.wav             │
│                                                                              │
│  Windows / macOS Loopback:                                                   │
│    Install VB-Audio Virtual Cable (Win) or BlackHole (macOS). Set your       │
│    softphone mic input to the virtual device, play the WAV, and record.      │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ METHOD C: ON-DEVICE LIVE VOICEMAIL (APPLE iOS 17+ & GOOGLE ASSISTANT CALL)   │
├──────────────────────────────────────────────────────────────────────────────┤
│  iOS 17+ Live Voicemail:                                                     │
│    Open Phone app -> Voicemail -> Greeting -> Custom -> Record -> Play WAV. │
│    Enables local, on-device SIT injection without contacting carrier PBX.    │
└──────────────────────────────────────────────────────────────────────────────┘


────────────────────────────────────────────────────────────────────────────────
[ 05. CLI COMMAND REFERENCE & PIPELINES ]
────────────────────────────────────────────────────────────────────────────────

Synthesize Arbitrary Module Sequence:
  $ python3 telcotrap.py --sequence na_nanp_ic,fax_cng --output intercept_fax.wav

Prepend Trap Sequence to Voice Recording (Auto-Resamples with 4th-Order LPF):
  $ python3 telcotrap.py --sequence na_nanp_ic --mix-voice my_voice.wav --output greeting.wav

Inspect File Audio Metrics & Run Goertzel Frequency Detection:
  $ python3 telcotrap.py --inspect release_wavs/US_Canada_Max_Disrupt.wav

Rebuild All Production Release Packs:
  $ python3 telcotrap.py --build-release-pack

Stream Directly to ALSA Audio Player (Zero Temporary Files):
  $ python3 telcotrap.py --sequence na_nanp_ic,fax_cng --output - | aplay

AVAILABLE SIGNALING MODULES:
  ● na_nanp_ic         : Bellcore Intercept SIT (913.8, 1370.6, 1776.7 Hz)
  ● na_nanp_nc         : Bellcore No Circuit SIT (985.2, 1370.6, 1776.7 Hz)
  ● na_nanp_vacant     : Bellcore Vacant Code SIT (985.2, 1428.5, 1776.7 Hz)
  ● itu_e180_sit       : ITU-T E.180 Standard SIT (950, 1400, 1800 Hz)
  ● uk_bt_sit          : UK BT SIN 350 Standard SIT (950, 1400, 1800 Hz + silence)
  ● uk_bt_nu           : UK BT Number Unobtainable tone (400 Hz continuous, 2.5s)
  ● eu_etsi_congestion : EU/ETSI Fast Busy Congestion (425 Hz 250ms ON/OFF x6)
  ● jp_ntt_busy        : Japan NTT Howler/Busy tone (400 Hz 500ms ON/OFF x3)
  ● fax_cng            : T.30 Fax Calling Tone (1100 Hz, 500ms ON / 3000ms OFF)
  ● modem_ced          : ITU-T V.25 Answer Tone (2100 Hz with 180° phase reversals)
  ● bell_202_fsk       : Bell 202 CPFSK Data Burst (1200/2200 Hz, 15ms symbols)
  ● amd_spoof          : AMD Formant Speech Spoof (120/240/360/720 Hz + 3.2s silence)
  ● vad_thrash         : AI Voice Agent VAD Jammer (5x jittered pink noise bursts)
  ● dtmf_fuzz          : IVR Opt-Out Sequence ('9', '*', '#', '0', '2' with twist)
  ● comfort_noise      : 300-3000 Hz Band-Limited Comfort Noise (-45 dBFS, 2s)
  ● silence            : Digital Silence Gap (500ms)


────────────────────────────────────────────────────────────────────────────────
[ 06. LEGAL & DEFENSIVE COMPLIANCE NOTICE ]
────────────────────────────────────────────────────────────────────────────────

telcotrap is released under the GPL-3.0-or-later license strictly for lawful,
defensive privacy protection, consumer telecommunications defense, and legitimate
security research against unsolicited, fraudulent, or abusive robocalls.
Users must comply with all local telecommunications laws and carrier terms.
────────────────────────────────────────────────────────────────────────────────
