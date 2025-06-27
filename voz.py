import os
from tts_gtts import hablar, reproducir_audio

def hablar_flexible(texto, nombre_audio=None, idioma="es"):
    """
    Usa un archivo pregrabado si existe. Si no, usa la función hablar() de tts_gtts.
    """
    if nombre_audio:
        ruta = f"audios/{nombre_audio}.mp3"
        if os.path.exists(ruta):
            reproducir_audio(ruta)
            return
    # Si no hay audio pregrabado, usar la lógica existente
    hablar(texto, idioma)
