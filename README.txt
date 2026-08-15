# APC40 MK2 LED Mapper v2

Programa Windows para controlar los LEDs de una Akai APC40 MK2.

## Estados
Solo hay tres estados:
- Solid: encendido fijo.
- Blink: parpadeo.
- Off: apagado.

Comportamiento al pulsar un botón configurado:
- Solid -> Blink
- Blink -> Solid
- Off -> Solid

La versión v2 incluye todos los botones con LED que el protocolo de APC40 MK2 permite controlar:
- 40 Clip Launch RGB
- 5 Scene Launch RGB
- Record Arm, Solo, Activator, Track Select y Clip Stop de las 8 pistas
- Crossfade A/B de las 8 pistas
- Device Left/Right, Bank Left/Right, Device On/Off, Device Lock, Clip/Device View, Detail View
- Master, Pan, Sends, User, Metronome, Play, Record y Session Record

Los botones que el protocolo define sin LED controlable (por ejemplo flechas, Shift, Tap Tempo, Nudge y Stop All Clips) no se incluyen porque no hay un estado LED que el host pueda escribir según el protocolo.

Los 45 controles RGB permiten seleccionar colores de la paleta APC40. Los demás botones tienen LED monocromo; para ellos el modo Blink se simula desde el programa.

## Compilación online
El workflow `.github/workflows/main.yml` compila automáticamente el EXE en Windows con Python 3.12 y PyInstaller.
