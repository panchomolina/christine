# Imports
import json
import queue
import sounddevice as sd
import vosk
import sys
import os
import random
import ctypes
import time
import re
import unicodedata
import threading

from datetime import datetime
from tts_gtts import hablar
from comandos import procesar_comando
from voz import hablar_flexible
from PyQt5.QtWidgets import QApplication
from asistente_visual import AsistenteVisual
from PyQt5.QtCore import QTimer, QMetaObject, Qt, Q_ARG, pyqtSlot

# Carga de configuración
try:
    with open("config.json") as f:
        config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    print("⚠️ Error: No se pudo cargar config.json. Verifica el archivo.")
    sys.exit(1)
    
idioma = config.get("idioma", "es")
respuesta_por_voz = config.get("respuesta_por_voz", False)
nombre_asistente_principal = config.get("nombre_asistente", "christine")
nombre_usuario = config.get("nombre_usuario", "")
tratamiento = config.get("tratamiento", "")
alias_asistente = config.get("alias_asistente", [nombre_asistente_principal])
nombre_asistente = alias_asistente 
bloquear_microfono_durante_audio = config.get("bloquear_microfono_durante_audio", True)

# Variables generales
bloquear_escucha = False
samplerate = 16000
q = queue.Queue()
tiempo_espera = 10 


def silenciar_logs_vosk():
    libc = ctypes.CDLL(None)
    devnull = os.open(os.devnull, os.O_WRONLY)
    libc.fflush(None)
    os.dup2(devnull, 2) 
    os.close(devnull)

# Silenciar logs molestos
silenciar_logs_vosk()

# Función callback para entrada de audio
def callback(indata, frames, time, status):
    if status:
        print("Error:", status, file=sys.stderr)
    q.put(bytes(indata))

# Control de micrófono
def silenciar_microfono():
    os.system("pactl set-source-mute @DEFAULT_SOURCE@ 1")

def activar_microfono():
    os.system("pactl set-source-mute @DEFAULT_SOURCE@ 0")

# Crea nombre audio con guion bajo hasta 50 caracteres
def clave_de_audio(texto):
    # Elimina tildes y caracteres especiales
    texto = unicodedata.normalize('NFD', texto)
    texto = texto.encode('ascii', 'ignore').decode('utf-8')

    # Convierte a minúsculas
    texto = texto.lower()

    # Reemplaza caracteres no alfanuméricos por guiones bajos
    texto = re.sub(r'[^a-z0-9]+', '_', texto)

    # Elimina guiones bajos al inicio o fin
    texto = texto.strip('_')

    # Limita la longitud del nombre del archivo (por seguridad)
    return texto[:50]
    
# Función para hablar sin interferencia de audio
def responder_con_voz(mensaje):
    global bloquear_escucha, tiempo_ultimo_comando
    bloquear_escucha = True
    if bloquear_microfono_durante_audio:
        silenciar_microfono()
        
    # Iniciar animación en hilo principal
    QMetaObject.invokeMethod(visor, "iniciar_ecualizador", Qt.QueuedConnection)
    
    # Función para el habla en hilo aparte
    def hablar_hilo():
        hablar_flexible(mensaje, nombre_audio=clave_de_audio(mensaje), idioma=idioma)
        # Cuando termina, detener la animación desde hilo principal
        QMetaObject.invokeMethod(visor, "detener_ecualizador", Qt.QueuedConnection)
        if bloquear_microfono_durante_audio:
            activar_microfono()
        global bloquear_escucha, tiempo_ultimo_comando
        bloquear_escucha = False
        tiempo_ultimo_comando = time.time()
        status_log("activado")
    
    hilo_voz = threading.Thread(target=hablar_hilo)
    hilo_voz.start()
    
# Impresion de estados y logs
def status_log(estado, guardar_en_log=False):
    colores = {
        "reset": "\033[0m",
        "verde": "\033[92m",
        "amarillo": "\033[93m",
        "rojo": "\033[91m",
        "azul": "\033[94m",
        "gris": "\033[90m",
    }

    mensajes = {
        "inicio":       ("✅ Iniciando el sistema.", "INFO"),
        "esperando":    ("🕓 Esperando activación: di el nombre del asistente.", "ESPERA"),
        "activado":     ("🎧 Asistente ACTIVADO: esperando comando.", "ACTIVO"),
        "desactivado":  (f"{nombre_asistente_principal.capitalize()} está en espera...", "ESPERA"),
        "cerrando":     ("💥️ Cerrando el asistente. Hasta pronto.", "FIN"),
    }

    hora = datetime.now().strftime("%H:%M:%S")
    mensaje, tipo = mensajes.get(estado, (f"[Estado desconocido: {estado}]", "??"))

    print(mensaje)

    # ACTUALIZA VISOR SI EXISTE
    if 'visor' in globals():
        if estado == "activado":
            visor.mostrar_texto("🎧 Escuchando...")
            visor.estado = "activo"
            visor.btn_estado.setPixmap(visor.pixmap_brillante)
        elif estado == "desactivado":
            visor.mostrar_texto("🔕 Inactivo...")
            visor.estado = "inactivo"
            visor.btn_estado.setPixmap(visor.pixmap_azul)
        elif estado == "cerrando":
            visor.mostrar_texto("👋 Cerrando...")

    # Guarda en log            
    if guardar_en_log:
        with open("asistente.log", "a", encoding="utf-8") as f:
            f.write(f"[{hora}] ({tipo}) {mensaje}\n")


# Frases de activación
frases_activacion = [
    "Estoy atenta.",
    "¿En qué puedo ayudarte?",
    "Aquí estoy, dime.",
    "Lista para escucharte.",
    "¿Qué necesitas?",
    f"{nombre_asistente_principal.capitalize()} a tu servicio."
]


def limpiar_buffer():
    while not q.empty():
        try:
            q.get_nowait()
        except queue.Empty:
            break
    time.sleep(0.2)
    
def continuar_carga():
    global model, activo, tiempo_ultimo_comando
    visor.mostrar_texto("⏳ Cargando modelo de voz...")

    # Medir el tiempo real de carga del modelo
    start_time = time.time()
    model_path = os.path.join(os.path.dirname(__file__), "modelos_vosk", "vosk-model-es-0.42")
    model = vosk.Model(model_path)

    end_time = time.time()
    tiempo_carga = end_time - start_time

    barra_total = 30
    for i in range(barra_total + 1):
        time.sleep(tiempo_carga / barra_total)
        porcentaje = int((i / barra_total) * 100)
        visor.actualizar_barra(porcentaje)
        QApplication.processEvents()

    visor.mostrar_texto("✅ Modelo cargado.")
    visor.actualizar_barra(100)
    visor.barra_carga.hide()
    
    # Mensaje de inicio
    status_log("inicio")

    # Saludo inicial por voz
    if respuesta_por_voz:
        hablar_flexible("Iniciando el sistema.", nombre_audio="inicio", idioma=idioma)

    activo = True
    tiempo_ultimo_comando = time.time()
    
    limpiar_buffer()
    status_log("activado")

    # Iniciar hilo del asistente
    hilo_asistente = threading.Thread(target=iniciar_asistente, daemon=True)
    hilo_asistente.start()


# Limpieza de buffer y estabilización antes de escuchar
while not q.empty():
    try:
        q.get_nowait()
    except queue.Empty:
        break

time.sleep(0.2)

# Bucle principal
def iniciar_asistente():
    global activo, tiempo_ultimo_comando
    try:
        with sd.RawInputStream(samplerate=samplerate, blocksize=8000,
                               dtype='int16', channels=1, callback=callback):
            rec = vosk.KaldiRecognizer(model, samplerate)

            while True:
                try:
                    data = q.get(timeout=5)
                except queue.Empty:
                    continue

                if rec.AcceptWaveform(data):
                    resultado = rec.Result()
                    texto = json.loads(resultado)["text"].lower()
                    if texto:
                        if bloquear_escucha:
                            continue

                        visor.mostrar_texto(f"👂 {texto}")
        
                        if activo:
                            respuesta, salir = procesar_comando(texto)
                            visor.mostrar_texto(f"🧠 {respuesta}")
                            
                            if respuesta_por_voz:
                                responder_con_voz(respuesta)

                            if respuesta.lower().startswith("no entiendo") or respuesta.lower().startswith("no encontré") or respuesta.lower().startswith("no tengo"):
                                tiempo_ultimo_comando = time.time() 
                            else:
                                tiempo_ultimo_comando = time.time() 

                            if salir == "desactivar":
                                status_log("desactivado")

                            elif salir == "apagar":
                                visor.mostrar_texto("💻 Apagando el sistema...")
                                os.system("shutdown now")
                                QTimer.singleShot(0, visor.close)
                                QTimer.singleShot(0, app.quit)
                                return

                            elif salir == "reiniciar":
                                visor.mostrar_texto("🔄 Reiniciando el sistema...")
                                os.system("reboot")
                                QTimer.singleShot(0, visor.close)
                                QTimer.singleShot(0, app.quit)
                                return

                            elif salir == "bloquear":
                                visor.mostrar_texto("🔒 Bloqueando el sistema...")
                                os.system("cinnamon-screensaver-command -l")

                            elif salir is True:
                                status_log("cerrando")
                                if respuesta_por_voz:
                                    hablar_flexible("Cerrando el asistente. Hasta pronto.", nombre_audio="cerrando_el_asistente_hasta_pronto", idioma=idioma)
                                    QTimer.singleShot(0, visor.close)
                                    QTimer.singleShot(0, app.quit)

                        else:
                            if any(f"{nombre} salir" in texto or
                                   f"{nombre} adiós" in texto or
                                   f"adiós {nombre}" in texto or
                                   f"hasta pronto {nombre}" in texto
                                   for nombre in nombre_asistente) or \
                               "terminar todo" in texto or "cerrar asistente" in texto:
                                status_log("cerrando")
                                if respuesta_por_voz:
                                    hablar_flexible("Cerrando el asistente. Hasta pronto.", nombre_audio="cerrando_el_asistente_hasta_pronto", idioma=idioma)
                                    QTimer.singleShot(0, visor.close)
                                    QTimer.singleShot(0, app.quit)

                            if any(nombre in texto for nombre in nombre_asistente):
                                activo = True
                                tiempo_ultimo_comando = time.time()
                                status_log("activado")
                                respuesta = random.choice(frases_activacion)
                                print("🧠 Respuesta:", respuesta)
                                if respuesta_por_voz:
                                    responder_con_voz(respuesta)

                if activo and (time.time() - tiempo_ultimo_comando > tiempo_espera):
                    activo = False
                    status_log("desactivado")
    
    except KeyboardInterrupt:
        print("\n👋 Saliendo.")
    except Exception as e:
        print("💥 Error:", e)

def cerrar_todo():
    QTimer.singleShot(0, visor.close)
    QTimer.singleShot(0, app.quit)

def manejar_cambio_estado(activo_nuevo):
    global activo
    activo = activo_nuevo
    if activo:
        status_log("activado")
    else:
        status_log("desactivado")

def cerrar_ordenado():
    global activo
    activar_microfono()
    status_log("cerrando")
    if respuesta_por_voz:
        hablar_flexible("Cerrando el asistente. Hasta pronto.", nombre_audio="cerrando_el_asistente_hasta_pronto", idioma=idioma)
    QTimer.singleShot(1000, lambda: visor.close())
    QTimer.singleShot(1000, lambda: app.quit())


# Crear la app y visor visual
app = QApplication(sys.argv)
visor = AsistenteVisual(nombre_asistente_principal)
visor.estado_cambiado.connect(manejar_cambio_estado)
visor.cerrar_signal.connect(cerrar_ordenado)
visor.show()

# Inicializa variables después de visor
tiempo_ultimo_comando = time.time()

# Programar inicio de carga (para que se vea el visor primero)
QTimer.singleShot(200, continuar_carga)

# Iniciar loop Qt (esto debe ir al final)
exit_code = app.exec_()
print("🔚 Qt finalizó, cerrando proceso...")
sys.exit(exit_code)
