# Checklist de Interpretación Rápida — Reporte de Data Profiling

Guía de referencia para leer el Excel sin tener que recordar la teoría cada vez.

---

## 1. Calidad de datos (pestaña `1_Limpieza`)

| Métrica | ✅ Aceptable | ⚠️ Revisar | 🔴 Alerta |
|---|---|---|---|
| Nulos (%) | < 5% | 5% – 20% | > 20% (considera imputar o descartar la columna) |
| Blancos (%) | < 1% | 1% – 5% | > 5% (probable error de captura, no un NaN real) |
| Ceros (%) | Depende del contexto | — | Muy alto en variables tipo "monto" puede indicar error, no un valor real |
| Valores Únicos (cardinalidad) | Coherente con el tipo de variable | — | Igual al total de filas en una categórica → probablemente es un ID mal clasificado |
| Balance Binaria (%) | 40% – 60% (balanceada) | 60% – 80% | > 90% (clase muy desbalanceada, cuidado si vas a modelar) |

## 2. Duplicados (pestaña `4_Duplicados`)

| Métrica | ✅ Aceptable | 🔴 Alerta |
|---|---|---|
| Filas Duplicadas (%) | 0% | > 0% siempre amerita revisión manual — decide si son duplicados reales o coincidencias legítimas |

## 3. Forma de la distribución (pestaña `2_Desc_Numericas`)

| Métrica | ✅ Simétrica / normal | ⚠️ Sesgo moderado | 🔴 Sesgo fuerte |
|---|---|---|---|
| Skewness | -0.5 a 0.5 | -1 a -0.5 / 0.5 a 1 | < -1 o > 1 |
| Shapiro-Wilk Stat (W) | > 0.95 (cerca de 1) | 0.90 – 0.95 | < 0.90 |
| Shapiro p-valor (n < 300) | > 0.05 → normal | — | ≤ 0.05 → no normal |
| Shapiro p-valor (n > 300) | ⚠️ No confiar solo en esto — mira W y Skewness juntos, el p-valor casi siempre da < 0.05 con muestras grandes | | |

> **Regla rápida:** si `n > 300`, ignora el "Sí/No" del p-valor y decide con
> Skewness + W. Si ambos están en rango aceptable, trátala como
> aproximadamente normal para fines prácticos.

### 3.1 Media vs. Mediana (columnas `Sesgo (Etiqueta)` y `Medida Recomendada`)

Combina la etiqueta de sesgo (Skewness) con la categoría de Outliers IQR (%)
para recomendar qué medida de tendencia central es más representativa:

| Sesgo \ Outliers IQR | Bajo (<1%) | Medio (1-5%) | Alto (>5%) |
|---|---|---|---|
| Simétrica (\|s\|≤0.5) | **Media** | Indiferente | Mediana |
| Moderado (0.5<\|s\|≤1) | Indiferente | Mediana | Mediana |
| Fuerte (\|s\|>1) | Mediana | Mediana | Mediana |

La media solo se recomienda cuando la distribución es simétrica y casi no
hay valores extremos (usa toda la información, es más eficiente). En cuanto
aparece sesgo relevante o outliers relevantes, la mediana es más robusta
porque no se distorsiona con esos valores. "Indiferente" marca los casos
mixtos, donde una señal es buena y la otra regular.

## 4. Outliers (pestaña `2_Desc_Numericas`)

| Métrica | ✅ Aceptable | ⚠️ Revisar | 🔴 Alerta |
|---|---|---|---|
| Outliers IQR (%) | < 1% | 1% – 5% | > 5% (revisar si son errores o valores legítimos extremos) |
| Outliers Z-score (%) | < 1% | 1% – 5% | > 5% |
| IQR vs Z-score muy distintos entre sí | — | Normal con datasets pequeños o 1-2 valores extremos | Si divergen mucho con n grande, revisa la calidad del dato |

## 5. Dispersión (pestaña `2_Desc_Numericas`)

| Métrica | Cómo leerla |
|---|---|
| Coeficiente de Variación (Desv. Estándar / Media × 100) | < 15% = dato homogéneo · 15–30% = dispersión moderada · > 30% = dato muy heterogéneo (no viene calculado en el reporte, pero es fácil de sacar con estos dos valores) |
| IQR muy distinto a (Máximo - Mínimo) | Indica presencia de valores extremos que agrandan el rango sin representar a la mayoría de los datos |

## 6. Categóricas (pestaña `3_Desc_Categoricas`)

| Métrica | ✅ Aceptable | ⚠️ Revisar | 🔴 Alerta |
|---|---|---|---|
| Peso Moda (%) | < 50% (buena variedad) | 50% – 80% | > 80% (variable casi constante, poco útil para segmentar) |
| Categorías Distintas | Acorde al contexto | — | Muy alto (> 50) en una columna que debería ser pocas categorías → revisar inconsistencias de escritura (ej. "Bogota" vs "bogotá") |

---

### Cómo usar este checklist
Recorre el Excel columna por columna comparando cada valor contra esta tabla.
Si cae en 🔴, prioriza esa variable antes de seguir con análisis o modelos
posteriores — normalmente son las que más distorsionan resultados.
