# Avisos de progreso de SURI

Este repositorio consulta el porcentaje del proyecto **SURI** en PortWatch VI cada 10 minutos desde GitHub Actions. No necesita que tu ordenador esté encendido. Envía una notificación push a ntfy únicamente cuando el porcentaje sube.

## Activación

1. Instala ntfy desde Google Play y suscríbete al tema privado que se configuró para este monitor.
2. En este repositorio abre **Settings → Secrets and variables → Actions → New repository secret**.
3. Crea un secreto llamado `NTFY_TOPIC` con el tema de ntfy. No lo guardes en archivos públicos.
4. En **Actions** puedes ejecutar **Probar notificación móvil** para mandar un simulacro o **Vigilar progreso de SURI** para una comprobación manual.

## Cómo son las alertas

- Emblema personalizado SURI en PNG, servido desde este repositorio.
- Título con la subida y el nuevo valor.
- Cuerpo con Markdown: encabezados, negritas, cursiva, listas, enlaces y separadores.
- Barra visual de progreso y resumen de hito, FPS, renderizado, historia y estabilidad.
- Prioridad alta, etiquetas visuales y enlace a la ficha de SURI.
- Acciones rápidas para abrir la ficha, copiar el porcentaje y consultar la metodología.

La app Android de ntfy necesita una versión que incluya compatibilidad con Markdown (v1.17.8 o posterior).

## Qué vigila

Lee `https://portwatch-vi.xyz/data/tracker.json`, busca únicamente el proyecto cuyo id es `suri` y reproduce el cálculo de puntuación que usa PortWatch. El valor inicial guardado fue **61,0 %**. Solo se avisa cuando el valor aumenta; los descensos actualizan la referencia sin mandar avisos.

La puntuación se publica con una precisión de una décima. El monitor detecta cualquier subida que el tracker llegue a reflejar (por ejemplo, de 61,0 a 61,1).

## Frecuencia y limitaciones

- GitHub Actions solicita una comprobación cada 10 minutos.
- GitHub puede retrasar trabajos programados en horas de mucha carga; no es una garantía de ejecución exacta al minuto.
- PortWatch publica sus datos aproximadamente cada 3 horas. Consultar cada 10 minutos no adelanta esa publicación.
- El repositorio es público para utilizar los runners estándar gratuitos de GitHub Actions.
- GitHub puede desactivar workflows programados de repositorios públicos tras 60 días sin actividad; si ocurre, hay que volver a habilitarlo desde Actions.

## Seguridad

El tema ntfy funciona como una contraseña: quien lo conozca puede publicar o suscribirse. Por eso usamos un nombre aleatorio largo y lo guardamos como secreto de GitHub. No publiques ese nombre en el repositorio.
