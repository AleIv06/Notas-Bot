# UNI Noti-Notas Bot (v2.7)

**Herramienta de automatización en Python para el monitoreo de calificaciones en el portal INTRALU (UNI).**

Este proyecto automatiza el flujo de revisión de notas, eliminando la necesidad de ingresar manualmente al portal y descargar reportes repetitivamente.

## El Problema:
El portal universitario (INTRALU) presenta dos barreras para una consulta rápida:
1.  **Autenticación:** El login está protegido por **reCAPTCHA v3 invisible**, lo que dificulta la automatización tradicional con `requests` puro.
2.  **Datos no estructurados:** Las notas no están en una tabla HTML, sino dentro de un archivo PDF que debe generarse y descargarse en cada sesión.

##  La Solución Técnica
Se implementó una **arquitectura híbrida** que combina la interacción de navegador con peticiones HTTP directas para maximizar la velocidad:

### 1. Bypass de Autenticación (Selenium)
- El bot inicia una instancia de Chrome.
- El usuario realiza el login manual (necesario para validar el Captcha).
- El script detecta el ingreso exitoso y captura las **Cookies de Sesión**.

### 2. Extracción de Datos (Requests)
- Se realiza un *Session Handoff*: Las cookies capturadas se inyectan en una sesión de `requests`.
- Esto permite descargar el PDF directamente desde el servidor, evitando la sobrecarga de renderizado del navegador.

### 3. Parsing y Análisis (ETL)
- **Extracción:** `pdfplumber` lee el archivo PDF línea por línea.
- **Normalización:** Se utilizan **Expresiones Regulares (Regex)** para estructurar los datos (Cursos vs. Notas).
- **Detección de Cambios:** Compara el estado actual contra un archivo local `notas_viejas.json`.

### 4. Notificaciones (Telegram API)
Si se detecta una diferencia, se envía una alerta al usuario con indicadores visuales:
- 🔥 **Aprobado** (Nota >= 13)
- 💀 **Reprobado** (Nota < 13)

## Stack Tecnológico
- **Python 3.10+**
- **Selenium:** Gestión de navegador y cookies.
- **Requests:** Cliente HTTP para descarga eficiente.
- **PdfPlumber:** Extracción de texto de PDFs.
- **Regex:** Patrones de búsqueda de texto.

##  Instrucciones de Uso

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/AleIv06/Notas-Bot.git](https://github.com/AleIv06/Notas-Bot.git)
    cd uni-notinotas-bot
    ```

2.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuración:**
    Crea un archivo `config.py` en la raíz del proyecto con las siguientes variables:
    ```python
    LOGIN_URL = "..."
    PDF_URL = "..."
    HOME_URL = "..."
    TELEGRAM_TOKEN = "..."
    TELEGRAM_CHAT_ID = "..."
    ```

4.  **Ejecutar:**
    ```bash
    python bot.py
    ```

##  Nota de Desarrollo
Este proyecto implementa una metodología de **Programación Asistida por IA**.
- **Diseño y Lógica:** Arquitectura definida por el autor para resolver la persistencia de sesión y lectura de PDF.
- **Implementación:** Código iterado con LLMs (Gemini) para la generación de patrones Regex y manejo de excepciones en Selenium.