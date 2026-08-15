APC40 MK2 LED Mapper — versión FINAL para GitHub

Esta versión contiene el último programa v2:
- 45 LEDs RGB.
- Botones con LED controlable por host.
- Estados SOLID / BLINK / OFF.
- Pulsación para alternar SOLID <-> BLINK.
- MIDI IN + MIDI OUT mediante Windows winmm.dll.
- Paleta APC40 MK2.
- Configuración de los LEDs controlables por host.

IMPORTANTE:
El workflow está configurado en modo --console de PyInstaller.
Esto es INTENCIONAL para diagnosticar por qué el EXE anterior no arrancaba.
Al abrir el EXE aparecerá una ventana de consola; si hay un error, se verá ahí.

COMPILAR EN GITHUB:
1. Crea/sube estos archivos a tu repositorio manteniendo .github/workflows/build.yml.
2. Ve a Actions.
3. Selecciona "Build APC40 MK2 LED Mapper".
4. Pulsa Run workflow.
5. Espera el check verde.
6. En la ejecución busca Artifacts.
7. Descarga APC40_MK2_LED_Mapper-Windows-Diagnostic.
8. Extrae el ZIP.
9. Ejecuta APC40_MK2_LED_Mapper.exe.

NO cambies --console por --windowed todavía.
Queremos ver el error real si el programa sigue sin arrancar.
