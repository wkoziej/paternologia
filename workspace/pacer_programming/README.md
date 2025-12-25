# ABOUTME: Workspace dla programowania Nektar Pacer
# ABOUTME: Zawiera źródła i dokumentację do generowania SysEx dla presetów Pacer

# Pacer Programming Workspace

Zasoby do implementacji programowania presetów Nektar Pacer w projekcie Paternologia.

## Struktura

```
workspace/pacer_programming/
├── pacer-editor/           # Sklonowane repo pacer-editor (open source)
│   ├── src/pacer/          # Kluczowe pliki logiki SysEx
│   │   ├── sysex.js        # Parser i generator SysEx (24KB)
│   │   ├── constants.js    # Wszystkie stałe protokołu (24KB)
│   │   ├── model.js        # Model danych
│   │   └── utils.js        # Funkcje pomocnicze
│   ├── dumps/              # Przykładowe dumpy presetów (bin/hex)
│   │   ├── README.md       # Dokumentacja formatu wiadomości
│   │   └── read-preset.md  # Szczegółowy format odczytu presetów
│   ├── sysex.md            # Dokumentacja protokołu SysEx
│   ├── data_structure.md   # Struktura danych
│   └── dump_format.md      # Format elementów (kolory, LED, etc.)
└── nektar_presets/         # (do pobrania) Oficjalne presety od Nektar
```

## Kluczowe informacje techniczne

### Identyfikator producenta (Manufacturer ID)
```
00 01 77  = Nektar Technology Inc
```

### Struktura wiadomości SysEx
```
F0 <header> <cmd> <tgt> <idx> <obj> <elm> <data> <cs> F7

F0          = Start SysEx
00 01 77    = Manufacturer ID (Nektar)
7F          = Custom header
<cmd>       = 01=Set, 02=Get
<tgt>       = 01=Preset, 05=Global, 7F=Full Backup
<idx>       = Indeks presetu (00-17 dla 1A-6D)
<obj>       = Kontrolka (0D-12=SW1-6, 14-17=SW A-D, etc.)
<elm>       = Element (01-24=kroki, 40-57=LED, 60=tryb)
<data>      = Dane
<cs>        = Checksum: (128 - (sum % 128)) % 128
F7          = End SysEx
```

### Mapowanie presetów
```
0x00=1A  0x01=2A  0x02=3A  0x03=4A  0x04=5A  0x05=6A
0x06=1B  0x07=2B  0x08=3B  0x09=4B  0x0A=5B  0x0B=6B
0x0C=1C  0x0D=2C  0x0E=3C  0x0F=4C  0x10=5C  0x11=6C
0x12=1D  0x13=2D  0x14=3D  0x15=4D  0x16=5D  0x17=6D
```

### Mapowanie kontrolek (obj)
```
0x0D=Stompswitch 1    0x14=Stompswitch A
0x0E=Stompswitch 2    0x15=Stompswitch B
0x0F=Stompswitch 3    0x16=Stompswitch C
0x10=Stompswitch 4    0x17=Stompswitch D
0x11=Stompswitch 5    0x18-0x1B=Footswitch 1-4
0x12=Stompswitch 6    0x36-0x37=Expression Pedal 1-2
0x01=Nazwa presetu    0x7E=MIDI config
```

### Typy wiadomości MIDI (msg_type dla stompswitchów)
```
0x40=CC Trigger       0x45=Program & Bank
0x47=CC Toggle        0x46=Program Step
0x48=CC Step          0x55=MMC
0x43=Note             0x59=Relay
0x44=Note Toggle      0x62=Preset Select
0x61=OFF
```

### Kolory LED
```
0x00=Off     0x03=Red      0x09=Yellow   0x0D=Green
0x11=Blue    0x15=Purple   0x17=White
(parzyste = pełna jasność, nieparzyste = dim)
```

## Narzędzia pomocnicze

### Wysyłanie SysEx (Linux)
```bash
# Instalacja sendmidi
sudo apt install sendmidi

# Odczyt presetu B1 (0x07)
sendmidi dev MIDI1 syx hex 00 01 77 7F 02 01 07 7F 77

# Odczyt wszystkich presetów
sendmidi dev MIDI1 syx hex 00 01 77 7F 02 01 7F 7E

# Full backup
sendmidi dev MIDI1 syx hex 00 01 77 7F 02 7F
```

### Konwersja hex ↔ bin
```bash
# Hex (tekstowy) → Binary
xxd -r -p input.hex > output.bin

# Binary → Hex (tekstowy)
xxd -g1 input.bin > output.hex
```

## Licencja

pacer-editor: GPL v3
Nektar, Pacer: Znaki towarowe Nektar Technology, Inc.
