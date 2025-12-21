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
    sys.exit(1) #Termina el script si no hay configuración

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

ARCHIVO_PDF_NUEVO = os.path.join(os.getcwd(), "notas_nuevas.pdf")
ARCHIVO_JSON_VIEJO = os.path.join(os.getcwd(), "notas_viejas.json") 

#Expresiones para el parseo, lo usamos ya que cada encabezado tiene un codigo de curso
REGEX_CURSO = r"^[A-Z]{2,4}\d{2,3}[A-Z]?\s+-\s+.+"
#Nos serviran para saber el tipo de evaluacion
REGEX_EVAL = r"^(PRACTICA|LABORATORIO|EXAMEN|MONOGRAFIA)"
#Nos serviran para detectar la nota
PALABRAS_CLAVE_NOTA = [
    "Cero", "Uno", "Dos", "Tres", "Cuatro", "Cinco", 
    "Seis", "Siete", "Ocho", "Nueve", "Diez", 
    "Once", "Doce", "Trece", "Catorce", "Quince", 
    "Dieciséis", "Diecisiete", "Dieciocho", "Diecinueve", "Veinte",
    "Evaluación" #Para evaluación no rendida
]

def enviar_alerta_telegram(mensaje):
    print(f"Enviando alerta por Telegram...")
    #aqui definimos la url del bot para poder utilizarlo
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
    print("Iniciando el navegador...")
    driver = webdriver.Chrome()
    driver.get(config.LOGIN_URL)
    print("Accion requerida: inicie sesión en la ventana de chrome.")
    
    try:
        #Se espera hasta un maximo de 300 segundos
        WebDriverWait(driver, 300).until(EC.url_contains(config.HOME_URL))
        print("Login exitoso. El bot toma el control.")
        return driver
    except Exception as e:
        print(f"Error: El login no se completó en el tiempo límite. {e}")
        driver.quit()
        return None
#aqui usaremos request ya que selenium es bastante lento para realizar esta descarga
def descargar_pdf(driver):
    print(f"Navegando a la URL del PDF...")
    #request utiliza las cookies de sesion conseguidas por selenium
    cookies = driver.get_cookies()
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
    print("Analizando PDF (v2.7)...")
    notas_limpias = {}
    curso_actual = None 
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                texto_pdf = page.extract_text()
                if not texto_pdf: continue

                for line in texto_pdf.split('\n'):
                    line = line.strip()

                    if re.match(REGEX_CURSO, line):
                        curso_actual = line 
                        continue

                    #Detectar Nota
                    if curso_actual and re.match(REGEX_EVAL, line):
                        partes = line.split()
                        if len(partes) < 3: continue 

                        #Buscar palabras claves
                        idx_nota_letra = -1
                        for i, parte in enumerate(partes):
                            parte_limpia = parte.replace(',', '').replace('.', '')
                            if parte_limpia in PALABRAS_CLAVE_NOTA:
                                idx_nota_letra = i
                                break
                        
                        # Si encontramos la palabra, el número es el anterior
                        if idx_nota_letra > 0:
                            nota = partes[idx_nota_letra - 1]
                            if nota.isdigit() and len(nota) <= 2:
                                tipo_evaluacion = " ".join(partes[:idx_nota_letra - 1])
                                clave = f"{curso_actual} | {tipo_evaluacion}"
                                notas_limpias[clave] = nota
        
        print(f"Análisis completado. Se encontraron {len(notas_limpias)} notas.")
        return notas_limpias
    except Exception as e:
        print(f"Error al parsear: {e}")
        return None

def cargar_notas_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return {}

def guardar_notas_json(notas, file_path):
    with open(file_path, "w") as f:
        json.dump(notas, f, indent=4, ensure_ascii=False)

def comparar_notas(dict_nuevo, dict_viejo):
    if not dict_nuevo: return False

    if not dict_viejo: 
        print("Primera ejecución. Guardando línea base.")
        enviar_alerta_telegram("🤖 Bot v2.7 configurado. Notas guardadas.")
        return True
    
    if dict_nuevo == dict_viejo:
        print("✅ Sin cambios.")
        return False 
    
    print("🚨 ¡Cambios detectados!")
    mensaje_alerta = "🚨 *ALERTA DE NOTAS* 🚨\n\n"
    cambios = False
    
    for clave, nota_nueva in dict_nuevo.items():
        nota_vieja = dict_viejo.get(clave, "N/A")
        
        if nota_nueva != nota_vieja:
            cambios = True
            partes = clave.split(" | ")
            curso = partes[0].split(" - ", 1)[-1].strip()
            evaluacion = partes[1]
            
            mensaje_alerta += f"*{curso}*\n  - {evaluacion}: `{nota_vieja}` ➡️ `{nota_nueva}`"
            
            try:
                # Convertimos a entero para comparar
                valor_nota = int(nota_nueva) 
                
                if valor_nota >= 13:
                    mensaje_alerta += " 🔥" 
                else:
                    mensaje_alerta += " 💀"
            except ValueError:
                #por si la nota es nsp
                mensaje_alerta += " ⚠️"
            
            mensaje_alerta += "\n\n"

    if cambios:
        enviar_alerta_telegram(mensaje_alerta)
    return True

def main():
    driver = iniciar_sesion_asistida()
    if not driver: return

    if descargar_pdf(driver):
        driver.quit()
        dict_nuevo = parsear_notas_inteligente(ARCHIVO_PDF_NUEVO)
        dict_viejo = cargar_notas_json(ARCHIVO_JSON_VIEJO)
        
        if dict_nuevo and comparar_notas(dict_nuevo, dict_viejo):
            guardar_notas_json(dict_nuevo, ARCHIVO_JSON_VIEJO)
    else:
        driver.quit()

if __name__ == "__main__":
    main()

