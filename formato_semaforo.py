"""
Módulo: formato_semaforo
-------------------------
Define las reglas de "semáforo" (verde = aceptable, amarillo = revisar,
rojo = alerta) usadas para colorear la fuente de las celdas del reporte
Excel, según los umbrales del checklist de interpretación rápida.

Cada regla recibe la FILA COMPLETA (pd.Series), no solo el valor de la
celda, para poder usar el contexto de otras columnas cuando sea necesario
(ej. el p-valor de Shapiro-Wilk solo se colorea si el tamaño de muestra
evaluado es pequeño; con muestras grandes se deja sin colorear a propósito).

Si una regla no puede evaluarse (valor no numérico, columna ausente, celda
"N/A"/"N/D"), se devuelve None y esa celda simplemente no se colorea.
"""


def _es_numero(valor):
    """Convierte a float de forma segura. Devuelve None si no es posible
    (por ejemplo, celdas de texto como 'N/A', 'N/D' o 'Error: ...')."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


# ----------------------------- Pestaña 1_Limpieza -----------------------------

def _regla_nulos(fila, columna):
    """Nulos (%): verde <5%, amarillo 5-20%, rojo >20%."""
    v = _es_numero(fila.get(columna))
    if v is None:
        return None
    if v < 5:
        return "verde"
    if v <= 20:
        return "amarillo"
    return "rojo"


def _regla_blancos(fila, columna):
    """Blancos (%): verde <1%, amarillo 1-5%, rojo >5%."""
    v = _es_numero(fila.get(columna))
    if v is None:
        return None
    if v < 1:
        return "verde"
    if v <= 5:
        return "amarillo"
    return "rojo"


def _regla_balance_binaria(fila, columna):
    """Balance de la categoría mayoritaria en binarias: verde 50-60%
    (balanceada), amarillo 60-90%, rojo >90% (clase muy desbalanceada).
    Las filas no binarias tienen 'N/A' y no se colorean."""
    v = _es_numero(fila.get(columna))
    if v is None:
        return None
    if v <= 60:
        return "verde"
    if v <= 90:
        return "amarillo"
    return "rojo"


# ----------------------------- Pestaña 2_Desc_Numericas -----------------------------

def _regla_skewness(fila, columna):
    """Skewness: verde |s|<=0.5, amarillo 0.5-1, rojo >1."""
    v = _es_numero(fila.get(columna))
    if v is None:
        return None
    av = abs(v)
    if av <= 0.5:
        return "verde"
    if av <= 1:
        return "amarillo"
    return "rojo"


def _regla_shapiro_w(fila, columna):
    """Estadístico W de Shapiro-Wilk: verde >0.95, amarillo 0.90-0.95, rojo <0.90."""
    v = _es_numero(fila.get(columna))
    if v is None:
        return None
    if v > 0.95:
        return "verde"
    if v >= 0.90:
        return "amarillo"
    return "rojo"


def _regla_shapiro_pvalor(fila, columna):
    """
    p-valor de Shapiro-Wilk: solo se colorea cuando el tamaño de muestra
    evaluado (columna 'Shapiro N Evaluado') es <= 300, ya que con muestras
    grandes el p-valor pierde utilidad práctica (casi siempre da < 0.05).
    """
    n = _es_numero(fila.get("Shapiro N Evaluado"))
    p = _es_numero(fila.get(columna))
    if n is None or p is None or n > 300:
        return None
    return "verde" if p > 0.05 else "rojo"


def _regla_outliers_pct(fila, columna):
    """Outliers (%) por IQR o Z-score: verde <1%, amarillo 1-5%, rojo >5%."""
    v = _es_numero(fila.get(columna))
    if v is None:
        return None
    if v < 1:
        return "verde"
    if v <= 5:
        return "amarillo"
    return "rojo"


# ----------------------------- Pestaña 3_Desc_Categoricas -----------------------------

def _regla_peso_moda(fila, columna):
    """Peso de la moda (%): verde <50%, amarillo 50-80%, rojo >80%."""
    v = _es_numero(fila.get(columna))
    if v is None:
        return None
    if v < 50:
        return "verde"
    if v <= 80:
        return "amarillo"
    return "rojo"


def _regla_categorias_distintas(fila, columna):
    """Cardinalidad categórica: solo se marca en rojo si supera 50 categorías
    distintas (posible inconsistencia de escritura); no hay verde/amarillo
    porque el valor 'esperado' depende totalmente del contexto de negocio."""
    v = _es_numero(fila.get(columna))
    if v is None:
        return None
    return "rojo" if v > 50 else None


# Mapa principal: {nombre_pestaña: {nombre_columna: función_regla}}
# La pestaña '4_Duplicados' tiene estructura distinta (Métrica/Valor) y se
# maneja como caso especial directamente en el módulo exportador.
REGLAS_POR_PESTANA = {
    "1_Limpieza": {
        "Nulos (%)": _regla_nulos,
        "Blancos (%)": _regla_blancos,
        "Balance Binaria - Cat. Mayoritaria (%)": _regla_balance_binaria,
    },
    "2_Desc_Numericas": {
        "Skewness": _regla_skewness,
        "Shapiro-Wilk Stat": _regla_shapiro_w,
        "Shapiro-Wilk p-valor": _regla_shapiro_pvalor,
        "Outliers IQR (%)": _regla_outliers_pct,
        "Outliers Z-score (%)": _regla_outliers_pct,
    },
    "3_Desc_Categoricas": {
        "Peso Moda (%)": _regla_peso_moda,
        "Categorías Distintas": _regla_categorias_distintas,
    },
}


def obtener_reglas(nombre_pestana):
    """Devuelve el diccionario {columna: función_regla} para una pestaña dada,
    o un diccionario vacío si esa pestaña no tiene reglas de semáforo definidas."""
    return REGLAS_POR_PESTANA.get(nombre_pestana, {})
