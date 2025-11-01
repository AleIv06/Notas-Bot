# Notas-Bot
Noti-Notas Bot

Este es un bot personal de automatización en Python que creé para resolver un problema: revisar el portal de notas de mi universidad (UNI) y comparar un PDF manualmente.

El Problema:

El portal de la UNI (INTRALU) requiere un login manual (protegido por reCAPTCHA v3 invisible) y la descarga de un PDF cada vez que quiero ver si un profesor ha subido una nueva calificación. Este proceso es lento y lo repetía varias veces al día.

La Solución:

Creé un script de "automatización asistida" (v2.5) que hace todo el trabajo por mí. El bot usa Selenium para abrir una ventana de Chrome. Yo realizo el login manualmente (necesario para pasar el reCAPTCHA v3).
Una vez logueado, el bot toma el control. Pasa las cookies de sesión a Requests para descargar el PDF de notas de forma eficiente.
Usa PdfPlumber para leer el PDF y, usando una lógica de "máquina de estados" (parseo línea por línea), extrae solo los cursos y sus notas.
Compara este nuevo diccionario de notas con un archivo notas_viejas.json guardado localmente.
Si detecta un cambio real en una nota (ignorando los "falsos positivos" como la fecha exacta del pdf), me envía una alerta instantánea a mi celular usando la API de Telegram.

Tecnologías Utilizadas:

Python 3
Selenium: Para la automatización del navegador y el login asistido.
Requests: Para manejar la sesión y descargar el PDF.
PdfPlumber: Para extraer el texto del PDF.
JSON: Para guardar la "línea base" de las notas.
re (Expresiones Regulares): Para el parseo del texto.
Venv: Para la gestión del entorno de desarrollo en Ubuntu.
(Asistido por Gemini AI para la depuración y desarrollo del código base)
