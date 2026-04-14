# Análisis CDR Clínica Dental — Informe Ejecutivo

> Informe generado a partir del análisis de 500 llamadas entrantes.
> Modo demo — generado sin IA. Ejecuta con API Key para obtener análisis con IA.

## Resumen ejecutivo

La clínica recibió **500 llamadas entrantes externas** durante el periodo analizado, 
con una tasa de contestación del **83.4%** y una duración media de conversación de 
**2.6 minutos**. Un total de **500 llamantes únicos** contactaron 
con la clínica, con una media de **25.0 llamadas diarias**. 
El **0.0%** de las llamadas fueron derivadas al buzón de voz.

## Hallazgos clave

1. **Tasa de contestación: 83.4%** — Por encima del benchmark del sector sanitario (80%).
2. **Tasa de pérdida: 16.6%** — 83 llamantes no pudieron contactar con la clínica.
3. **Buzón de voz: 0.0%** — 0 llamadas fueron derivadas al buzón cuando nadie pudo atender.
4. **Duración media: 2.6 min** — Dentro del rango esperado para llamadas de clínica dental (pedir cita, confirmar, consultar dirección).
5. **Volumen diario: 25.0 llamadas/día** — Requiere cobertura dedicada de recepción durante horario comercial.

## Problemas detectados

### 📊 Moderada tasa de llamadas perdidas (16.6%)
Cada llamada perdida es un paciente potencial que puede reservar con la competencia. 
Con un valor medio estimado de 150-300€ por primera visita, incluso un 16.6% 
de pérdida representa un impacto significativo en facturación.

### Congestión en horas punta
La distribución horaria muestra picos de volumen concentrados en franjas específicas. 
El personal de recepción puede verse desbordado en estos picos mientras está infrautilizado 
en los valles.

### Derivación a buzón de voz (0.0%)
Las llamadas al buzón de voz indican que la recepción no da abasto en ciertos momentos. 
Muchos pacientes no dejan mensaje y simplemente cuelgan, lo que equivale a una llamada perdida.

## Recomendaciones accionables

1. **Implementar un sistema de callback** para llamadas perdidas en horas punta — esto recupera 
   hasta un 60% de llamadas perdidas según datos del sector sanitario.
2. **Revisar plantilla en horas punta** — asegurar cobertura adecuada de recepción 
   durante las franjas con más tráfico identificadas en el análisis horario.
3. **Configurar un IVR básico** (respuesta automática) para consultas frecuentes 
   (dirección, horario), liberando a recepción para gestión de citas.
4. **Monitorizar tendencias semanales** — usar esta herramienta de análisis periódicamente 
   para comprobar si los cambios de personal o procesos mejoran la tasa de contestación.

## Próximos pasos

- Ejecutar este análisis mensualmente para detectar tendencias.
- Cruzar llamadas perdidas con datos de reservas para cuantificar el impacto en facturación.
- Analizar patrones de duración para detectar oportunidades de eficiencia.
- Valorar la implementación de citas online para reducir la dependencia del teléfono.

---
*Informe generado por Dental Clinic CDR Analyzer — [github.com/vjsoriano83/dental-clinic-cdr-analyzer](https://github.com/vjsoriano83/dental-clinic-cdr-analyzer)*
