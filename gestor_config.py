"""
Módulo: gestor_config
-----------------------
Funciones encargadas de guardar y cargar la clasificación de tipos de
columnas en un archivo JSON, para poder reutilizarla en ejecuciones
futuras sobre el mismo dataset (o uno con columnas similares).
"""

import json
import os


def guardar_configuracion(tipos_columnas, ruta="config_tipos.json"):
    """
    Guarda el diccionario {columna: tipo} en un archivo JSON legible.

    Parámetros:
        tipos_columnas (dict): clasificación de tipos a persistir.
        ruta (str): ruta/nombre del archivo de salida.

    Retorna:
        str: la ruta del archivo guardado, o None si ocurrió un error.
    """
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(tipos_columnas, f, ensure_ascii=False, indent=2)
        return ruta
    except Exception as e:
        print(f"[ERROR] No se pudo guardar la configuración de tipos: {e}")
        return None


def cargar_configuracion(ruta):
    """
    Carga un diccionario {columna: tipo} desde un archivo JSON previamente
    guardado con guardar_configuracion().

    Parámetros:
        ruta (str): ruta del archivo .json a cargar.

    Retorna:
        dict con la configuración cargada, o None si el archivo no existe,
        está corrupto, o no tiene el formato esperado.
    """
    try:
        if not os.path.isfile(ruta):
            print(f"[ERROR] El archivo de configuración '{ruta}' no existe.")
            return None
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if not isinstance(datos, dict):
            print("[ERROR] El archivo de configuración no tiene el formato esperado (debe ser un objeto JSON).")
            return None
        return datos
    except Exception as e:
        print(f"[ERROR] No se pudo cargar la configuración de tipos: {e}")
        return None


def filtrar_configuracion_valida(config, columnas_disponibles):
    """
    Filtra una configuración cargada para conservar solo las entradas cuyas
    columnas existan en el dataset actual. Columnas del JSON que ya no
    existan en el archivo se descartan silenciosamente (se informa cuántas).

    Parámetros:
        config (dict): configuración cargada desde JSON.
        columnas_disponibles (list): columnas presentes en el DataFrame actual.

    Retorna:
        dict filtrado, solo con columnas válidas.
    """
    if not config:
        return {}
    validas = {c: t for c, t in config.items() if c in columnas_disponibles}
    descartadas = len(config) - len(validas)
    if descartadas > 0:
        print(f"[AVISO] {descartadas} columna(s) de la configuración ya no existen en este archivo y se ignoraron.")
    return validas
