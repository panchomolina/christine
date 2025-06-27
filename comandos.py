# comandos.py
import json
import subprocess
import difflib
import random
import requests
import feedparser
import wikipedia
import os
import psutil
import webbrowser
import tempfile
import unicodedata
from datetime import datetime, timedelta
from sympy import sympify
from sympy.core.sympify import SympifyError
from tts_gtts import reproducir_audio
from memoria import cache, limpiar_respuesta, guardar_en_cache
from bs4 import BeautifulSoup
from tts_gtts import hablar
from urllib.parse import quote

# Cargar configuración general
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

nombre_asistente_principal = config.get("nombre_asistente", "christine")
nombre_usuario = config.get("nombre_usuario", "")
tratamiento = config.get("tratamiento", "")
alias_asistente = config.get("alias_asistente", [nombre_asistente_principal])
nombre_asistente = alias_asistente 
latitud = config.get("ubicacion", {}).get("lat", -33.0510765)
longitud = config.get("ubicacion", {}).get("lon", -71.6222547)
max_noticias = config.get("noticias_max", 5)
idioma = config.get("idioma", "es")

# Configura el idioma en español
wikipedia.set_lang("es")

# Diccionario plataformas de busqueda
PLATAFORMAS_BUSQUEDA = {
    "google": "https://www.google.com/search?q={}",
    "youtube": "https://www.youtube.com/results?search_query={}",
    "facebook": "https://www.facebook.com/search/top/?q={}",
    "twitter": "https://twitter.com/search?q={}",
    "wikipedia": "https://es.wikipedia.org/wiki/Especial:Buscar?search={}",
    "pinterest": "https://www.pinterest.com/search/pins/?q={}"
}

#########################################################
##                     FUNCIONES                       ##
#########################################################      

# Busca en wikipedia
def buscar_en_wikipedia(texto):
    try:
        resultados = wikipedia.search(texto)
        if not resultados:
            return "No encontré resultados en Wikipedia."
        
        # Toma el primer resultado
        pagina = wikipedia.page(resultados[0])
        resumen = wikipedia.summary(pagina.title, sentences=2)
        return resumen
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Tu consulta es ambigua. Prueba ser más específico. Ejemplos: {', '.join(e.options[:3])}."
    except Exception:
        return "Ocurrió un error al buscar la información."
        
        
def cargar_json(archivo, encoding="utf-8"):
    try:
        with open(archivo, "r", encoding=encoding) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Archivo no encontrado: {archivo}")
    except json.JSONDecodeError:
        print(f"⚠️ Error al interpretar JSON: {archivo}")
    return {}


# Pasa de texto a signo matematico
def texto_a_expresion(expr):
    reemplazos = {
        "más": "+",
        "menos": "-",
        "por": "*",
        "entre": "/",
        "dividido": "/",
        "elevado a": "**",
    }

    for palabra, simbolo in reemplazos.items():
        expr = expr.replace(palabra, simbolo)

    return expr


# Reemplaza el nombre de un numero a numero ademas de los signos matematicos.   
def reemplazar_numeros_conocidos(expr):
    palabras = expr.split()
    resultado = []

    for palabra in palabras:
        resultado.append(mapa_numeros.get(palabra, palabra))

    return " ".join(resultado)

# Dice el clima de mi ciudad
def obtener_clima(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode&timezone=auto"
    try:
        response = requests.get(url)
        data = response.json()

        temp = data["current"]["temperature_2m"]
        codigo = data["current"]["weathercode"]

        condiciones = {
            0: "despejado",
            1: "mayormente despejado",
            2: "parcialmente nublado",
            3: "nublado",
            45: "niebla",
            48: "niebla con escarcha",
            51: "llovizna ligera",
            53: "llovizna moderada",
            55: "llovizna intensa",
            61: "lluvia ligera",
            63: "lluvia moderada",
            65: "lluvia fuerte",
            71: "nieve ligera",
            73: "nieve moderada",
            75: "nieve intensa",
            80: "chubascos ligeros",
            81: "chubascos moderados",
            82: "chubascos fuertes"
        }

        estado = condiciones.get(codigo, "condición desconocida")
        return f"La temperatura actual es de {int(temp)} grados con cielo {estado}."

    except Exception as e:
        return "No pude obtener el clima en este momento."
        
        
# Obtener noticias de feed 
def obtener_noticias(limit=5):
    url = config.get("url_noticias", "https://www.cooperativa.cl/noticias/site/tax/port/all/rss_3___1.xml")
    try:
        feed = feedparser.parse(url)
        noticias = []

        for entry in feed.entries[:limit]:
            noticias.append(f"- {entry.title}")

        if noticias:
            return "Aquí tienes las noticias más recientes:\n" + "\n".join(noticias)
        else:
            return "No encontré noticias nuevas por ahora."
    except Exception:
        return "Ocurrió un error al obtener las noticias."

# Significado de palabras desde wordreference
def obtener_significado(palabra):
    palabra = palabra.lower()

    # Revisar si ya está guardado
    if palabra in significados_cache:
        return f"(Desde caché)\n{significados_cache[palabra]}"

    url = f"https://www.wordreference.com/definicion/{palabra}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return f"No pude obtener el significado de '{palabra}'."

        soup = BeautifulSoup(response.text, 'html.parser')

        definicion_div = soup.find("ol", class_="entry")
        if not definicion_div:
            return f"No encontré el significado de '{palabra}'."

        parrafos = definicion_div.find_all("li")
        definiciones = [p.get_text(strip=True) for p in parrafos if len(p.get_text(strip=True)) > 0]

        if not definiciones:
            return f"No hay una definición clara para '{palabra}'."

        resultado = f"El significado de '{palabra}' es:\n- " + "\n- ".join(definiciones[:3])

        # Guardar en caché
        significados_cache[palabra] = resultado
        with open(archivo_significados, "w", encoding="utf-8") as f:
            json.dump(significados_cache, f, indent=2, ensure_ascii=False)

        return resultado

    except Exception:
        return "Ocurrió un error al buscar el significado."

# Saludo segun horario
def obtener_saludo_correcto():
    hora = datetime.now().hour
    if hora < 12:
        return "buenos días"
    elif hora < 20:
        return "buenas tardes"
    else:
        return "buenas noches"
        
# Estado del equipo        
def obtener_estado_equipo():
    # CPU
    cpu = psutil.cpu_percent(interval=1)

    # RAM (%)
    ram = psutil.virtual_memory()
    ram_pct = ram.percent

    # Disco (% en raíz)
    disco = psutil.disk_usage('/')
    disco_pct = disco.percent

    # Temperatura
    temperatura = "No se detectó temperatura."

    try:
        temps = psutil.sensors_temperatures()
        if temps:
            # Buscar temperatura del CPU (comúnmente 'coretemp' o similar)
            for nombre_sensor, lecturas in temps.items():
                for entry in lecturas:
                    if "cpu" in entry.label.lower() or "package" in entry.label.lower():
                        temperatura = f"{entry.current:.1f} °C (CPU)"
                        raise StopIteration
            # Si no se encontró ninguna etiqueta útil, usar la primera
            for lecturas in temps.values():
                if lecturas:
                    temperatura = f"{lecturas[0].current:.1f} °C (sensor general)"
                    break
        else:
            # Alternativa con comando 'sensors'
            salida = subprocess.check_output(["sensors"]).decode()
            for linea in salida.splitlines():
                if "Core 0" in linea or "Tctl" in linea:
                    partes = linea.split()
                    for parte in partes:
                        if "°C" in parte or parte.endswith("C"):
                            temperatura = parte + " (desde sensors)"
                            break
    except Exception:
        temperatura = "No se pudo obtener temperatura del sistema."

    # Resumen final
    estado = (
        f"Estado actual del equipo:\n"
        f"- CPU: {cpu:.0f}% de uso\n"
        f"- RAM: {ram_pct:.0f}% usada\n"
        f"- Disco: {disco_pct:.0f}% usado\n"
        f"- Temperatura: {temperatura}"
    )

    return estado

# Lee texto seleccionado    
def obtener_texto_seleccionado():
    try:
        texto = subprocess.check_output(["xclip", "-selection", "primary", "-o"]).decode().strip()
        return texto if texto else "No encontré texto seleccionado."
    except Exception:
        return "No se pudo obtener el texto seleccionado."
        
# Buscar en google, youtube, facebook y otros        
def interpretar_busqueda(texto):
    texto = texto.lower()

    # Buscar plataforma
    for plataforma in PLATAFORMAS_BUSQUEDA:
        if f" en {plataforma}" in texto:
            consulta = texto.split(f" en {plataforma}")[0]
            consulta = consulta.replace("buscar ", "").replace("busca ", "").strip()
            url = PLATAFORMAS_BUSQUEDA[plataforma].format(consulta.replace(" ", "+"))
            return f"Buscando '{consulta}' en {plataforma.title()}.", url

    # Si no se especificó plataforma → usar Google por defecto
    consulta = texto.replace("buscar ", "").replace("busca ", "").strip()
    url = PLATAFORMAS_BUSQUEDA["google"].format(consulta.replace(" ", "+"))
    return f"Buscando '{consulta}' en Google.", url

# Quita tildes y cambia a minusculas
def normalizar(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower()
    
# Búsqueda recursiva
def buscar_archivo_o_carpeta(nombre, tipo="archivo", extension=None):
    resultados = []
    puntos_montaje = ["/", "/media", "/mnt", os.path.expanduser("~")]
    nombre = normalizar(nombre) # Normalizamos antes

    for raiz in puntos_montaje:
        for directorio_actual, subdirs, archivos in os.walk(raiz):
            try:
                if tipo == "archivo":
                    for archivo in archivos:
                        if nombre in normalizar(archivo):  # nombre es parte del archivo
                            if extension is None or normalizar(archivo).endswith(extension):
                                resultados.append(os.path.join(directorio_actual, archivo))
                elif tipo == "carpeta":
                    for subdir in subdirs:
                        if nombre in normalizar(subdir):
                            resultados.append(os.path.join(directorio_actual, subdir))
            except PermissionError:
                continue  # Saltar carpetas sin acceso
            except Exception as e:
                print(f"⚠️ Error en {directorio_actual}: {e}")
                continue

    return resultados if resultados else None

        
# Muestra resultados en html
def mostrar_resultados_en_html(resultados, nombre, tipo):
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Resultados de búsqueda</title>
        <style>
            body {{ font-family: sans-serif; margin: 2em; }}
            h2 {{ color: #333; }}
            a {{ display: block; margin: 0.5em 0; color: #0066cc; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <h2>{tipo.capitalize()}s encontrados con nombre: <em>{nombre}</em></h2>
        {"".join([f"<a href='file://{ruta}' target='_blank'>{ruta}</a>" for ruta in resultados])}
    </body>
    </html>
    """

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
        f.write(html)
        archivo_html = f.name

    webbrowser.open(f"file://{archivo_html}")
    
# Muestra resultados en terminal
def mostrar_resultados_en_terminal(resultados, nombre, tipo):
    print(f"\n📄 {tipo.capitalize()}s encontrados con el nombre '{nombre}':\n")
    for ruta in resultados:
        ruta_escapada = quote(ruta)  # convierte espacios y caracteres especiales
        print(f"🔗 \"file://{ruta_escapada}\"")
    print("\nPuedes hacer clic en la ruta para abrir el archivo.\n")
    
RUTA_CACHE = "busqueda_equipo.json"

def cargar_busquedas_cache():
    if not os.path.exists(RUTA_CACHE):
        return {}
    with open(RUTA_CACHE, "r", encoding="utf-8") as f:
        datos = json.load(f)

    # Limpieza automática (ej: después de 7 días)
    hoy = datetime.now()
    expiracion = timedelta(days=7)
    limpiar = False

    claves_a_borrar = []
    for clave, info in datos.items():
        try:
            fecha = datetime.fromisoformat(info["fecha"])
            if hoy - fecha > expiracion:
                claves_a_borrar.append(clave)
        except Exception:
            claves_a_borrar.append(clave)

    for clave in claves_a_borrar:
        del datos[clave]
        limpiar = True

    if limpiar:
        guardar_busquedas_cache(datos)

    return datos

def guardar_busquedas_cache(cache):
    with open(RUTA_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def buscar_en_cache(nombre, tipo):
    cache = cargar_busquedas_cache()
    if nombre in cache:
        rutas_validas = [ruta for ruta in cache[nombre]["rutas"] if os.path.exists(ruta)]
        return rutas_validas if rutas_validas else None
    return None

def actualizar_cache(nombre, rutas):
    cache = cargar_busquedas_cache()
    cache[nombre] = {
        "rutas": rutas,
        "fecha": datetime.now().isoformat()
    }
    guardar_busquedas_cache(cache)

# Comandos basicos sistema    
ventana_minimizada_id = None  # Asegúrate de que esté fuera de la función

def ejecutar_comando_sistema(accion):
    global ventana_minimizada_id

    try:
        if accion == "minimizar":
            result = subprocess.run(["xdotool", "getactivewindow"], capture_output=True, text=True)
            ventana_minimizada_id = result.stdout.strip()
            subprocess.run(["xdotool", "windowminimize", ventana_minimizada_id])
            return "Listo.", False

        elif accion == "maximizar":
            if ventana_minimizada_id:
                subprocess.run(["xdotool", "windowsize", ventana_minimizada_id, "100%", "100%"])
                subprocess.run(["xdotool", "windowactivate", ventana_minimizada_id])
                return "Listo.", False
            else:
                return "No recuerdo qué ventana minimizar.", False

        elif accion == "cerrar_ventana":
            subprocess.run(["xdotool", "getactivewindow", "windowclose"])
            return "Listo.", False

        elif accion == "cambiar_ventana":
            subprocess.run(["xdotool", "key", "Alt+Tab"])
            return "Listo.", False

        comandos = {
            "mostrar_escritorio": ["xdotool", "key", "Super+d"],
            "copiar": ["xdotool", "key", "ctrl+c"],
            "pegar": ["xdotool", "key", "ctrl+v"],
            "cortar": ["xdotool", "key", "ctrl+x"],
            "escape": ["xdotool", "key", "Escape"]
        }

        if accion in comandos:
            subprocess.run(comandos[accion])
            return "Listo.", False
        else:
            return f"No reconozco el comando '{accion}'.", False

    except Exception as e:
        return f"Ocurrió un error al ejecutar el comando '{accion}': {e}", False

# Control volume
def controlar_volumen(accion):
    try:
        if accion == "subir":
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"])
            return "Listo.", False

        elif accion == "bajar":
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"])
            return "Listo.", False

        elif accion == "silenciar":
            subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"])
            return "Listo.", False

        elif accion == "activar":
            subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"])
            return "Listo.", False

        else:
            return "No reconozco el comando de volumen.", False
    except Exception as e:
        return f"Error al controlar el volumen: {e}", False

# Control brillo
def controlar_brilho(accion):
    try:
        if accion == "subir":
            subprocess.run(["brightnessctl", "set", "+10%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Listo.", False

        elif accion == "bajar":
            subprocess.run(["brightnessctl", "set", "10%-"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Listo.", False

        else:
            return "No entendí si quieres subir o bajar el brillo.", False
    except Exception as e:
        return f"Ocurrió un error al controlar el brillo: {e}", False
        
        
        
            
#########################################################
##                DICCIONARIOS JSON                    ##
######################################################### 
# Archivo de significados
archivo_significados = "significados.json"
# Diccionarios de programas y paginas
programas_disponibles = cargar_json("programas.json")
paginas_web = cargar_json("paginas.json")
# Diccionario de capitales de paises
capitales = cargar_json("capitales.json")
# Diccionario respuestas conversacionales
respuestas = cargar_json("respuestas.json")
# Archivo con los numeros de texto (nombre) a numero
mapa_numeros = cargar_json("numeros.json")

# Cargar los significados existentes
if os.path.exists(archivo_significados):
    with open(archivo_significados, "r", encoding="utf-8") as f:
        significados_cache = json.load(f)
else:
    significados_cache = {}
                     
        


#########################################################
##                      COMANDOS                       ##
#########################################################        

# Procesa los comandos
def procesar_comando(texto):
   
    # convierte cualquier lista en una cadena legible, antes de seguir
    if isinstance(texto, list):
        texto = " ".join(str(palabra) for palabra in texto)
    texto = texto.lower()

    # Busca si alguna clave en respuestas está en el texto y devuelve una respuesta aleatoria
    for clave in respuestas:
        if clave in texto:
            return random.choice(respuestas[clave]), False

    # Comando de fecha y hora
    if any(frase in texto for frase in ["fecha y hora", "fecha hora", "dime la fecha y hora"]):
        fecha_hora_actual = datetime.now().strftime("%d/%m/%Y a las %H:%M")
        return f"Hoy es {fecha_hora_actual}.", False
        
    # Comando de hora
    elif any(frase in texto for frase in ["qué hora es", "hora", "dime la hora", "la hora"]):
        hora_actual = datetime.now().strftime("%H:%M")
        return f"La hora actual es {hora_actual}.", False

    # Comando de fecha
    elif any(frase in texto for frase in ["qué fecha es", "fecha", "la fecha", "qué dia es hoy", "dia", "el dia", "cual es la fecha", "cual es el dia", "dime la fecha", "dame la fecha"]):
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        return f"La fecha de hoy es {fecha_actual}.", False

    # Búsqueda recursiva
    elif any(f in texto for f in [
        "buscar en el equipo", "buscar en el pc", "buscar en el sistema", "buscar en el disco",
        "busca en el equipo", "busca en el pc", "busca en el sistema", "busca en el disco", 
        "buscar archivo", "buscar carpeta", "busca el archivo", "busca la carpeta"
    ]):
        tipo = "archivo" if "archivo" in texto else "carpeta" if "carpeta" in texto else "archivo"
        palabra_clave = "archivo" if tipo == "archivo" else "carpeta"
        nombre = texto.split(palabra_clave)[-1].strip()

        # 🔍 DETECTAR EXTENSIÓN SI HAY
        extensiones_validas = {
            "pdf": ".pdf",
            "doc": ".doc",
            "docx": ".docx",
            "word": ".docx",
            "texto": ".txt",
            "txt": ".txt",
            "excel": ".xlsx",
            "ppt": ".pptx",
            "powerpoint": ".pptx"
        }
        extension = None
        for clave, ext in extensiones_validas.items():
            if clave in texto.lower():
                extension = ext
                break
        
        if extension:
            palabra_extension = extension.replace(".", "")
            if nombre.lower().endswith(palabra_extension):
                nombre = nombre[: -len(palabra_extension)].strip()
            elif nombre.lower().endswith(extension):
                nombre = nombre[: -len(extension)].strip()

    
        # Buscar en caché primero
        resultados = buscar_en_cache(nombre, tipo)
        if resultados:
            if len(resultados) == 1:
                os.system(f"xdg-open '{resultados[0]}'")
                return f"Abrí {tipo} '{nombre}' desde el historial.", False
            else:
                mostrar_resultados_en_terminal(resultados, nombre, tipo)
                return f"Mostré los resultados de '{nombre}' desde el historial.", False

        # Aviso por voz
        hablar(f"Buscaré {tipo} '{nombre}' en todo el equipo. Esto puede tardar algunos segundos o minutos.", idioma=idioma)

        # Aviso visual
        print("🔍 Buscando en el sistema, esto puede tardar un poco...")

        # Búsqueda completa
        resultados = buscar_archivo_o_carpeta(nombre, tipo=tipo, extension=extension)

        if resultados:
            actualizar_cache(nombre, resultados)
            if len(resultados) == 1:
                os.system(f"xdg-open '{resultados[0]}'")
                return f"Abrí el {tipo} '{nombre}'.", False
            else:
                mostrar_resultados_en_terminal(resultados, nombre, tipo)
                return f"Encontré varios resultados para '{nombre}'. Los mostré en la terminal.", False
        else:
            return f"No encontré {tipo} '{nombre}' en el equipo.", False



            
    # Comando para cerrar asistente y despedida
    elif any(frase in texto for frase in ["salir del asistente", "terminar todo", "cerrar asistente"]):
        return "Cerrando el asistente. Hasta pronto.", True

    # Comando para abrir programas o páginas con múltiples frases posibles
    elif any(texto.startswith(frase) for frase in [
        "abrir ", "abre ", "inicia ", "iniciar ", "ejecuta ", "ejecutar ",
        "lanza ", "lanzar ", "ve a ", "quiero abrir ", "quiero ir a ", "quiero iniciar "
    ]):

        frases_abrir = [
            "abrir ", "abre ", "inicia ", "iniciar ", "ejecuta ", "ejecutar ",
            "lanza ", "lanzar ", "ve a ", "quiero abrir ", "quiero ir a ", "quiero iniciar "
        ]

        objetivo = texto
        for frase in frases_abrir:
            if texto.startswith(frase):
                objetivo = texto.replace(frase, "", 1).strip()
                break

        # Función para encontrar mejor coincidencia en un diccionario
        def encontrar_objeto(objetivo, diccionario):
            # 1. Búsqueda exacta
            if objetivo in diccionario:
                return objetivo

            # 2. Búsqueda aproximada con difflib
            keys = diccionario.keys()
            matches = difflib.get_close_matches(objetivo, keys, n=1, cutoff=0.6)
            if matches:
                return matches[0]

            # 3. Búsqueda por subcadena
            for key in keys:
                if key in objetivo:
                    return key

            return None

        # Buscar en programas
        programa = encontrar_objeto(objetivo, programas_disponibles)
        if programa:
            comando = programas_disponibles[programa]
            try:
                subprocess.Popen([comando])
                return f"Abriendo {objetivo}.", False
            except Exception:
                return f"No se pudo abrir el programa '{programa}'.", False

        # Buscar en páginas web
        pagina = encontrar_objeto(objetivo, paginas_web)
        if pagina:
            url = paginas_web[pagina]
            try:
                subprocess.Popen(["xdg-open", url])
                return f"Abriendo la página de {objetivo}.", False
            except Exception:
                return f"No se pudo abrir la página '{pagina}'.", False

        return f"No tengo registrado cómo abrir '{objetivo}'.", False

    # Cálculos seguros primero
    elif any(frase in texto for frase in ["calcula", "calcular"]):
        expr = texto.replace("calcula ", "", 1).replace("calcular ", "", 1).strip()
        expr = texto_a_expresion(expr)
        expr = reemplazar_numeros_conocidos(expr)

        try:
            resultado = float(sympify(expr).evalf())
            if resultado.is_integer():
                resultado = int(resultado)

            return f"El resultado es {resultado}", False
        except SympifyError:
            return "No entendí la expresión matemática.", False
        except Exception:
            return "Ocurrió un error al calcular.", False


    # Búsqueda en internet o plataformas
    elif any(f in texto for f in ["busca", "buscar"]):
        mensaje, url = interpretar_busqueda(texto)
        if not url:
            return "No entendí qué deseas buscar.", False

        subprocess.Popen(["xdg-open", url])
        return mensaje, False

        
    # Comando para decir el tiempo
    elif any(frase in texto for frase in ["clima", "tiempo"]):
        clima = obtener_clima(latitud, longitud)
        return clima, False

    # Comando para ver el rss de noticias
    elif any(frase in texto for frase in ["noticias", "novedades", "qué hay de nuevo"]):
        reproducir_audio("audios/buscando_noticias.mp3")
        noticias = obtener_noticias(limit=max_noticias)
        return noticias, False

    # Búsqueda informativa en wikipedia tipo "qué es...", "quién es...", etc.
    elif any(frase in texto for frase in ["qué es ", "quién es ", "háblame de ", "define "]):
        reproducir_audio("audios/consultando_wikipedia.mp3")
        pregunta = texto
        
        if pregunta in cache:
            return cache[pregunta], False
        
        try:
            wikipedia.set_lang("es")
            resumen = wikipedia.summary(pregunta, sentences=2)
            resumen_limpio = limpiar_respuesta(resumen)
            guardar_en_cache(pregunta, resumen_limpio)
            return resumen_limpio, False
        except Exception:
            return "No encontré una respuesta clara para eso.", False

    # Pregunta sobre capitales de países
    elif any(frase in texto for frase in ["cuál es la capital de", "cual es la capital de"]):
        pais = texto.replace("cuál es la capital de", "").replace("cual es la capital de", "").strip()
        if pais in capitales:
            return f"La capital de {pais.title()} es {capitales[pais]}.", False
        else:
            return f"No tengo registrada la capital de {pais}.", False


    # Buscar significado
    elif any(frase in texto for frase in ["qué significa", "cual es el significado de", "cuál es el significado de", "dime el significado de"]):
        for frase in ["qué significa", "cual es el significado de", "cuál es el significado de", "dime el significado de"]:
            if frase in texto:
                palabra = texto.split(frase)[-1].strip()
                break
        if palabra:
            significado = obtener_significado(palabra)
            return significado, False
        else:
            return "¿Qué palabra quieres que defina?", False

    # Comando de saludos
    elif any(palabra in texto for palabra in [
        "hola", "buenos días", "buenas tardes", "buenas noches",
        "qué tal", "saludos", "hey", "buen día"
    ]):
        saludo_real = obtener_saludo_correcto()

        # Detectar cuál saludo usó el usuario (si es uno "clásico")
        saludos_detectados = ["buenos días", "buenas tardes", "buenas noches"]
        saludo_usuario = next((s for s in saludos_detectados if s in texto), None)

        saludo_personal = f"{saludo_real.capitalize()}, {tratamiento or nombre_usuario}."

        if saludo_usuario == saludo_real:
            return f"{saludo_personal} Soy {nombre_asistente_principal}, a tu servicio.", False
        else:
            return f"{saludo_personal} Aunque ahora no es momento de decir '{saludo_usuario}', jejeje. Soy {nombre_asistente_principal}, a tu servicio.", False

    # Responde el nombre del asistente
    elif any(pregunta in texto for pregunta in [
        "cómo te llamas", "como te llamas", "cuál es tu nombre", "cual es tu nombre",
        "dime tu nombre", "quién eres", "quien eres", "tu nombre"
    ]):
        respuesta = f"Mi nombre es {nombre_asistente_principal}. Soy el asistente virtual de {nombre_usuario or 'mi creador'}."
        return respuesta, False

    # Estado del equipo
    elif any(frase in texto for frase in [
        "cómo está el equipo", "dime el estado del equipo", "estado del equipo", "cuál es tu estado", "estado del sistema"
    ]):
        respuesta = obtener_estado_equipo()
        return respuesta, False

    # Leer texto seleccionado
    elif any(frase in texto for frase in [
        "lee el texto seleccionado", "leer texto seleccionado", "leer lo que seleccioné", "leer lo marcado"
    ]):
        texto_seleccionado = obtener_texto_seleccionado()
        return texto_seleccionado, False

    # Llamada a comandos basicos
    elif any(f in texto for f in ["minimiza", "minimizar ventana"]):
        return ejecutar_comando_sistema("minimizar")

    elif any(f in texto for f in ["maximiza", "maximizar ventana"]):
        return ejecutar_comando_sistema("maximizar")

    elif any(f in texto for f in ["mostrar escritorio", "ver escritorio"]):
        return ejecutar_comando_sistema("mostrar_escritorio")

    elif "copiar" in texto:
        return ejecutar_comando_sistema("copiar")

    elif "pegar" in texto:
        return ejecutar_comando_sistema("pegar")

    elif "cortar" in texto:
        return ejecutar_comando_sistema("cortar")

    elif "escape" in texto or "escapar" in texto:
        return ejecutar_comando_sistema("escape")
    
    elif "cerrar ventana" in texto or "cierra la ventana" in texto:
        return ejecutar_comando_sistema("cerrar_ventana")

    elif "cambiar ventana" in texto or "siguiente ventana" in texto:
        return ejecutar_comando_sistema("cambiar_ventana")



    # Control volume
    elif any(f in texto for f in ["sube el volumen", "aumenta el volumen"]):
        return controlar_volumen("subir")

    elif any(f in texto for f in ["baja el volumen", "disminuye el volumen"]):
        return controlar_volumen("bajar")

    elif "silenciar" in texto or "mute" in texto:
        return controlar_volumen("silenciar")

    elif "activar sonido" in texto or "quitar silencio" in texto:
        return controlar_volumen("activar")

    # Control brillo
    elif "sube el brillo" in texto or "aumenta el brillo" in texto:
        return controlar_brilho("subir")

    elif "baja el brillo" in texto or "disminuye el brillo" in texto:
        return controlar_brilho("bajar")
        
        

    #####################################
    # Apagar, reiniciar o bloquear equipo
    elif any(frase in texto for frase in ["apaga el equipo", "apagar el equipo", "apaga el computador", "apagar computador"]):
        return "Apagando el equipo...", "apagar"

    elif any(frase in texto for frase in ["reinicia el sistema", "reiniciar equipo", "reinicia el computador", "reiniciar computador"]):
        return "Reiniciando el sistema...", "reiniciar"

    elif any(frase in texto for frase in ["bloquea el equipo", "bloquea el computador", "bloquear equipo", "bloquear el sistema"]):
        return "Bloqueando el equipo...", "bloquear"



    else:
        return f"No entiendo el comando: {texto}", False
