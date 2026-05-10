import json
import os
from dotenv import load_dotenv
from groq import Groq
from urllib.parse import quote

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODELO = "llama-3.3-70b-versatile"

# Cargar la guía de estilo (antes canon)
with open('biblia/guia_estilo.json', 'r', encoding='utf-8') as f:
    GUIA = json.load(f)

# Memoria simple: llevará un registro de temas usados recientemente para variar
MEMORIA_TEMAS_PATH = 'memoria/temas_usados.json'
try:
    with open(MEMORIA_TEMAS_PATH, 'r', encoding='utf-8') as f:
        temas_usados = json.load(f)
except FileNotFoundError:
    temas_usados = {"ultimos_temas": []}
    with open(MEMORIA_TEMAS_PATH, 'w', encoding='utf-8') as f:
        json.dump(temas_usados, f)

# --- Agente 1: El Poeta ---
def agente_poeta():
    print("🖋️ El Poeta comienza a escribir...")
    
    # Seleccionar un tema al azar, evitando los dos últimos para variedad
    temas_disponibles = GUIA['temas']
    ultimos = temas_usados['ultimos_temas']
    temas_filtrados = [t for t in temas_disponibles if t['nombre'] not in ultimos]
    import random
    tema_elegido = random.choice(temas_filtrados if temas_filtrados else temas_disponibles)
    
    # Actualizar memoria de temas
    ultimos.append(tema_elegido['nombre'])
    if len(ultimos) > 2:
        ultimos.pop(0)
    temas_usados['ultimos_temas'] = ultimos
    with open(MEMORIA_TEMAS_PATH, 'w', encoding='utf-8') as f:
        json.dump(temas_usados, f)
    
    print(f"   Tema elegido: {tema_elegido['nombre']}")

    system_prompt = f"""
Eres 'El Poeta', creador de 'Ecos del Alma'. Escribirás un texto poético breve siguiendo esta guía estricta:

## REGLAS DE ESTILO
- Género: {GUIA['tono_estilo']['genero']}
- Longitud: {GUIA['tono_estilo']['longitud']}
- Recursos permitidos: {', '.join(GUIA['tono_estilo']['recursos_permitidos'])}
- PROHIBIDO: {', '.join(GUIA['tono_estilo']['prohibido'])}
- Restricción especial: {GUIA['restriccion_adicional']}

## TEMA DEL DÍA
Nombre: {tema_elegido['nombre']}
Descripción: {tema_elegido['descripcion']}

## ESTRUCTURA
{chr(10).join(GUIA['estructura_poetica'])}

Escribe SOLO el texto poético, sin título ni firma. Debe ser auténtico, sin caer en frases hechas. Usa imágenes sensoriales concretas.
"""
    
    response = client.chat.completions.create(
        model=MODELO,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Escribe un texto sobre el tema: {tema_elegido['nombre']}."}
        ],
        temperature=0.95,
        max_tokens=300
    )
    texto = response.choices[0].message.content.strip()
    print(f"✅ Texto generado: {texto[:60]}...")
    return texto, tema_elegido

# --- Agente 2: El Guardián de la Emoción ---
def agente_guardian(texto, tema):
    print("🛡️ El Guardián de la Emoción revisa...")
    
    check_prompt = f"""
Eres un editor sensible. Revisa este texto poético y evalúa si cumple la calidad emocional.
Tema: {tema['nombre']} - {tema['descripcion']}

## CRITERIOS DE CALIDAD
1. ¿Evita clichés y frases hechas?
2. ¿Usa imágenes sensoriales concretas (no solo conceptos abstractos)?
3. ¿La emoción se siente genuina, no forzada?
4. ¿Cumple la restricción especial: "{GUIA['restriccion_adicional']}"?
5. ¿Respeta la longitud y el tono definidos?

## TEXTO A EVALUAR
{texto}

Responde ÚNICAMENTE con JSON:
{{
  "es_valido": true/false,
  "violaciones": ["descripción de cada violación encontrada"],
  "puntuacion_emocional": 1-10
}}
"""
    response = client.chat.completions.create(
        model=MODELO,
        messages=[{"role": "user", "content": check_prompt}],
        temperature=0.0,
        max_tokens=200
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    resultado = json.loads(raw)
    
    if resultado['es_valido'] and resultado.get('puntuacion_emocional', 0) >= 6:
        print(f"✅ Aprobado (puntuación emocional: {resultado['puntuacion_emocional']}/10)")
        return texto, True
    else:
        print(f"❌ Rechazado: {resultado['violaciones']}")
        return resultado['violaciones'], False

# --- Agente 3: El Visualizador (imágenes abstractas/atmosféricas) ---
def agente_visualizador(texto):
    print("🎨 El Visualizador crea la ilustración...")
    
    prompt_visual = client.chat.completions.create(
        model=MODELO,
        messages=[{
            "role": "user",
            "content": f"""Crea un prompt en INGLÉS para generar una imagen artística que acompañe este texto poético. 
Estilo: minimalista, aesthetic, tonos pastel o blanco y negro, textura de papel o acuarela ligera, sin rostros, sin texto en la imagen.
Basado en: {texto[:200]}
Solo el prompt, máximo 60 palabras."""
        }],
        temperature=0.8,
        max_tokens=100
    )
    prompt_imagen = prompt_visual.choices[0].message.content.strip()
    print(f"   Prompt visual: {prompt_imagen[:80]}...")
    
    imagen_url = f"https://image.pollinations.ai/prompt/{quote(prompt_imagen)}?width=1080&height=1080&nologo=true"
    print(f"✅ Ilustración creada: {imagen_url}")
    return imagen_url, prompt_imagen