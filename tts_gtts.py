import os
import subprocess
import time
import socket
import tempfile
from gtts import gTTS
from mutagen.mp3 import MP3

# Verifica si hay conexión a Internet
def hay_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
        return True
    except Exception:
        return False

# Verifica si las dependencias están instaladas
def verificar_dependencias():
    for cmd in ["mpg123", "pico2wave"]:
        if subprocess.call(f"which {cmd}", shell=True, stdout=subprocess.DEVNULL) != 0:
            print(f"⚠️ Falta el comando '{cmd}'. Algunas funciones podrían no funcionar correctamente.")

verificar_dependencias()

# Usa gTTS para hablar
def hablar_gtts(texto, idioma="es"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        archivo_audio = tmp.name

    tts = gTTS(text=texto, lang=idioma)
    tts.save(archivo_audio)

    try:
        duracion = MP3(archivo_audio).info.length
    except Exception:
        duracion = 1

    subprocess.run(["mpg123", archivo_audio])
    os.remove(archivo_audio)
    #time.sleep(duracion + 0.3)

# Usa pico2wave (offline) para hablar
def hablar_pico2wave(texto):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav:
        archivo_wav = wav.name
    archivo_mp3 = archivo_wav.replace(".wav", ".mp3")

    cmd = ['pico2wave', '--lang=es-ES', '--wave', archivo_wav, texto]
    resultado = subprocess.run(cmd, capture_output=True)

    if resultado.returncode != 0:
        print("❌ Error generando audio con pico2wave.")
        return

    # Intenta convertir a mp3 si está disponible ffmpeg
    cmd_ffmpeg = ["ffmpeg", "-y", "-i", archivo_wav, archivo_mp3]
    conversion = subprocess.run(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if conversion.returncode == 0:
        subprocess.run(["mpg123", "-q", archivo_mp3], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(archivo_mp3)
    else:
        # Si no hay ffmpeg, reproduce el wav directamente
        subprocess.run(["aplay", archivo_wav])

    os.remove(archivo_wav)

# Elige la mejor opción disponible y habla
def hablar(texto, idioma="es"):
    if hay_internet():
        try:
            hablar_gtts(texto, idioma)
        except Exception as e:
            print(f"🌐 Error con gTTS: {e}. Usando pico2wave.")
            hablar_pico2wave(texto)
    else:
        hablar_pico2wave(texto)

# Reproduce audio
def reproducir_audio(archivo):
    # Usa mpg123 para reproducir mp3 (o cambia por tu reproductor favorito)
    subprocess.run(["mpg123", archivo])
