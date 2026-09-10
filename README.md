# Herramienta de Data Profiling (CLI)

Herramienta interactiva de terminal para hacer **limpieza (calidad de datos)** y
**análisis descriptivo** de un dataset `.csv` o `.xlsx`, con detección de
duplicados, test de normalidad, detección de outliers, sugerencia automática
de tipos de variable, y exportación a un reporte Excel de múltiples pestañas.

Arquitectura 100% modular: cada responsabilidad vive en su propio archivo, y un
fallo en una columna o en un módulo no interrumpe el resto de la ejecución.

---

## 1. Estructura de archivos

```
.
├── main.py                  # Orquestador: ejecuta el flujo completo
├── interfaz_usuario.py      # Consola, encoding automático, sugerencia de tipos
├── gestor_config.py         # Guardar/cargar la clasificación de columnas (JSON)
├── nivel1_limpieza.py       # Calidad de datos + detección de duplicados
├── nivel2_descriptivo.py    # Estadísticas descriptivas + outliers + normalidad
├── formato_semaforo.py      # Reglas de color verde/amarillo/rojo (checklist)
├── exportador.py            # Generación del Excel final + formato semáforo
├── requirements.txt         # Dependencias
└── README.md                # Este archivo
```

| Módulo | Responsabilidad |
|---|---|
| `interfaz_usuario.py` | Ruta del archivo, detección de encoding, menús, sugerencia automática de tipos, clasificación en bloque. |
| `gestor_config.py` | Guardar y cargar la clasificación de tipos en un archivo JSON reutilizable. |
| `nivel1_limpieza.py` | Nulos, blancos, cardinalidad, % de ceros, balance de binarias y detección de duplicados. |
| `nivel2_descriptivo.py` | Estadísticas descriptivas, detección de outliers (IQR y Z-score) y test de normalidad (Shapiro-Wilk). |
| `formato_semaforo.py` | Umbrales verde/amarillo/rojo del checklist de interpretación, por columna. |
| `exportador.py` | Escribir el Excel final con pestañas, anchos ajustados y color de fuente semáforo. |
| `main.py` | Llama a los módulos anteriores en el orden correcto y maneja errores globales. |

---

## 2. Instalación

Requiere Python 3.8+.

```bash
pip install -r requirements.txt
```

Dependencias: `pandas`, `numpy`, `xlsxwriter`, `openpyxl`, `scipy` (test de
normalidad), `chardet` (detección de encoding).

---

## 3. Ejecución

```bash
python main.py
```

### Paso 1 — Ruta del archivo

```
📂 Ingresa la ruta del archivo (.csv o .xlsx), o 'salir' para cancelar: datos/ventas.csv
```

Para archivos `.csv`, el script **detecta automáticamente el encoding** con
`chardet` (ej. UTF-8, Latin-1, Windows-1252). Si la detección falla o el
archivo tiene un encoding poco común, se prueba en cascada
`utf-8 → utf-8-sig → latin-1 → cp1252` antes de mostrar un error. Verás algo
como:

```
[INFO] Encoding detectado: 'ISO-8859-1' (confianza aprox. 87%).
```

### Paso 2 — ¿Reutilizar una configuración de tipos guardada?

```
¿Tienes un archivo de configuración de tipos guardado? (ruta del .json o Enter para omitir):
```

- Si presionas Enter, se omite y se clasifican todas las columnas desde cero.
- Si das la ruta de un `config_tipos.json` guardado en una ejecución anterior,
  las columnas que coincidan con el archivo actual **no se vuelven a
  preguntar** (incluidas las que habías marcado como "Ignorar"). Solo se te
  preguntará por columnas nuevas que no estén en esa configuración.

### Paso 3 — Vista previa y sugerencia automática de tipos

Antes de preguntar nada, el script analiza cada columna pendiente y te
muestra una tabla con una sugerencia heurística:

```
============================================================
VISTA PREVIA Y SUGERENCIA AUTOMÁTICA DE TIPOS
============================================================
 [1] id_cliente     ->  muestra: ['C001', 'C002', 'C003']        |  sugerido: Ignorar
 [2] ingreso        ->  muestra: ['4500000', '3200000', '5100000'] |  sugerido: Numérica Continua
 [3] num_compras    ->  muestra: ['3', '5', '0']                 |  sugerido: Numérica Discreta
 [4] ciudad         ->  muestra: ['Bogota', 'Medellin', 'Bogota'] |  sugerido: Cualitativa Nominal
 [5] tiene_tarjeta  ->  muestra: ['Si', 'No', 'Si']               |  sugerido: Cualitativa Binaria
 [6] fecha_registro ->  muestra: ['2023-01-15', '2023-02-20']     |  sugerido: Fecha
```

**Cómo funciona la sugerencia (heurística, siempre editable):**

| Señal detectada | Sugerencia |
|---|---|
| ≥80% de los valores se interpretan como fecha | Fecha |
| ≥90% son numéricos y solo tienen 2 valores distintos | Cualitativa Binaria |
| ≥90% son numéricos, todos enteros | Numérica Discreta |
| ≥90% son numéricos, con decimales | Numérica Continua |
| Texto con solo 2 categorías distintas | Cualitativa Binaria |
| Texto con tantos valores únicos como filas | Ignorar (probable ID) |
| Cualquier otro texto | Cualitativa Nominal |

> La opción "Cualitativa Ordinal" **nunca se sugiere automáticamente**: el
> orden entre categorías (ej. "Bajo/Medio/Alto") requiere criterio humano.
> Siempre puedes reasignarla manualmente.

Después de la vista previa, eliges cómo clasificar:

```
¿Cómo deseas clasificar estas columnas?
  1. Aceptar TODAS las sugerencias automáticas
  2. Clasificar en bloques (grupos de columnas con el mismo tipo)
  3. Clasificar una por una (con sugerencia editable)
```

**Opción 1 — Aceptar todas:** usa la sugerencia de cada columna sin más preguntas. Ideal para una primera exploración rápida.

**Opción 2 — Clasificar en bloques:** te deja agrupar columnas por número y asignarles el mismo tipo de una sola vez:

```
Columnas aún sin clasificar:
  [1] ciudad (sugerido: Cualitativa Nominal)
  [2] pais (sugerido: Cualitativa Nominal)
  [3] region (sugerido: Cualitativa Nominal)
  [4] ingreso (sugerido: Numérica Continua)

Ingresa los números del bloque a clasificar (ej: 1,3,5-7), o 'individual' para hacer el resto una por una: 1-3
Columnas seleccionadas: ['ciudad', 'pais', 'region']
¿Qué tipo se asigna a TODAS estas columnas?
  ...
Selecciona una opción (1-7): 3
```

Puedes repetir esto con distintos bloques (ej. otro bloque para las columnas
numéricas), y en cualquier momento escribir `individual` para clasificar el
resto una por una.

**Opción 3 — Una por una:** el flujo clásico, pero ahora la sugerencia
aparece como valor por defecto — presiona Enter para aceptarla, o escribe otro
número para cambiarla:

```
Selecciona una opción (1-7) [Enter = Cualitativa Binaria]:
```

### Paso 4 — Guardar la clasificación

```
¿Deseas guardar esta clasificación de columnas para reutilizarla después? (S/N): S
Nombre del archivo de configuración [config_tipos.json]:
```

Se guarda un JSON simple, editable a mano si lo necesitas:

```json
{
  "ingreso": "numerica_continua",
  "ciudad": "cualitativa_nominal",
  "id_cliente": "ignorar"
}
```

### Paso 5 — Elegir qué proceso ejecutar

```
============================================================
¿Qué proceso deseas ejecutar?
  A. Solo Limpieza
  B. Solo Descripción
  C. Ambos
```

### Paso 6 — Nombre del archivo de salida

```
Nombre del archivo de salida [reporte_calidad.xlsx]:
```

---

## 4. Guía de tipos de variable

| Opción | Cuándo usarla | Ejemplos |
|---|---|---|
| Numérica continua | Mediciones que pueden tomar cualquier valor decimal | Dinero, temperatura, peso |
| Numérica discreta | Conteos, valores enteros | Número de hijos, unidades vendidas |
| Cualitativa nominal | Categorías sin ningún orden lógico | Ciudad, color, marca |
| Cualitativa ordinal | Categorías con un orden natural | Mes, nivel educativo, talla (S/M/L) |
| Cualitativa binaria | Solo dos categorías posibles | Sí/No, 0/1, Activo/Inactivo |
| Fecha | Columnas de fecha/hora | Fecha de compra, fecha de nacimiento |
| Ignorar columna | No se necesita analizar | IDs internos, columnas irrelevantes |

Las columnas de tipo "Fecha" solo se incluyen en el reporte de **Limpieza**
(Nivel 1); no forman parte del análisis descriptivo (Nivel 2).

---

## 5. Qué calcula cada módulo

### Nivel 1 — Limpieza (pestaña `1_Limpieza`)

| Columna | Descripción |
|---|---|
| Tipo Asignado | El tipo que elegiste (ej. "Numérica Continua") |
| Nulos (#) / (%) | Cantidad y porcentaje de valores `NaN` |
| Blancos (#) / (%) | Cantidad y porcentaje de strings vacíos o solo espacios |
| Valores Únicos | Cardinalidad (conteo de valores distintos, sin contar nulos) |
| Ceros (%) | % de valores exactamente iguales a 0 |
| Balance Binaria - Cat. Mayoritaria (%) | Solo para binarias: % de la categoría más frecuente. "N/A" para el resto |

### Detección de duplicados (pestaña `4_Duplicados`)

Se calcula sobre las columnas que **sí analizaste** (excluyendo las
ignoradas, para que un ID único no impida detectar duplicados de negocio):

| Métrica | Descripción |
|---|---|
| Total de Filas | Filas totales del dataset |
| Filas Duplicadas (#) / (%) | Filas cuyo contenido (en las columnas analizadas) ya apareció antes |
| Filas Únicas Resultantes | Total menos duplicadas |
| Columnas Consideradas | Qué columnas se usaron para comparar |

### Nivel 2 — Descriptivo

**Pestaña `2_Desc_Numericas`** (incluye numérica continua + discreta):

| Columna | Descripción |
|---|---|
| Media, Mediana (P50), Moda | Medidas de tendencia central |
| Mínimo, Máximo | Rango de valores |
| Q1 (P25), Q3 (P75), IQR | Cuartiles y rango intercuartílico |
| Desv. Estándar | Dispersión de los datos |
| Skewness | Coeficiente de asimetría |
| Límite Inferior/Superior IQR | Umbrales `Q1 - 1.5×IQR` y `Q3 + 1.5×IQR` |
| Outliers IQR (#) / (%) | Valores fuera de esos límites (método robusto, recomendado por defecto) |
| Outliers Z-score (#) / (%) | Valores con `\|z\| > 3` desviaciones estándar |
| Shapiro N Evaluado | Cuántos datos se usaron en el test (máx. 5000, muestreados si hay más) |
| Shapiro-Wilk Stat / p-valor | Resultado del test de normalidad |
| ¿Distribución Normal? (p>0.05) | Veredicto "Sí"/"No" |

> **Notas importantes:**
> - Los dos métodos de outliers pueden diferir, sobre todo con datasets
>   pequeños o un solo valor muy extremo: el Z-score puede "enmascarar"
>   outliers porque el valor atípico también infla la media y la desviación
>   estándar usadas para calcularlo. El IQR es más robusto en esos casos.
> - El test de Shapiro-Wilk pierde fiabilidad (se vuelve excesivamente
>   sensible) con más de ~5000 datos; por eso se muestrea automáticamente.
>   Un p-valor bajo con muestras muy grandes no siempre implica una
>   desviación práctica relevante de la normalidad.

**Pestaña `3_Desc_Categoricas`** (incluye nominal + ordinal + binaria):

| Columna | Descripción |
|---|---|
| Moda | Categoría más frecuente |
| Peso Moda (%) | % que representa la moda sobre el total |
| Categorías Distintas | Número de categorías únicas |
| Categoría Menos Frecuente | La categoría con menor número de apariciones |

---

## 6. Reporte final (Excel)

El archivo `.xlsx` se genera con `xlsxwriter` y solo incluye las pestañas que
tengan datos:

- `1_Limpieza` — si elegiste A o C.
- `4_Duplicados` — si elegiste A o C.
- `2_Desc_Numericas` — si elegiste B o C **y** hay al menos una columna numérica.
- `3_Desc_Categoricas` — si elegiste B o C **y** hay al menos una columna categórica.

Cada pestaña tiene el ancho de columnas ajustado automáticamente.

### Formato semáforo (color de fuente automático)

Las celdas de las métricas clave se colorean automáticamente según los
umbrales de `checklist_interpretacion.md` (incluido junto a este README):

| Color | Significado |
|---|---|
| 🟢 Verde | Valor aceptable |
| 🟡 Amarillo | Revisar |
| 🔴 Rojo | Alerta |

| Pestaña | Columnas coloreadas |
|---|---|
| `1_Limpieza` | Nulos (%), Blancos (%), Balance Binaria - Cat. Mayoritaria (%) |
| `2_Desc_Numericas` | Skewness, Shapiro-Wilk Stat, Shapiro-Wilk p-valor (solo si N evaluado ≤ 300), Outliers IQR (%), Outliers Z-score (%) |
| `3_Desc_Categoricas` | Peso Moda (%), Categorías Distintas (solo marca rojo si supera 50) |
| `4_Duplicados` | Fila "Filas Duplicadas (%)": verde si es 0%, rojo si es mayor a 0% |

Las celdas sin una regla aplicable (ej. "N/A", "N/D", o valores fuera del
alcance de una regla) simplemente quedan sin colorear — no es un error, es
una decisión intencional para no dar señales falsas donde el checklist dice
"depende del contexto".

> Nota sobre el p-valor de Shapiro con muestras grandes: si `Shapiro N
> Evaluado > 300`, la celda del p-valor se deja **sin colorear a propósito**,
> ya que con datasets grandes el p-valor pierde utilidad práctica (ver la
> sección 5 más abajo). Guíate por el color de Skewness y de Shapiro-Wilk
> Stat en esos casos.

---

## 7. Manejo de errores

- Ruta de archivo inexistente, extensión no soportada, o configuración JSON
  inválida → mensaje claro y se vuelve a preguntar (o se omite sin romper el flujo).
- Encoding no identificable → se prueba una cascada de encodings comunes antes de fallar.
- Entrada inválida en cualquier menú → vuelve a preguntar sin perder el progreso.
- Si una columna específica falla al calcular sus métricas, esa fila se marca
  como `"N/D"` o `"Error: ..."` pero el resto del reporte se genera con normalidad.
- `Ctrl+C` cierra el programa de forma limpia.

---

## 8. Posibles extensiones futuras

- Matriz de correlación entre variables numéricas (Pearson/Spearman).
- Detección de inconsistencias de escritura en categóricas (ej. "Bogota" vs "bogotá").
- Gráficos embebidos en el Excel (histogramas, boxplots).
- Modo no interactivo (`--config archivo.json`) para pipelines automatizados.
- Suite de pruebas unitarias (pytest) para cada función.
