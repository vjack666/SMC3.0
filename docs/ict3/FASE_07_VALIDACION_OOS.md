# Fase 7 — Simulación y validación fuera de muestra

## Orden de trabajo para los agentes

**Mandato.** Mide estados y cobertura del motor con una evaluación cronológica reproducible.

1. **Agente de datos.** Genera un inventario por activo y marco con alias, fuente, primer y último cierre, cantidad de velas y huecos. Identifica cobertura común y registra cada exclusión. Mide M1 por separado cuando esté disponible. Mantén datos y credenciales privados fuera del informe.
2. **Agente de simulación.** Registra la fecha que separa calibración de validación, los parámetros congelados y el comando de ejecución. Reproduce por cortes causales y agrupa por símbolo, PDH/PDL, sesión, tipo de POI y estado. Reporta denominadores y cobertura efectiva.
3. **Agente de revisión.** Reproduce una muestra con el comando publicado y verifica invariancia por prefijos alrededor de transiciones. Inspecciona cómo se cuentan ventanas incompletas y comprueba que calibración y evaluación permanecen separadas.
4. **Entregable de Hermes.** Informe y tablas agregadas con fechas, cobertura y ejemplos auditables. Aceptación: otra persona puede reproducir los conteos con las mismas fuentes. Los resultados se limitan a estados observados y su frecuencia.

## Objetivo
Medir la representación causal, no afirmar rentabilidad.

## Trabajo
- Repetir cobertura de 26 pares y cuatro índices con universo declarado.
- Separar calibración y evaluación fuera de muestra.
- Desglosar nivel, sesión, HTF, POI, ventana y estado final.
- Verificar `prefix_to_t == full_series_at_t`.
- Reportar errores por símbolo/feed/cobertura.
- No calcular fills, lotaje, P&L ni curva de capital.

## Delegación y aceptación
Delegar datos/cobertura, replay/simulación y auditoría estadística. El informe debe ser reproducible y no convertir conteos en ventaja estadística.
