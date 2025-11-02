import time
import os
import pdfplumber
import requests
import json 
import re 
import sys

try:
    import config
except ImportError:
    print("Error: No se encontró el archivo 'config.py'.")
    print("Por favor, crea 'config.py' con tus URLs y tokens.")
    sys.exit(1) # Termina el script si no hay configuración

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

ARCHIVO_PDF_NUEVO = os.path.join(os.getcwd(), "notas_nuevas.pdf")
ARCHIVO_JSON_VIEJO = os.path.join(os.getcwd(), "notas_viejas.json") 

# Expresiones Regulares para el parseo v2.5
REGEX_CURSO = r"^[A-Z]{2,4}\d{3}[A-Z]\s+-\s+.+"
REGEX_EVAL = r"^(PRACTICA|LABORATORIO|EXAMEN|MONOGRAFIA)"
PALABRAS_CLAVE_NOTA = [
    "Once", "Cero", "Evaluación", "Trece", "Dieciocho", "Diez", "Cuatro",
    "Diecisiete", "Dieciséis", "Catorce", "Quince"
]

def enviar_alerta_telegram(mensaje):
    """
    Envía un mensaje formateado a un chat de Telegram.
    """
    print(f"Enviando alerta por Telegram...")
    url_telegram = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': config.TELEGRAM_CHAT_ID, 
        'text': mensaje, 
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url_telegram, data=payload)
        if response.status_code == 200:
            print("Alerta enviada con éxito.")
        else:
            print(f"Error al enviar alerta de Telegram: {response.text}")
    except Exception as e:
        print(f"Excepción al conectar con la API de Telegram: {e}")

def iniciar_sesion_asistida():
    """
    Abre Chrome y espera a que el usuario inicie sesión manualmente.
    Devuelve el objeto 'driver' si el login es exitoso.
    """
    print("Iniciando el navegador...")
    driver = webdriver.Chrome()
    driver.get(config.LOGIN_URL)
    print("ACCIÓN REQUERIDA: Por favor, inicie sesión en la ventana de Chrome.")
    print("El script esperará hasta que la URL cambie a la página de inicio...")
    
    try:
        # Espera un máximo de 5 minutos (300 seg) por el login manual
        WebDriverWait(driver, 300).until(
            EC.url_contains(config.HOME_URL)
        )
        print("Login exitoso. El bot toma el control.")
        return driver
    except Exception as e:
        print(f"Error: El login no se completó en el tiempo límite. {e}")
        driver.quit()
        return None

def descargar_pdf(driver):
    """
    Usa la sesión de Selenium (ya logueada) para descargar el PDF.
    """
    print(f"Navegando a la URL del PDF...")
    
    # Obtenemos las cookies de la sesión de Selenium
    cookies = driver.get_cookies()
    
    # Creamos una sesión de 'requests' para la descarga
    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])
        
    print("Descargando PDF de notas...")
    try:
        response = session.get(config.PDF_URL)
        
        if response.status_code == 200:
            with open(ARCHIVO_PDF_NUEVO, "wb") as f:
                f.write(response.content)
            print(f"PDF guardado como: {ARCHIVO_PDF_NUEVO}")
            return True
        else:
            print(f"Error al descargar el PDF. Código: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error en la descarga del PDF: {e}")
        return False

def parsear_notas_inteligente(pdf_path):
    """
    Parsea el PDF usando la lógica de máquina de estados v2.5.
    Extrae las notas en un diccionario.
    """
    print("Analizando PDF con lógica de parseo v2.5...")
    notas_limpias = {}
    curso_actual = None 
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                texto_pdf = page.extract_text()
                if not texto_pdf:
                    continue

                for line in texto_pdf.split('\n'):
                    line = line.strip()

                    # 1. ¿Es esta línea un TÍTULO DE CURSO?
                    if re.match(REGEX_CURSO, line):
                        curso_actual = line 
                        continue

                    # 2. ¿Es esta línea una NOTA (y ya tenemos un curso)?
                    if curso_actual and re.match(REGEX_EVAL, line):
                        partes = line.split()
                        
                        if len(partes) < 3:
                            continue 

                        # Busca el índice de la nota en letras
                        idx_nota_letra = -1
                        for i, parte in enumerate(partes):
                            if parte in PALABRAS_CLAVE_NOTA:
                                idx_nota_letra = i
                                break
                        
                        # Si encontramos la nota en letras, la nota numérica es la anterior
                        if idx_nota_letra > 0:
                            nota = partes[idx_nota_letra - 1]
                            
                            if nota.isdigit() and len(nota) <= 2:
                                tipo_evaluacion = " ".join(partes[:idx_nota_letra - 1])
                                clave = f"{curso_actual} | {tipo_evaluacion}"
                                notas_limpias[clave] = nota
        
        print(f"Análisis completado. Se encontraron {len(notas_limpias)} notas.")
        return notas_limpias
        
    except Exception as e:
        print(f"Error crítico al parsear el PDF: {e}")
        return None

def cargar_notas_json(file_path):
    """Carga el diccionario de notas viejas desde el archivo JSON."""
    if os.path.exists(file_path):
        print("Cargando notas antiguas desde JSON...")
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error: Archivo JSON corrupto. Se tratará como primera ejecución.")
            return {}
    else:
        print("No se encontró archivo JSON. Se asumirá primera ejecución.")
        return {} 

def guardar_notas_json(notas, file_path):
    """Guarda el nuevo diccionario de notas en el archivo JSON."""
    print("Guardando notas nuevas en JSON...")
    try:
        with open(file_path, "w") as f:
            json.dump(notas, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error al guardar el archivo JSON: {e}")

def comparar_notas(dict_nuevo, dict_viejo):
    """
    Compara los dos diccionarios de notas y decide si enviar alerta.
    Devuelve True si los datos nuevos deben guardarse.
    """
    if dict_nuevo is None or len(dict_nuevo) == 0:
        print("Error: No se encontraron notas en el PDF. No se comparará.")
        return False # No guardar un diccionario vacío

    if not dict_viejo: 
        print("Es la primera ejecución. Guardando línea base de notas.")
        enviar_alerta_telegram(
            "Bot de Notas (v2.6) configurado.\n"
            "Se ha guardado tu reporte de notas actual. "
            "Se te notificará cuando se detecte un cambio."
        )
        return True # Guardar
    
    if dict_nuevo == dict_viejo:
        print("Sin cambios. Tus notas siguen exactamente igual.")
        return False # No es necesario volver a guardar lo mismo
    
    # Si llegamos aquí, ¡hay cambios!
    print("¡ALERTA! Se detectaron cambios en las notas.")
    
    mensaje_alerta = "🚨 *ALERTA DE NOTAS (v2.6)* 🚨\n\nSe detectaron cambios:\n\n"
    cambios_encontrados = False
    
    # 1. Buscar notas cambiadas o nuevas
    for clave, nota_nueva in dict_nuevo.items():
        nota_vieja = dict_viejo.get(clave, "N/A") # "N/A" si la nota es nueva
        
        if nota_nueva != nota_vieja:
            cambios_encontrados = True
            partes_clave = clave.split(" | ")
            if len(partes_clave) == 2:
                # Extrae solo el nombre del curso, no el código
                curso_nombre = partes_clave[0].split(" - ", 1)[-1].strip() 
                eval_nombre = partes_clave[1]
                
                mensaje_alerta += f"*{curso_nombre}*\n"
                mensaje_alerta += f"  - {eval_nombre}: `{nota_vieja}` ➡️ `{nota_nueva}`\n\n"
            
    # 2. Buscar notas eliminadas (si una nota existía pero ya no)
    for clave in dict_viejo:
        if clave not in dict_nuevo:
            # (Esta lógica se puede implementar si es necesario)
            cambios_encontrados = True

    if not cambios_encontrados:
        mensaje_alerta = (
            "El formato del reporte cambió (quizás un curso nuevo o eliminado), "
            "pero las notas existentes están iguales. Se recomienda revisar."
        )

    enviar_alerta_telegram(mensaje_alerta)
    return True # Guardar los nuevos cambios


def main():
    """Punto de entrada principal del script."""
    
    dict_notas_viejo = cargar_notas_json(ARCHIVO_JSON_VIEJO)
    
    driver = iniciar_sesion_asistida()
    if not driver:
        print("Proceso de login fallido. Terminando.")
        return

    if descargar_pdf(driver):
        driver.quit()
        
        dict_notas_nuevo = parsear_notas_inteligente(ARCHIVO_PDF_NUEVO)
        
        if comparar_notas(dict_notas_nuevo, dict_notas_viejo):
            guardar_notas_json(dict_notas_nuevo, ARCHIVO_JSON_VIEJO)
    else:
        driver.quit()
        print("No se pudo descargar el PDF. Terminando.")

if __name__ == "__main__":
    main()

