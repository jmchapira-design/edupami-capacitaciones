import os
import re
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Lista de IDs / URLs oficiales a monitorear
CURSOS_IDS = [
    8937, 8939, 8944, 8942, 8946, 8947, 8948, 
    8941, 8940, 8943, 8949, 8945, 8952, 8951
]

BASE_URL = "https://edupami.pami.org.ar/portal/curso.php?curso={}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extraer_curso(curso_id):
    url = BASE_URL.format(curso_id)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"Error {resp.status_code} al consultar ID {curso_id}")
            return None

        soup = BeautifulSoup(resp.content, "html.parser")
        
        # 1. Título y Edición
        titulo_tag = soup.find("h1")
        titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Sin título"
        
        edicion_tag = soup.find(string=re.compile(r"edición", re.IGNORECASE))
        edicion = edicion_tag.strip() if edicion_tag else "N/D"

        # 2. Horas para Carrera Administrativa
        horas_tag = soup.find(string=re.compile(r"horas?", re.IGNORECASE))
        horas = horas_tag.strip() if horas_tag else "N/D"

        # 3. Objetivo / Resumen
        objetivo = "N/D"
        obj_header = soup.find(string=re.compile(r"Objetivo del curso", re.IGNORECASE))
        if obj_header:
            p_obj = obj_header.find_next("p")
            if p_obj:
                objetivo = p_obj.get_text(strip=True)

        # 4. Extracción de bloques de información técnica (fechas, disposición, etc.)
        texto_completo = soup.get_text(separator=" \n ")

        # Fechas de Inscripción
        insc_ini = re.search(r"Inscripción\s*Inicio:\s*([\d/]+)", texto_completo, re.I)
        insc_fin = re.search(r"Cierre:\s*([\d/]+)", texto_completo, re.I)
        
        # Fechas de Cursada
        curso_ini = re.search(r"Curso\s*Inicio:\s*([\d/]+)", texto_completo, re.I)
        curso_fin = re.search(r"Fin:\s*([\d/]+)", texto_completo, re.I)

        # Disposición
        dispo = re.search(r"Disposición\s*([\d/\w]+)", texto_completo, re.I)

        # Modalidad y Categoría
        modalidad = re.search(r"Modalidad\s*([^\n]+)", texto_completo, re.I)
        categoria = re.search(r"Categoría\s*([^\n]+)", texto_completo, re.I)
        contacto = re.search(r"Contacto\s*([^\n]+)", texto_completo, re.I)

        return {
            "id_curso": curso_id,
            "url": url,
            "titulo": titulo,
            "edicion": edicion,
            "horas_carrera_admin": horas,
            "inscripcion_inicio": insc_ini.group(1).strip() if insc_ini else "N/D",
            "inscripcion_cierre": insc_fin.group(1).strip() if insc_fin else "N/D",
            "cursada_inicio": curso_ini.group(1).strip() if curso_ini else "N/D",
            "cursada_fin": curso_fin.group(1).strip() if curso_fin else "N/D",
            "disposicion": dispo.group(1).strip() if dispo else "N/D",
            "modalidad": modalidad.group(1).strip() if modalidad else "E-Learning",
            "categoria": categoria.group(1).strip() if categoria else "General",
            "contacto_tutor": contacto.group(1).strip() if contacto else "N/D",
            "objetivo": objetivo
        }

    except Exception as e:
        print(f"Error procesando curso {curso_id}: {e}")
        return None

def main():
    os.makedirs("data", exist_ok=True)
    resultados = []

    print("Iniciando extracción de EduPAMI...")
    for cid in CURSOS_IDS:
        print(f"-> Extrayendo ID {cid}...")
        datos = extraer_curso(cid)
        if datos:
            resultados.append(datos)

    # 1. Guardar JSON
    with open("data/capacitaciones.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    # 2. Guardar CSV (Excel)
    df = pd.DataFrame(resultados)
    df.to_csv("data/capacitaciones.csv", index=False, encoding="utf-8-sig")

    # 3. Actualizar README.md con la tabla de cursos
    markdown_table = df[[
        "titulo", "horas_carrera_admin", "inscripcion_inicio", 
        "inscripcion_cierre", "cursada_inicio", "cursada_fin", "disposicion"
    ]].rename(columns={
        "titulo": "Curso",
        "horas_carrera_admin": "Horas C.A.",
        "inscripcion_inicio": "Insc. Inicio",
        "inscripcion_cierre": "Insc. Cierre",
        "cursada_inicio": "Cursada Inicio",
        "cursada_fin": "Cursada Fin",
        "disposicion": "Disposición"
    }).to_markdown(index=False)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# 📚 Monitor de Capacitaciones EduPAMI\n\n")
        f.write("> **Última sincronización automática:** Información extraída directamente de las fichas de EduPAMI.\n\n")
        f.write("### 📋 Oferta Vigente y Acreditación de Horas\n\n")
        f.write(markdown_table if markdown_table else "No hay cursos registrados.")
        f.write("\n\n---\n*Archivos de datos:* [`data/capacitaciones.json`](data/capacitaciones.json) | [`data/capacitaciones.csv`](data/capacitaciones.csv)")

    print("¡Extracción y actualización completada con éxito!")

if __name__ == "__main__":
    main()
