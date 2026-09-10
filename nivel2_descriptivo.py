"""
Módulo: nivel2_descriptivo
---------------------------
Funciones encargadas de calcular estadísticas descriptivas según el tipo
de dato: numéricas y categóricas. Cada columna se procesa de forma aislada.
"""

import numpy as np
import pandas as pd


def _moda_segura(serie):
    """Devuelve la moda de una serie de forma segura, o 'N/D' si no se puede calcular."""
    try:
        moda = serie.mode(dropna=True)
        if moda.empty:
            return "N/D"
        return moda.iloc[0]
    except Exception:
        return "N/D"


def _outliers_iqr(serie, q1, q3):
    """
    Detecta outliers por el método del Rango Intercuartílico (IQR):
    un valor es outlier si cae por debajo de Q1 - 1.5*IQR o por encima de
    Q3 + 1.5*IQR. No asume una distribución normal de los datos.

    Retorna: (limite_inferior, limite_superior, cantidad_outliers, porcentaje_outliers)
    """
    try:
        iqr = q3 - q1
        limite_inf = q1 - 1.5 * iqr
        limite_sup = q3 + 1.5 * iqr
        es_outlier = (serie < limite_inf) | (serie > limite_sup)
        cantidad = int(es_outlier.sum())
        porcentaje = round((cantidad / len(serie)) * 100, 2) if len(serie) else 0
        return round(limite_inf, 4), round(limite_sup, 4), cantidad, porcentaje
    except Exception:
        return "N/D", "N/D", "N/D", "N/D"


def _outliers_zscore(serie, umbral=3):
    """
    Detecta outliers por el método del Z-score: un valor es outlier si su
    desviación respecto a la media supera 'umbral' desviaciones estándar
    (por defecto ±3). Asume una distribución aproximadamente normal.

    Retorna: (cantidad_outliers, porcentaje_outliers)
    """
    try:
        std = serie.std()
        if std == 0 or pd.isna(std):
            return 0, 0.0
        z_scores = (serie - serie.mean()) / std
        es_outlier = z_scores.abs() > umbral
        cantidad = int(es_outlier.sum())
        porcentaje = round((cantidad / len(serie)) * 100, 2) if len(serie) else 0
        return cantidad, porcentaje
    except Exception:
        return "N/D", "N/D"


def _etiqueta_sesgo(skewness):
    """
    Clasifica el coeficiente de asimetría en una etiqueta legible, usando
    los mismos umbrales del checklist de interpretación (|s|<=0.5 simétrica,
    0.5-1 moderado, >1 fuerte), incluyendo la dirección del sesgo.
    """
    try:
        s = float(skewness)
    except (TypeError, ValueError):
        return "N/D"
    direccion = "derecha" if s > 0 else "izquierda"
    if abs(s) <= 0.5:
        return "Simétrica"
    if abs(s) <= 1:
        return f"Moderado ({direccion})"
    return f"Fuerte ({direccion})"


def _categoria_outliers(pct_outliers_iqr):
    """Clasifica el % de outliers IQR en Bajo (<1%), Medio (1-5%) o Alto (>5%)."""
    try:
        p = float(pct_outliers_iqr)
    except (TypeError, ValueError):
        return None
    if p < 1:
        return "Bajo"
    if p <= 5:
        return "Medio"
    return "Alto"


# Matriz de decisión Media/Mediana: la media solo se recomienda cuando la
# distribución es simétrica y casi no hay outliers; ante sesgo relevante u
# outliers relevantes, la mediana es más robusta. Los casos mixtos (una
# señal buena y otra regular) quedan como "Indiferente".
_MATRIZ_MEDIDA_RECOMENDADA = {
    "Simétrica": {"Bajo": "Media", "Medio": "Indiferente", "Alto": "Mediana"},
    "Moderado": {"Bajo": "Indiferente", "Medio": "Mediana", "Alto": "Mediana"},
    "Fuerte": {"Bajo": "Mediana", "Medio": "Mediana", "Alto": "Mediana"},
}


def _medida_recomendada(etiqueta_sesgo, pct_outliers_iqr):
    """
    Decide si es más recomendable usar Media o Mediana para una variable,
    combinando la etiqueta de sesgo (Skewness) y el % de outliers IQR según
    la matriz de decisión acordada. Devuelve 'N/D' si falta algún insumo.
    """
    categoria_outliers = _categoria_outliers(pct_outliers_iqr)
    if etiqueta_sesgo == "N/D" or categoria_outliers is None:
        return "N/D"

    categoria_sesgo = etiqueta_sesgo.split(" ")[0]  # "Simétrica" / "Moderado" / "Fuerte"
    return _MATRIZ_MEDIDA_RECOMENDADA.get(categoria_sesgo, {}).get(categoria_outliers, "N/D")


def _test_normalidad(serie, max_muestra=5000, semilla=42):
    """
    Ejecuta el test de normalidad Shapiro-Wilk sobre una serie numérica.
    Requiere al menos 3 observaciones. Si la serie tiene más de
    'max_muestra' valores, se toma una muestra aleatoria (con semilla fija
    para reproducibilidad) ya que el test pierde fiabilidad y se vuelve
    excesivamente sensible con datasets muy grandes.

    Retorna: (n_evaluado, estadístico, p_valor, es_normal ('Sí'/'No'))
    o ('N/D', 'N/D', 'N/D', 'N/D') si no se pudo calcular.
    """
    try:
        from scipy import stats

        n = len(serie)
        if n < 3:
            return "N/D", "N/D", "N/D", "N/D"

        datos = serie if n <= max_muestra else serie.sample(max_muestra, random_state=semilla)
        estadistico, p_valor = stats.shapiro(datos)
        es_normal = "Sí" if p_valor > 0.05 else "No"
        return len(datos), round(estadistico, 4), round(p_valor, 6), es_normal
    except Exception:
        return "N/D", "N/D", "N/D", "N/D"


def calcular_descriptivo_numericas(df, columnas_numericas):
    """
    Calcula estadísticas descriptivas para columnas numéricas:
    Media, Mediana (P50), Moda, Mínimo, Máximo, Q1 (P25), Q3 (P75),
    IQR, Desviación Estándar, Coeficiente de Asimetría (Skewness) y
    detección de outliers por dos métodos:
      - IQR: valores fuera de [Q1 - 1.5*IQR, Q3 + 1.5*IQR].
      - Z-score: valores con |z| > 3 desviaciones estándar respecto a la media.

    Parámetros:
        df (pd.DataFrame): dataset original.
        columnas_numericas (list): columnas marcadas como numéricas por el usuario.

    Retorna:
        pd.DataFrame con una fila por columna numérica.
    """
    columnas_reporte = [
        "Columna", "Media", "Mediana (P50)", "Moda", "Mínimo", "Máximo",
        "Q1 (P25)", "Q3 (P75)", "IQR", "Desv. Estándar", "Skewness",
        "Sesgo (Etiqueta)", "Medida Recomendada",
        "Límite Inferior IQR", "Límite Superior IQR", "Outliers IQR (#)", "Outliers IQR (%)",
        "Outliers Z-score (#)", "Outliers Z-score (%)",
        "Shapiro N Evaluado", "Shapiro-Wilk Stat", "Shapiro-Wilk p-valor", "¿Distribución Normal? (p>0.05)",
    ]
    filas = []

    for columna in columnas_numericas:
        fila = {c: "N/D" for c in columnas_reporte}
        fila["Columna"] = columna
        try:
            serie = pd.to_numeric(df[columna], errors="coerce").dropna()
            if serie.empty:
                filas.append(fila)
                continue

            q1 = serie.quantile(0.25)
            q3 = serie.quantile(0.75)

            fila.update({
                "Media": round(serie.mean(), 4),
                "Mediana (P50)": round(serie.median(), 4),
                "Moda": _moda_segura(serie),
                "Mínimo": round(serie.min(), 4),
                "Máximo": round(serie.max(), 4),
                "Q1 (P25)": round(q1, 4),
                "Q3 (P75)": round(q3, 4),
                "IQR": round(q3 - q1, 4),
                "Desv. Estándar": round(serie.std(), 4),
                "Skewness": round(serie.skew(), 4),
            })

            # Outliers - método IQR
            limite_inf, limite_sup, n_out_iqr, pct_out_iqr = _outliers_iqr(serie, q1, q3)
            fila["Límite Inferior IQR"] = limite_inf
            fila["Límite Superior IQR"] = limite_sup
            fila["Outliers IQR (#)"] = n_out_iqr
            fila["Outliers IQR (%)"] = pct_out_iqr

            # Sesgo y recomendación Media/Mediana (usa Skewness + Outliers IQR %)
            etiqueta_sesgo = _etiqueta_sesgo(fila["Skewness"])
            fila["Sesgo (Etiqueta)"] = etiqueta_sesgo
            fila["Medida Recomendada"] = _medida_recomendada(etiqueta_sesgo, pct_out_iqr)

            # Outliers - método Z-score
            n_out_z, pct_out_z = _outliers_zscore(serie)
            fila["Outliers Z-score (#)"] = n_out_z
            fila["Outliers Z-score (%)"] = pct_out_z

            # Test de normalidad Shapiro-Wilk
            n_eval, stat_sw, p_sw, normalidad = _test_normalidad(serie)
            fila["Shapiro N Evaluado"] = n_eval
            fila["Shapiro-Wilk Stat"] = stat_sw
            fila["Shapiro-Wilk p-valor"] = p_sw
            fila["¿Distribución Normal? (p>0.05)"] = normalidad

        except Exception as e:
            fila["Media"] = f"Error: {e}"

        filas.append(fila)

    if not filas:
        return pd.DataFrame(columns=columnas_reporte)
    return pd.DataFrame(filas)[columnas_reporte]


def calcular_descriptivo_categoricas(df, columnas_categoricas):
    """
    Calcula estadísticas descriptivas para columnas categóricas:
    Moda (categoría más frecuente), peso (%) de esa moda sobre el total,
    número de categorías distintas y la categoría con menor frecuencia.

    Parámetros:
        df (pd.DataFrame): dataset original.
        columnas_categoricas (list): columnas marcadas como categóricas por el usuario.

    Retorna:
        pd.DataFrame con una fila por columna categórica.
    """
    columnas_reporte = [
        "Columna", "Moda", "Peso Moda (%)", "Categorías Distintas", "Categoría Menos Frecuente"
    ]
    filas = []

    for columna in columnas_categoricas:
        fila = {c: "N/D" for c in columnas_reporte}
        fila["Columna"] = columna
        try:
            serie = df[columna].dropna().astype(str).str.strip()
            serie = serie[serie != ""]
            if serie.empty:
                filas.append(fila)
                continue

            conteo = serie.value_counts()
            moda = conteo.idxmax()
            peso_moda = round((conteo.max() / conteo.sum()) * 100, 2)
            categoria_menos_frecuente = conteo.idxmin()

            fila.update({
                "Moda": moda,
                "Peso Moda (%)": peso_moda,
                "Categorías Distintas": int(serie.nunique()),
                "Categoría Menos Frecuente": categoria_menos_frecuente,
            })
        except Exception as e:
            fila["Moda"] = f"Error: {e}"

        filas.append(fila)

    if not filas:
        return pd.DataFrame(columns=columnas_reporte)
    return pd.DataFrame(filas)[columnas_reporte]
