"""
Módulo: nivel1_limpieza
------------------------
Funciones encargadas de evaluar la calidad e integridad de los datos:
nulos, blancos, cardinalidad y ceros. Cada columna se evalúa de forma
aislada para que un fallo puntual no interrumpa el resto del reporte.
"""

import pandas as pd

# Mapeo de claves internas de tipo a etiquetas legibles para el reporte final.
TIPOS_LEGIBLES = {
    "numerica_continua": "Numérica Continua",
    "numerica_discreta": "Numérica Discreta",
    "cualitativa_nominal": "Cualitativa Nominal",
    "cualitativa_ordinal": "Cualitativa Ordinal",
    "cualitativa_binaria": "Cualitativa Binaria",
    "fecha": "Fecha",
}


def _contar_blancos(serie):
    """Cuenta valores 'blancos' (strings vacíos o solo espacios) dentro de una serie."""
    try:
        no_nulos = serie.dropna()
        if no_nulos.empty:
            return 0
        es_blanco = no_nulos.astype(str).str.strip() == ""
        return int(es_blanco.sum())
    except Exception:
        return 0


def _contar_ceros(serie):
    """
    Cuenta valores exactamente iguales a 0, intentando una conversión numérica
    segura. Si la columna no es convertible a número, devuelve 0.
    """
    try:
        numerico = pd.to_numeric(serie, errors="coerce")
        return int((numerico == 0).sum())
    except Exception:
        return 0


def _balance_binaria(serie, tipo):
    """
    Para variables 'cualitativa_binaria', calcula el % que representa la
    categoría mayoritaria sobre el total (ej. 70% 'Sí' / 30% 'No').
    Para el resto de los tipos, devuelve 'N/A' porque la métrica no aplica.
    """
    if tipo != "cualitativa_binaria":
        return "N/A"
    try:
        limpio = serie.dropna().astype(str).str.strip()
        limpio = limpio[limpio != ""]
        if limpio.empty:
            return "N/D"
        conteo = limpio.value_counts()
        return round((conteo.max() / conteo.sum()) * 100, 2)
    except Exception:
        return "N/D"


def evaluar_columna(df, columna, tipo):
    """
    Calcula las métricas de calidad de una única columna:
    - Tipo asignado por el usuario.
    - Nulos (conteo y %).
    - Blancos (conteo y %).
    - Valores únicos (cardinalidad).
    - % de valores exactamente cero.

    Si ocurre un error, la fila se marca con 'N/D' o el detalle del error,
    sin interrumpir la evaluación de las demás columnas.
    """
    total = len(df)
    fila = {
        "Columna": columna,
        "Tipo Asignado": TIPOS_LEGIBLES.get(tipo, tipo),
        "Nulos (#)": "N/D",
        "Nulos (%)": "N/D",
        "Blancos (#)": "N/D",
        "Blancos (%)": "N/D",
        "Valores Únicos": "N/D",
        "Ceros (%)": "N/D",
        "Balance Binaria - Cat. Mayoritaria (%)": "N/D",
    }
    try:
        serie = df[columna]
        n_nulos = int(serie.isna().sum())
        n_blancos = _contar_blancos(serie)
        n_unicos = int(serie.nunique(dropna=True))
        n_ceros = _contar_ceros(serie)

        fila["Nulos (#)"] = n_nulos
        fila["Nulos (%)"] = round((n_nulos / total) * 100, 2) if total else 0
        fila["Blancos (#)"] = n_blancos
        fila["Blancos (%)"] = round((n_blancos / total) * 100, 2) if total else 0
        fila["Valores Únicos"] = n_unicos
        fila["Ceros (%)"] = round((n_ceros / total) * 100, 2) if total else 0
        fila["Balance Binaria - Cat. Mayoritaria (%)"] = _balance_binaria(serie, tipo)
    except Exception as e:
        fila["Nulos (#)"] = f"Error: {e}"

    return fila


def calcular_limpieza(df, columnas_tipos):
    """
    Recorre todas las columnas seleccionadas por el usuario (con su tipo asignado)
    y construye un DataFrame consolidado con las métricas de calidad de cada una.

    Parámetros:
        df (pd.DataFrame): dataset original.
        columnas_tipos (dict): {nombre_columna: tipo}.

    Retorna:
        pd.DataFrame con una fila por columna evaluada.
    """
    filas = []
    for columna, tipo in columnas_tipos.items():
        try:
            fila = evaluar_columna(df, columna, tipo)
        except Exception as e:
            fila = {"Columna": columna, "Tipo Asignado": tipo, "Nulos (#)": f"Error: {e}"}
        filas.append(fila)

    columnas_reporte = [
        "Columna", "Tipo Asignado", "Nulos (#)", "Nulos (%)",
        "Blancos (#)", "Blancos (%)", "Valores Únicos", "Ceros (%)",
        "Balance Binaria - Cat. Mayoritaria (%)",
    ]

    if not filas:
        return pd.DataFrame(columns=columnas_reporte)

    return pd.DataFrame(filas)[columnas_reporte]


def detectar_duplicados(df, columnas):
    """
    Analiza duplicados a nivel de fila, considerando únicamente las columnas
    que el usuario seleccionó para el análisis (no las ignoradas), ya que
    columnas identificadoras (ej. IDs únicos) harían que nunca se detecten
    duplicados reales de negocio.

    Parámetros:
        df (pd.DataFrame): dataset original.
        columnas (list): columnas a considerar para la comparación de filas.
                          Si está vacía, se usan todas las columnas del df.

    Retorna:
        pd.DataFrame de dos columnas (Métrica, Valor) con el resumen.
    """
    try:
        subset = columnas if columnas else None
        total_filas = len(df)

        mask_duplicadas = df.duplicated(subset=subset, keep="first")
        n_duplicadas = int(mask_duplicadas.sum())
        pct_duplicadas = round((n_duplicadas / total_filas) * 100, 2) if total_filas else 0

        filas = [
            {"Métrica": "Total de Filas", "Valor": total_filas},
            {"Métrica": "Filas Duplicadas (#)", "Valor": n_duplicadas},
            {"Métrica": "Filas Duplicadas (%)", "Valor": pct_duplicadas},
            {"Métrica": "Filas Únicas Resultantes", "Valor": total_filas - n_duplicadas},
            {"Métrica": "Columnas Consideradas", "Valor": ", ".join(subset) if subset else "Todas las columnas"},
        ]
        return pd.DataFrame(filas)
    except Exception as e:
        return pd.DataFrame([
            {"Métrica": "Error al calcular duplicados", "Valor": str(e)}
        ])
