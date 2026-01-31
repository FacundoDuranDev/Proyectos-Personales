# ASCII stream a VLC (tiempo real)

Este modulo genera un stream ASCII desde camara y lo envia por UDP para verlo
en VLC. Incluye un modo CLI y control en vivo desde Jupyter.

## Requisitos
- Python 3.8+
- ffmpeg
- Paquetes: opencv-python, pillow, numpy, ipywidgets (para notebook)

Instalacion (ejemplo):
```
python -m pip install opencv-python pillow numpy ipywidgets
```

## Ejecutar local (misma maquina)
```
python -m ascii_stream.streamer --host 127.0.0.1 --port 1234
```

VLC:
```
udp://@127.0.0.1:1234
```

## Broadcast LAN (cualquiera en la red)
```
python -m ascii_stream.streamer --host 255.255.255.255 --port 1234
```

VLC en cualquier equipo:
```
udp://@0.0.0.0:1234
```

## Multicast (alternativa)
```
python -m ascii_stream.streamer --host 239.0.0.1 --port 1234
```

VLC:
```
udp://@239.0.0.1:1234
```

## Control en vivo desde Jupyter
Ejemplo minimo:
```python
from ascii_stream import AsciiStreamer

streamer = AsciiStreamer()
streamer.start()

# Ajustes en vivo
streamer.update_config(contrast=1.6, brightness=10, invert=True)

# Detener
streamer.stop()
```

Ejemplo con sliders (ipywidgets):
```python
import ipywidgets as widgets
from ascii_stream import AsciiStreamer

streamer = AsciiStreamer()
streamer.start()

contrast = widgets.FloatSlider(value=1.2, min=0.5, max=3.0, step=0.1)
brightness = widgets.IntSlider(value=0, min=-50, max=50, step=1)
invert = widgets.Checkbox(value=False)

def on_change(_):
    streamer.update_config(
        contrast=contrast.value,
        brightness=brightness.value,
        invert=invert.value,
    )

for w in [contrast, brightness, invert]:
    w.observe(on_change, names="value")

display(contrast, brightness, invert)
```

Nota: cambios en grid_w/grid_h/host/port/fps requieren reiniciar el stream.
