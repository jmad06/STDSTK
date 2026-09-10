"""
Módulo: exportador
--------------------
Funciones encargadas de guardar los resultados del profiling en un archivo
Excel con múltiples pestañas, formato legible (anchos de columna ajustados)
y formato semáforo (fuente verde/amarillo/rojo) según los umbrales definidos
en el módulo 'formato_semaforo'.
"""

import pandas as pd

import formato_semaforo as semaforo


def _ajustar_anchos(worksheet, df):
    """Ajusta el ancho de cada columna de una hoja según el contenido más largo."""
    for i, col in enumerate(df.columns):
        try:
            largo_max = max(
                df[col].astype(str).map(len).max() if not df.empty else 0,
                len(str(col))
            )
            worksheet.set_column(i, i, min(int(largo_max) + 3, 60))
        except Exception:
            worksheet.set_column(i, i, 18)


def _crear_formatos_semaforo(workbook):
    """Crea los 3 formatos de fuente (verde/amarillo/rojo) usando los colores
    estándar de Excel para estilos 'Bueno/Neutral/Malo', para que sean
    visualmente reconocibles."""
    return {
        "verde": workbook.add_format({"font_color": "#006100", "bold": True}),
        "amarillo": workbook.add_format({"font_color": "#9C6500", "bold": True}),
        "rojo": workbook.add_format({"font_color": "#9C0006", "bold": True}),
    }


def _colorear_fila_duplicados(worksheet, df, formatos):
    """
    Caso especial para la pestaña '4_Duplicados', que tiene estructura
    Métrica/Valor en vez de una columna por métrica. Colorea solo la fila
    'Filas Duplicadas (%)': verde si es 0%, rojo si es mayor a 0%.
    """
    try:
        columnas = list(df.columns)
        if "Métrica" not in columnas or "Valor" not in columnas:
            return
        idx_valor = columnas.index("Valor")
        for idx_fila, (_, fila) in enumerate(df.iterrows()):
            if fila.get("Métrica") == "Filas Duplicadas (%)":
                try:
                    valor_num = float(fila["Valor"])
                except (TypeError, ValueError):
                    continue
                tier = "verde" if valor_num == 0 else "rojo"
                worksheet.write(idx_fila + 1, idx_valor, fila["Valor"], formatos[tier])
    except Exception as e:
        print(f"[ERROR] No se pudo aplicar semáforo a duplicados: {e}")


def _aplicar_semaforo(worksheet, df, nombre_hoja, formatos):
    """
    Aplica color de fuente (verde/amarillo/rojo) a las celdas cuyas columnas
    tengan una regla definida en 'formato_semaforo', según el checklist de
    interpretación rápida. Un fallo en una celda puntual no interrumpe el
    resto del formato.
    """
    if nombre_hoja == "4_Duplicados":
        _colorear_fila_duplicados(worksheet, df, formatos)
        return

    reglas = semaforo.obtener_reglas(nombre_hoja)
    if not reglas:
        return

    columnas = list(df.columns)
    for nombre_col, funcion_regla in reglas.items():
        if nombre_col not in columnas:
            continue
        idx_col = columnas.index(nombre_col)
        for idx_fila, (_, fila) in enumerate(df.iterrows()):
            try:
                tier = funcion_regla(fila, nombre_col)
                if tier and tier in formatos:
                    worksheet.write(idx_fila + 1, idx_col, fila[nombre_col], formatos[tier])
            except Exception:
                continue  # una celda problemática no debe romper el resto del formato


def exportar_reporte(hojas, ruta_salida="reporte_calidad.xlsx"):
    """
    Exporta uno o varios DataFrames a un archivo Excel, cada uno en su propia
    pestaña, con anchos de columna ajustados y formato semáforo aplicado
    según el checklist de interpretación rápida.

    Parámetros:
        hojas (dict): {nombre_pestaña: DataFrame}. Las pestañas con DataFrame
                      vacío o None se omiten automáticamente.
        ruta_salida (str): nombre/ruta del archivo .xlsx a generar.

    Retorna:
        str: ruta del archivo generado, o None si ocurrió un error crítico
             o no había datos para exportar.
    """
    try:
        with pd.ExcelWriter(ruta_salida, engine="xlsxwriter") as writer:
            workbook = writer.book
            formatos = _crear_formatos_semaforo(workbook)
            hojas_escritas = 0

            for nombre_hoja, df in hojas.items():
                if df is None or df.empty:
                    continue
                try:
                    nombre_valido = nombre_hoja[:31]  # límite de Excel para nombres de pestaña
                    df.to_excel(writer, sheet_name=nombre_valido, index=False)
                    worksheet = writer.sheets[nombre_valido]
                    _ajustar_anchos(worksheet, df)
                    _aplicar_semaforo(worksheet, df, nombre_hoja, formatos)
                    hojas_escritas += 1
                except Exception as e:
                    print(f"[ERROR] No se pudo escribir la pestaña '{nombre_hoja}': {e}")

            if hojas_escritas == 0:
                print("[AVISO] No había datos para exportar. No se generó ningún reporte.")
                return None

        return ruta_salida
    except Exception as e:
        print(f"[ERROR] No fue posible generar el archivo Excel: {e}")
        return None
