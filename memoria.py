# memoria.py
import json
import re
import os

archivo_cache = "respuestas_cache.json"

# Cargar el cache desde el archivo (si existe)
if os.path.exists(archivo_cache):
    with open(archivo_cache, "r", encoding="utf-8") as f:
        cache = json.load(f)
else:
    cache = {}

def limpiar_respuesta(texto):
    """Elimina referencias tipo [1], [2], etc., del texto"""
    return re.sub(r"\[\d+\]", "", texto).strip()

def guardar_en_cache(pregunta, respuesta):
    """Guarda una pregunta y respuesta en el cache y archivo"""
    cache[pregunta] = respuesta
    with open(archivo_cache, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
