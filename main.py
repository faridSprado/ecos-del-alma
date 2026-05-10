from datetime import datetime
import json
import os
from dotenv import load_dotenv
from groq import Groq
from agentes.agentes import agente_poeta, agente_guardian, agente_visualizador

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODELO = "llama-3.3-70b-versatile"

# Cargar guía
with open('biblia/guia_estilo.json', 'r', encoding='utf-8') as f:
    GUIA = json.load(f)

# Memoria de publicación
MEMORIA_PATH = 'memoria/estado_publicacion.json'
try:
    with open(MEMORIA_PATH, 'r', encoding='utf-8') as f:
        memoria = json.load(f)
except FileNotFoundError:
    memoria = {
        "ultimo_id": 0,
        "fecha_ultima_publicacion": "",
        "publicaciones": []
    }

# --- Flujo de agentes ---
relato_ok = False
intentos = 0
max_intentos = 3

while not relato_ok and intentos < max_intentos:
    intentos += 1
    texto, tema = agente_poeta()
    texto_final, es_valido = agente_guardian(texto, tema)
    if es_valido:
        relato_ok = True
        print("🎉 Texto aprobado.")
    else:
        print(f"⏳ Reintentando ({intentos}/{max_intentos})...")

if not relato_ok:
    raise Exception("No se logró un texto válido.")

# --- Publicar ---
hoy = datetime.now().strftime("%Y-%m-%d")
nuevo_id = memoria['ultimo_id'] + 1
titulo_archivo = f"escrito-{nuevo_id:04d}_{hoy}.md"
ruta_publicacion = f"docs/_posts/{titulo_archivo}"

# Generar ilustración
url_ilustracion = None
try:
    url_ilustracion, _ = agente_visualizador(texto_final)
except Exception as e:
    print(f"⚠️ Fallo al generar imagen: {e}")

# Construir Markdown
contenido_md = f"""---
layout: post
title: "{tema['nombre']} - {hoy}"
date: {hoy} 08:00:00 -0000
categories: ecos-del-alma
---

{texto_final}

"""

if url_ilustracion:
    contenido_md += f"![Ilustración]({url_ilustracion})\n\n"

contenido_md += f"*Tema: {tema['nombre']} | Generado autónomamente por Ecos del Alma*"

os.makedirs(os.path.dirname(ruta_publicacion), exist_ok=True)
with open(ruta_publicacion, 'w', encoding='utf-8') as f:
    f.write(contenido_md)
print(f"📄 Publicado en {ruta_publicacion}")

# Actualizar memoria
memoria['ultimo_id'] = nuevo_id
memoria['fecha_ultima_publicacion'] = hoy
memoria['publicaciones'].append({
    "id": nuevo_id,
    "fecha": hoy,
    "tema": tema['nombre']
})

with open(MEMORIA_PATH, 'w', encoding='utf-8') as f:
    json.dump(memoria, f, indent=2, ensure_ascii=False)
print("🧠 Memoria de publicación actualizada.")