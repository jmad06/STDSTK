#!/usr/bin/env python3
"""
Script principal: Herramienta interactiva de Data Profiling (CLI)
-------------------------------------------------------------------
Orquesta la ejecución de los módulos:
  1. interfaz_usuario   -> interacción con el usuario, encoding, sugerencias
  2. gestor_config      -> guardar/cargar clasificación de tipos (JSON)
  3. nivel1_limpieza    -> calidad e integridad de los datos + duplicados
  4. nivel2_descriptivo -> estadísticas descriptivas + outliers + normalidad
  5. exportador         -> generación del reporte Excel

Ejecutar con: python main.py
Requiere: pandas, numpy, xlsxwriter, openpyxl, scipy, chardet (ver requirements.txt)
"""

import sys

import interfaz_usuario as ui
import gestor_config as config
import nivel1_limpieza as limpieza
import nivel2_descriptivo as descriptivo
import exportador

# Tipos que comparten las mismas métricas descriptivas numéricas / categóricas.
TIPOS_NUMERICOS = ("numerica_continua", "numerica_discreta")
TIPOS_CATEGORICOS = ("cualitativa_nominal", "cualitativa_ordinal", "cualitativa_binaria")


def main():
    print("=" * 60)
    print(" HERRAMIENTA DE DATA PROFILING - Limpieza y Análisis Descriptivo")
    print("=" * 60)

    # 1. Ruta del archivo: se acepta como argumento de línea de comandos
    #    (ej. arrastrado sobre el .bat) o, si no viene, se pregunta por consola.
    ruta = None
    if len(sys.argv) > 1:
        ruta_arg = sys.argv[1].strip('"')
        if ui.validar_ruta_valida(ruta_arg):
            ruta = ruta_arg
            ui.mostrar_mensaje(f"Archivo recibido: '{ruta}'", "ok")
        else:
            ui.mostrar_mensaje("Se ignorará el argumento recibido; se pedirá la ruta manualmente.", "warn")

    if ruta is None:
        ruta = ui.solicitar_ruta_archivo()
        if ruta is None:
            ui.mostrar_mensaje("Operación cancelada por el usuario.", "warn")
            return

    # 2. Carga del dataset (con detección automática de encoding para .csv)
    try:
        df = ui.cargar_dataset(ruta)
        ui.mostrar_mensaje(
            f"Archivo cargado correctamente: {df.shape[0]} filas x {df.shape[1]} columnas.", "ok"
        )
    except RuntimeError as e:
        ui.mostrar_mensaje(str(e), "error")
        return

    # 3. Intentar cargar una configuración de tipos previamente guardada
    tipos_precargados = {}
    ruta_config = ui.solicitar_ruta_configuracion_entrada()
    if ruta_config:
        try:
            config_cruda = config.cargar_configuracion(ruta_config)
            if config_cruda:
                tipos_precargados = config.filtrar_configuracion_valida(config_cruda, list(df.columns))
        except Exception as e:
            ui.mostrar_mensaje(f"No se pudo usar la configuración cargada: {e}", "error")

    # 4. Definición interactiva del tipo de cada columna (bloques, sugerencia, o precargada)
    #    tipos_todos incluye TODAS las columnas clasificadas, incluidas las "ignorar",
    #    para que la configuración guardada las recuerde en la próxima ejecución.
    tipos_todos = ui.definir_tipos_columnas(df, tipos_precargados=tipos_precargados)
    tipos_columnas = {c: t for c, t in tipos_todos.items() if t != "ignorar"}
    if not tipos_columnas:
        ui.mostrar_mensaje("No se seleccionó ninguna columna para analizar. Finalizando.", "warn")
        return

    # 5. Ofrecer guardar la clasificación resultante (incluidas las ignoradas) para reutilizarla después
    try:
        if ui.solicitar_guardar_configuracion():
            nombre_config = ui.solicitar_nombre_configuracion()
            guardada = config.guardar_configuracion(tipos_todos, nombre_config)
            if guardada:
                ui.mostrar_mensaje(f"Configuración guardada en '{guardada}'.", "ok")
    except Exception as e:
        ui.mostrar_mensaje(f"No se pudo guardar la configuración: {e}", "error")

    # 6. Selección de procesos a ejecutar
    proceso = ui.solicitar_procesos()

    df_limpieza = None
    df_duplicados = None
    df_num = None
    df_cat = None

    # 7. Ejecución de módulos según selección (cada uno aislado en su propio try/except)
    if proceso in ("A", "C"):
        try:
            ui.mostrar_mensaje("Ejecutando módulo de Limpieza (Nivel 1)...", "info")
            df_limpieza = limpieza.calcular_limpieza(df, tipos_columnas)
            ui.mostrar_mensaje("Módulo de Limpieza finalizado.", "ok")
        except Exception as e:
            ui.mostrar_mensaje(f"Falló el módulo de Limpieza: {e}", "error")

        try:
            ui.mostrar_mensaje("Analizando filas duplicadas...", "info")
            df_duplicados = limpieza.detectar_duplicados(df, list(tipos_columnas.keys()))
            ui.mostrar_mensaje("Análisis de duplicados finalizado.", "ok")
        except Exception as e:
            ui.mostrar_mensaje(f"Falló el análisis de duplicados: {e}", "error")

    if proceso in ("B", "C"):
        try:
            ui.mostrar_mensaje("Ejecutando módulo Descriptivo (Nivel 2)...", "info")

            columnas_numericas = [c for c, t in tipos_columnas.items() if t in TIPOS_NUMERICOS]
            columnas_categoricas = [c for c, t in tipos_columnas.items() if t in TIPOS_CATEGORICOS]

            if columnas_numericas:
                df_num = descriptivo.calcular_descriptivo_numericas(df, columnas_numericas)
            else:
                ui.mostrar_mensaje("No hay columnas numéricas seleccionadas; se omite esa pestaña.", "warn")

            if columnas_categoricas:
                df_cat = descriptivo.calcular_descriptivo_categoricas(df, columnas_categoricas)
            else:
                ui.mostrar_mensaje("No hay columnas categóricas seleccionadas; se omite esa pestaña.", "warn")

            ui.mostrar_mensaje("Módulo Descriptivo finalizado.", "ok")
        except Exception as e:
            ui.mostrar_mensaje(f"Falló el módulo Descriptivo: {e}", "error")

    # 8. Exportación del reporte
    ruta_salida = ui.confirmar_ruta_salida()
    hojas = {
        "1_Limpieza": df_limpieza,
        "2_Desc_Numericas": df_num,
        "3_Desc_Categoricas": df_cat,
        "4_Duplicados": df_duplicados,
    }
    resultado = exportador.exportar_reporte(hojas, ruta_salida)

    if resultado:
        ui.mostrar_mensaje(f"Reporte generado exitosamente: '{resultado}'", "ok")
    else:
        ui.mostrar_mensaje("No se generó el reporte final.", "error")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[AVISO] Ejecución interrumpida por el usuario (Ctrl+C).")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR CRÍTICO] Ocurrió un error inesperado: {e}")
        sys.exit(1)
