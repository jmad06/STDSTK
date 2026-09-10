"""
Módulo: interfaz_usuario
------------------------
Contiene todas las funciones que gestionan la interacción con el usuario
por consola (inputs, validaciones, menús y mensajes), la detección
automática de encoding y la sugerencia automática de tipos de variable.
"""

import os
import warnings
import pandas as pd

TIPOS_VALIDOS = {
    "1": "numerica_continua",
    "2": "numerica_discreta",
    "3": "cualitativa_nominal",
    "4": "cualitativa_ordinal",
    "5": "cualitativa_binaria",
    "6": "fecha",
    "7": "ignorar",
}

TIPOS_LEGIBLES = {
    "numerica_continua": "Numérica Continua",
    "numerica_discreta": "Numérica Discreta",
    "cualitativa_nominal": "Cualitativa Nominal",
    "cualitativa_ordinal": "Cualitativa Ordinal",
    "cualitativa_binaria": "Cualitativa Binaria",
    "fecha": "Fecha",
    "ignorar": "Ignorar",
}


def mostrar_mensaje(texto, tipo="info"):
    """Imprime un mensaje formateado en consola según su tipo (info, ok, warn, error)."""
    prefijos = {
        "info": "[INFO]",
        "ok": "[OK]",
        "warn": "[AVISO]",
        "error": "[ERROR]",
    }
    print(f"{prefijos.get(tipo, '[INFO]')} {texto}")


def validar_ruta_valida(ruta):
    """
    Valida que una ruta exista y tenga extensión soportada, SIN pedir input
    por consola. Se usa cuando la ruta llega como argumento de línea de
    comandos (ej. al arrastrar un archivo sobre el .bat de ejecución rápida).

    Devuelve True si la ruta es válida, False en caso contrario (mostrando
    el motivo por consola).
    """
    if not ruta:
        return False
    if not os.path.isfile(ruta):
        mostrar_mensaje(f"El archivo arrastrado '{ruta}' no existe.", "error")
        return False
    if not ruta.lower().endswith((".csv", ".xlsx")):
        mostrar_mensaje("Extensión no soportada en el archivo arrastrado. Solo se aceptan .csv o .xlsx.", "error")
        return False
    return True


def solicitar_ruta_archivo():
    """
    Solicita al usuario la ruta de un archivo .csv o .xlsx y valida:
    - Que el archivo exista físicamente.
    - Que la extensión sea soportada.
    Devuelve la ruta validada (str) o None si el usuario decide cancelar.
    """
    while True:
        ruta = input(
            "\n📂 Ingresa la ruta del archivo (.csv o .xlsx), o 'salir' para cancelar: "
        ).strip().strip('"')

        if ruta.lower() in ("salir", "exit", "q"):
            return None

        if not os.path.isfile(ruta):
            mostrar_mensaje(f"El archivo '{ruta}' no existe. Verifica la ruta e intenta de nuevo.", "error")
            continue

        if not ruta.lower().endswith((".csv", ".xlsx")):
            mostrar_mensaje("Extensión no soportada. Solo se aceptan .csv o .xlsx.", "error")
            continue

        return ruta


def detectar_encoding(ruta, n_bytes=200000):
    """
    Detecta el encoding probable de un archivo de texto usando 'chardet'
    sobre una muestra de sus primeros bytes.

    Retorna: (encoding_detectado (str), confianza (float entre 0 y 1))
    Si 'chardet' no está disponible o falla, retorna ('utf-8', 0.0) como
    valor por defecto seguro.
    """
    try:
        import chardet
        with open(ruta, "rb") as f:
            crudo = f.read(n_bytes)
        resultado = chardet.detect(crudo)
        encoding = resultado.get("encoding") or "utf-8"
        confianza = resultado.get("confidence") or 0.0
        return encoding, confianza
    except Exception:
        return "utf-8", 0.0


def cargar_dataset(ruta):
    """
    Carga el dataset en un DataFrame de pandas según su extensión.

    Para archivos .csv, detecta automáticamente el encoding con 'chardet'
    y, si falla, prueba en cascada una lista de encodings comunes
    (utf-8, utf-8-sig, latin-1, cp1252) antes de rendirse.

    Lanza una excepción controlada (RuntimeError) si la lectura falla
    (archivo corrupto, separador desconocido, encoding no identificable, etc.)
    """
    try:
        if ruta.lower().endswith(".csv"):
            encoding_detectado, confianza = detectar_encoding(ruta)
            candidatos = [encoding_detectado, "utf-8", "utf-8-sig", "latin-1", "cp1252"]
            # Elimina duplicados preservando el orden de prioridad
            candidatos = list(dict.fromkeys([c for c in candidatos if c]))

            df = None
            ultimo_error = None
            encoding_usado = None
            for enc in candidatos:
                try:
                    df = pd.read_csv(ruta, sep=None, engine="python", encoding=enc)
                    encoding_usado = enc
                    break
                except (UnicodeDecodeError, LookupError) as e:
                    ultimo_error = e
                    continue

            if df is None:
                raise ultimo_error or RuntimeError("No fue posible determinar el encoding del archivo.")

            if confianza:
                mostrar_mensaje(
                    f"Encoding detectado: '{encoding_usado}' (confianza aprox. {confianza:.0%}).", "info"
                )
            else:
                mostrar_mensaje(f"Encoding utilizado: '{encoding_usado}'.", "info")
        else:
            df = pd.read_excel(ruta)

        if df.empty:
            raise ValueError("El archivo se leyó correctamente pero no contiene datos.")

        return df
    except Exception as e:
        raise RuntimeError(f"No fue posible leer el archivo: {e}")


def sugerir_tipo_columna(serie):
    """
    Analiza el contenido de una serie y sugiere heurísticamente un tipo de
    variable. La sugerencia es solo un punto de partida editable por el
    usuario; nunca sugiere 'cualitativa_ordinal' porque el orden entre
    categorías requiere criterio humano.

    Retorna la clave interna del tipo sugerido (ver TIPOS_VALIDOS).
    """
    try:
        no_nulos = serie.dropna()
        if no_nulos.empty:
            return "cualitativa_nominal"

        # 1. ¿Parece una fecha?
        muestra_texto = no_nulos.astype(str).head(30)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            fechas_parseadas = pd.to_datetime(muestra_texto, errors="coerce", format=None)
        pct_fechas_validas = fechas_parseadas.notna().mean()
        if pct_fechas_validas >= 0.8:
            return "fecha"

        # 2. ¿Es numérica?
        numerico = pd.to_numeric(no_nulos, errors="coerce")
        pct_numerico = numerico.notna().mean()
        if pct_numerico >= 0.9:
            numerico = numerico.dropna()
            n_unicos = numerico.nunique()
            if n_unicos <= 2:
                return "cualitativa_binaria"
            es_entero = ((numerico % 1) == 0).all()
            return "numerica_discreta" if es_entero else "numerica_continua"

        # 3. Es texto: ¿binaria, identificador único, o nominal?
        limpio = no_nulos.astype(str).str.strip()
        n_unicos = limpio.nunique()
        total = len(limpio)
        if n_unicos <= 2:
            return "cualitativa_binaria"
        if n_unicos == total and total > 1:
            return "ignorar"  # probablemente un identificador único (ID)
        return "cualitativa_nominal"
    except Exception:
        return "cualitativa_nominal"


def _mostrar_menu_tipos():
    """Imprime el menú numerado de tipos de variable disponibles."""
    print("  1. Variable numérica continua")
    print("  2. Variable numérica discreta")
    print("  3. Variable cualitativa nominal")
    print("  4. Variable cualitativa ordinal")
    print("  5. Variable cualitativa binaria")
    print("  6. Fecha")
    print("  7. Ignorar columna")


def solicitar_tipo_columna(nombre_columna, muestra, sugerencia=None):
    """
    Muestra el nombre de una columna y una muestra de sus primeros valores,
    y solicita al usuario que clasifique el tipo de variable. Si se provee
    una 'sugerencia', el usuario puede aceptarla presionando Enter.

    Devuelve la clave interna del tipo elegido (ver TIPOS_VALIDOS).
    """
    print("\n" + "-" * 60)
    print(f"Columna: '{nombre_columna}'")
    print(f"Muestra de valores: {muestra}")
    print("¿Qué tipo de variable es?")
    _mostrar_menu_tipos()

    etiqueta_sugerencia = f" [Enter = {TIPOS_LEGIBLES.get(sugerencia, sugerencia)}]" if sugerencia else ""

    while True:
        eleccion = input(f"Selecciona una opción (1-7){etiqueta_sugerencia}: ").strip()
        if eleccion == "" and sugerencia:
            return sugerencia
        if eleccion in TIPOS_VALIDOS:
            return TIPOS_VALIDOS[eleccion]
        mostrar_mensaje("Opción inválida. Debes ingresar un número entre 1 y 7.", "error")


def _parsear_seleccion_indices(texto, total_columnas):
    """
    Convierte un texto como '1,3,5-7' en una lista de índices base-0 válidos.
    Ignora índices fuera de rango o mal formados sin detener el programa.
    """
    indices = set()
    partes = [p.strip() for p in texto.split(",") if p.strip()]
    for parte in partes:
        try:
            if "-" in parte:
                inicio, fin = parte.split("-")
                inicio, fin = int(inicio), int(fin)
                for i in range(inicio, fin + 1):
                    if 1 <= i <= total_columnas:
                        indices.add(i - 1)
            else:
                i = int(parte)
                if 1 <= i <= total_columnas:
                    indices.add(i - 1)
        except (ValueError, IndexError):
            continue
    return sorted(indices)


def definir_tipos_columnas(df, tipos_precargados=None):
    """
    Orquesta la clasificación de columnas ofreciendo tres modos:
      1. Aceptar automáticamente la sugerencia heurística para todas.
      2. Clasificar en bloques (mismo tipo para varias columnas a la vez).
      3. Clasificar una por una (con sugerencia editable).

    Las columnas presentes en 'tipos_precargados' (de una configuración
    guardada previamente) no se vuelven a preguntar.

    Devuelve un diccionario {nombre_columna: tipo} con TODAS las columnas
    clasificadas, incluidas las marcadas como 'ignorar' (para que una
    configuración guardada las recuerde en la próxima ejecución). Es
    responsabilidad de quien llame a esta función filtrar las 'ignorar'
    antes de pasar el resultado a los módulos de análisis. Si una columna
    individual falla al procesarse, se ignora y se continúa con las demás.
    """
    tipos_precargados = tipos_precargados or {}
    columnas_pendientes = [c for c in df.columns if c not in tipos_precargados]
    tipos = dict(tipos_precargados)

    if tipos_precargados:
        mostrar_mensaje(
            f"{len(tipos_precargados)} columna(s) ya tienen tipo asignado desde la configuración cargada.",
            "ok"
        )

    if not columnas_pendientes:
        return tipos

    # --- Vista previa + sugerencias para las columnas pendientes ---
    sugerencias = {}
    print("\n" + "=" * 60)
    print("VISTA PREVIA Y SUGERENCIA AUTOMÁTICA DE TIPOS")
    print("=" * 60)
    for i, col in enumerate(columnas_pendientes, start=1):
        try:
            muestra = df[col].dropna().astype(str).head(3).tolist()
            sugerencia = sugerir_tipo_columna(df[col])
        except Exception:
            muestra, sugerencia = [], "cualitativa_nominal"
        sugerencias[col] = sugerencia
        print(f" [{i}] {col}  ->  muestra: {muestra}  |  sugerido: {TIPOS_LEGIBLES.get(sugerencia, sugerencia)}")

    print("\n¿Cómo deseas clasificar estas columnas?")
    print("  1. Aceptar TODAS las sugerencias automáticas")
    print("  2. Clasificar en bloques (grupos de columnas con el mismo tipo)")
    print("  3. Clasificar una por una (con sugerencia editable)")

    while True:
        modo = input("Selecciona una opción (1-3): ").strip()
        if modo in ("1", "2", "3"):
            break
        mostrar_mensaje("Opción inválida. Debes ingresar 1, 2 o 3.", "error")

    if modo == "1":
        for col in columnas_pendientes:
            tipo = sugerencias[col]
            if tipo == "ignorar":
                mostrar_mensaje(f"Columna '{col}' será ignorada (sugerencia automática).", "warn")
            tipos[col] = tipo
        return tipos

    if modo == "2":
        pendientes = list(columnas_pendientes)
        while pendientes:
            print("\nColumnas aún sin clasificar:")
            for i, col in enumerate(pendientes, start=1):
                print(f"  [{i}] {col} (sugerido: {TIPOS_LEGIBLES.get(sugerencias[col], sugerencias[col])})")
            texto = input(
                "\nIngresa los números del bloque a clasificar (ej: 1,3,5-7),"
                " o 'individual' para hacer el resto una por una: "
            ).strip().lower()

            if texto == "individual":
                break

            indices = _parsear_seleccion_indices(texto, len(pendientes))
            if not indices:
                mostrar_mensaje("No se reconoció ningún número válido. Intenta de nuevo.", "error")
                continue

            columnas_bloque = [pendientes[i] for i in indices]
            print(f"\nColumnas seleccionadas: {columnas_bloque}")
            print("¿Qué tipo se asigna a TODAS estas columnas?")
            _mostrar_menu_tipos()
            while True:
                eleccion = input("Selecciona una opción (1-7): ").strip()
                if eleccion in TIPOS_VALIDOS:
                    tipo_bloque = TIPOS_VALIDOS[eleccion]
                    break
                mostrar_mensaje("Opción inválida. Debes ingresar un número entre 1 y 7.", "error")

            for col in columnas_bloque:
                tipos[col] = tipo_bloque
                if tipo_bloque == "ignorar":
                    mostrar_mensaje(f"Columna '{col}' será ignorada.", "warn")

            pendientes = [c for c in pendientes if c not in columnas_bloque]

        # Lo que quede pendiente (o si el usuario escribió 'individual') se hace uno por uno
        for col in pendientes:
            try:
                muestra = df[col].dropna().astype(str).head(3).tolist()
                tipo = solicitar_tipo_columna(col, muestra, sugerencia=sugerencias.get(col))
                tipos[col] = tipo
                if tipo == "ignorar":
                    mostrar_mensaje(f"Columna '{col}' será ignorada.", "warn")
            except Exception as e:
                mostrar_mensaje(f"No se pudo procesar la columna '{col}': {e}. Se ignorará.", "error")

        return tipos

    # modo == "3": una por una, con sugerencia editable
    for col in columnas_pendientes:
        try:
            muestra = df[col].dropna().astype(str).head(3).tolist()
            tipo = solicitar_tipo_columna(col, muestra, sugerencia=sugerencias.get(col))
            tipos[col] = tipo
            if tipo == "ignorar":
                mostrar_mensaje(f"Columna '{col}' será ignorada.", "warn")
        except Exception as e:
            mostrar_mensaje(f"No se pudo procesar la columna '{col}': {e}. Se ignorará.", "error")

    return tipos


def solicitar_procesos():
    """
    Pregunta al usuario qué proceso desea ejecutar.
    Devuelve 'A' (Solo Limpieza), 'B' (Solo Descripción) o 'C' (Ambos).
    """
    print("\n" + "=" * 60)
    print("¿Qué proceso deseas ejecutar?")
    print("  A. Solo Limpieza")
    print("  B. Solo Descripción")
    print("  C. Ambos")

    while True:
        eleccion = input("Selecciona una opción (A/B/C): ").strip().upper()
        if eleccion in ("A", "B", "C"):
            return eleccion
        mostrar_mensaje("Opción inválida. Debes ingresar A, B o C.", "error")


def confirmar_ruta_salida(nombre_por_defecto="reporte_calidad.xlsx"):
    """
    Pregunta al usuario si desea usar el nombre de archivo por defecto para el
    reporte final, o especificar uno propio. Garantiza que termine en .xlsx.
    """
    ruta = input(f"\nNombre del archivo de salida [{nombre_por_defecto}]: ").strip()
    if not ruta:
        ruta = nombre_por_defecto
    if not ruta.lower().endswith(".xlsx"):
        ruta += ".xlsx"
    return ruta


def solicitar_ruta_configuracion_entrada():
    """
    Pregunta si el usuario tiene un archivo de configuración de tipos
    previamente guardado. Devuelve la ruta (str) o None si se omite.
    """
    ruta = input(
        "\n¿Tienes un archivo de configuración de tipos guardado? "
        "(ruta del .json o Enter para omitir): "
    ).strip().strip('"')
    if not ruta:
        return None
    if not os.path.isfile(ruta):
        mostrar_mensaje(f"No se encontró el archivo '{ruta}'. Se omitirá la configuración previa.", "warn")
        return None
    return ruta


def solicitar_guardar_configuracion():
    """
    Pregunta si el usuario desea guardar la clasificación de tipos actual
    para reutilizarla en una próxima ejecución. Devuelve True/False.
    """
    while True:
        eleccion = input(
            "\n¿Deseas guardar esta clasificación de columnas para reutilizarla después? (S/N): "
        ).strip().upper()
        if eleccion in ("S", "N"):
            return eleccion == "S"
        mostrar_mensaje("Respuesta inválida. Escribe S o N.", "error")


def solicitar_nombre_configuracion(nombre_por_defecto="config_tipos.json"):
    """Pregunta el nombre de archivo para guardar la configuración de tipos."""
    ruta = input(f"Nombre del archivo de configuración [{nombre_por_defecto}]: ").strip()
    if not ruta:
        ruta = nombre_por_defecto
    if not ruta.lower().endswith(".json"):
        ruta += ".json"
    return ruta
