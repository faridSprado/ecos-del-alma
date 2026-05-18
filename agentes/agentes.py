import json
import random
import re
import unicodedata
from typing import Any
from urllib.parse import quote

from groq import Groq

from config import BIBLIA_PATH, GROQ_API_KEY, GROQ_MODEL, PROJECT_NAME


if not GROQ_API_KEY:
    raise RuntimeError(
        "Falta GROQ_API_KEY. Crea un archivo .env local o configura el secret en GitHub Actions."
    )

client = Groq(api_key=GROQ_API_KEY)


def cargar_guia() -> dict[str, Any]:
    with open(BIBLIA_PATH, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


GUIA = cargar_guia()

# Palabras o marcas típicas que no deberían aparecer en el texto final.
# No pretende ser un detector lingüístico perfecto; funciona como filtro preventivo
# y como disparador para una corrección adicional cuando aparece algo raro.
ENGLISH_WORDS = {
    "outside",
    "inside",
    "window",
    "street",
    "silence",
    "memory",
    "memories",
    "coffee",
    "comfort",
    "goodbye",
    "grief",
    "farewell",
    "hands",
    "hand",
    "light",
    "shadow",
    "room",
    "dust",
    "sunlight",
    "lonely",
    "empty",
    "call",
    "heart",
    "soul",
}

ENGLISH_MARKERS = [
    "outside",
    "inside",
    "window",
    "street",
    "silence",
    "memory",
    "coffee",
    "comfort",
    "goodbye",
    "farewell",
    "sunlight",
]

HUMANIZER_REGLAS = (
    "Suena a una persona pensando, no a una plantilla.",
    "Usa detalles materiales concretos y evita símbolos inflados.",
    "No cierres con moralejas ni frases motivacionales.",
    "Evita gerundios en cadena, tríos mecánicos y fórmulas como 'no es solo'.",
    "Prefiere verbos simples, ritmo variado y una emoción contenida.",
)


def _lista_guia(clave: str) -> list[str]:
    valores = GUIA.get(clave, [])
    return valores if isinstance(valores, list) else []


def limpiar_respuesta(texto: str) -> str:
    texto = texto.strip()
    if texto.startswith("```"):
        partes = texto.split("```")
        if len(partes) >= 2:
            texto = partes[1].strip()
            if texto.lower().startswith("json"):
                texto = texto[4:].strip()
    return texto.strip().strip('"').strip()


def extraer_json(texto: str) -> dict[str, Any]:
    limpio = limpiar_respuesta(texto)
    try:
        return json.loads(limpio)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", limpio, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def normalizar_token(token: str) -> str:
    token = unicodedata.normalize("NFKD", token)
    token = "".join(ch for ch in token if not unicodedata.combining(ch))
    return token.lower()



def detectar_tokens_sospechosos(texto: str) -> list[str]:
    tokens = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", texto)
    sospechosos: list[str] = []

    for token in tokens:
        token_sin_tildes = normalizar_token(token)

        # Caso tipo calleOutside, almaInside, etc.
        if re.search(r"[a-záéíóúüñ]+[A-Z][a-zA-ZÁÉÍÓÚÜÑáéíóúüñ]*", token):
            sospechosos.append(token)
            continue

        if token_sin_tildes in ENGLISH_WORDS:
            sospechosos.append(token)
            continue

        for marker in ENGLISH_MARKERS:
            if marker in token_sin_tildes and token_sin_tildes != marker:
                sospechosos.append(token)
                break

    # Evita duplicados y conserva el orden.
    vistos = set()
    salida = []
    for token in sospechosos:
        if token not in vistos:
            vistos.add(token)
            salida.append(token)
    return salida


def detectar_motivos_bloqueados(texto: str) -> list[str]:
    motivos = [normalizar_token(item) for item in _lista_guia("motivos_bloqueados")]
    if not motivos:
        return []

    tokens = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", texto)
    encontrados: list[str] = []

    for token in tokens:
        normalizado = normalizar_token(token)
        if normalizado in motivos and normalizado not in encontrados:
            encontrados.append(normalizado)

    return encontrados



def corregir_idioma(texto: str, tema: dict[str, str]) -> str:
    """
    Hace una pasada de seguridad para que el texto quede completamente en español.
    Si aparece una palabra en inglés, spanglish o un token extraño, la corrige sin
    cambiar el tono del texto.
    """

    prompt = f"""
Eres un corrector editorial de estilo literario.

Tu única tarea es revisar el siguiente texto y dejarlo completamente en español neutro.
No lo resumas ni lo reescribas por completo.
Corrige solo lo necesario para que quede limpio y natural.

Reglas:
- El resultado debe estar total y completamente en español.
- No puede quedar ninguna palabra en inglés.
- No puede quedar spanglish.
- No puede quedar camelCase ni tokens raros incrustados dentro de palabras.
- Conserva el tono íntimo, la voz y la estructura original.
- No agregues título.
- No agregues comillas.
- Devuelve solo el texto final corregido.

Tema: {tema['nombre']}

Texto:
{texto}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=420,
    )

    corregido = limpiar_respuesta(response.choices[0].message.content or "")
    return corregido or texto



def asegurar_texto_en_espanol(texto: str, tema: dict[str, str]) -> str:
    """
    Aplica una corrección editorial y valida que no queden tokens sospechosos.
    Si todavía encuentra restos extraños, hace un segundo intento más estricto.
    """

    texto_corregido = corregir_idioma(texto, tema)
    sospechosos = detectar_tokens_sospechosos(texto_corregido)

    if not sospechosos:
        return texto_corregido

    prompt = f"""
Corrige este texto para que quede completamente en español y elimina cualquier resto de palabras en inglés o mezclas raras.

Palabras o fragmentos problemáticos detectados: {', '.join(sospechosos)}

Reglas obligatorias:
- Devuelve solo el texto corregido.
- Todo debe quedar en español.
- Mantén el mismo sentido y tono.
- No añadas explicaciones.

Texto:
{texto_corregido}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=420,
    )

    segunda_version = limpiar_respuesta(response.choices[0].message.content or "")
    return segunda_version or texto_corregido


def humanizar_texto(texto: str, tema: dict[str, str]) -> str:
    """
    Pasa el texto por la guía humanizer antes de la revisión final.
    La meta no es adornar: es quitar huellas de plantilla y repetir menos motivos.
    """

    humanizer = GUIA.get("humanizer", {})
    evitar = humanizer.get("evitar", []) if isinstance(humanizer, dict) else []
    preferir = humanizer.get("preferir", []) if isinstance(humanizer, dict) else []
    bloqueados = _lista_guia("motivos_bloqueados")
    vigilados = _lista_guia("motivos_vigilados")

    prompt = f"""
Eres editor literario de {PROJECT_NAME}. Aplica una pasada de humanizer al texto.

Tema: {tema['nombre']} - {tema['descripcion']}

Reglas de humanizer:
{chr(10).join(f'- {item}' for item in HUMANIZER_REGLAS)}

Evita especialmente:
{chr(10).join(f'- {item}' for item in evitar)}

Prefiere:
{chr(10).join(f'- {item}' for item in preferir)}

Motivos bloqueados: {', '.join(bloqueados)}
Motivos vigilados, solo si son inevitables: {', '.join(vigilados)}

Instrucciones:
- Conserva el tema, la intención y una longitud breve.
- No uses la palabra "alma".
- No uses los motivos bloqueados.
- Si el texto depende de un motivo repetido, cámbialo por un objeto cotidiano menos usado.
- Mantén el texto en español natural.
- Devuelve solo la versión final, sin título ni explicación.

Texto:
{texto}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.25,
        max_tokens=420,
    )

    humanizado = limpiar_respuesta(response.choices[0].message.content or "")
    return humanizado or texto



def seleccionar_tema(temas_recientes: list[str] | None = None) -> dict[str, str]:
    temas_recientes = temas_recientes or []
    temas_disponibles = GUIA["temas"]
    temas_filtrados = [
        tema for tema in temas_disponibles if tema["nombre"] not in temas_recientes
    ]
    return random.choice(temas_filtrados if temas_filtrados else temas_disponibles)


# --- Agente 1: El Poeta ---
def agente_poeta(temas_recientes: list[str] | None = None) -> tuple[str, dict[str, str]]:
    print("🖋️ El Poeta comienza a escribir...")

    tema_elegido = seleccionar_tema(temas_recientes)
    print(f"   Tema elegido: {tema_elegido['nombre']}")

    system_prompt = f"""
Eres El Poeta, la voz editorial de {PROJECT_NAME}.

Tu trabajo es escribir un texto poético breve, íntimo y publicable. No escribes frases motivacionales genéricas: escribes escenas pequeñas que alguien podría sentir como propias.

## Requisito absoluto de idioma
- Escribe exclusivamente en español.
- No uses palabras en inglés.
- No mezcles idiomas.
- No inventes tokens raros ni camelCase dentro de una palabra.

## Guía de estilo
- Género: {GUIA['tono_estilo']['genero']}
- Atmósfera: {GUIA['tono_estilo']['atmosfera']}
- Longitud: {GUIA['tono_estilo']['longitud']}
- Recursos permitidos: {', '.join(GUIA['tono_estilo']['recursos_permitidos'])}
- Evitar: {', '.join(GUIA['tono_estilo']['prohibido'])}
- Restricción especial: {GUIA['restriccion_adicional']}

## Tema de hoy
Nombre: {tema_elegido['nombre']}
Descripción: {tema_elegido['descripcion']}

## Estructura sugerida
{chr(10).join(f'- {item}' for item in GUIA['estructura_poetica'])}

## Variedad editorial
- No uses estos motivos bloqueados: {', '.join(_lista_guia('motivos_bloqueados'))}.
- No empieces por costumbre con estos motivos vigilados: {', '.join(_lista_guia('motivos_vigilados'))}.
- Puedes partir de objetos menos usados como: {', '.join(_lista_guia('objetos_sugeridos'))}.
- Si eliges un objeto, que sea necesario para la escena y no un adorno.

## Pasada humanizer antes de responder
{chr(10).join(f'- {item}' for item in HUMANIZER_REGLAS)}

## Reglas de salida
- Devuelve solo el texto final.
- No incluyas título.
- No incluyas firma.
- No expliques el proceso.
- No uses hashtags dentro del texto.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Escribe un texto nuevo sobre: {tema_elegido['nombre']}. "
                    "Evita motivos repetidos y no uses la palabra taza."
                ),
            },
        ],
        temperature=0.9,
        max_tokens=360,
    )

    texto = limpiar_respuesta(response.choices[0].message.content or "")
    texto = asegurar_texto_en_espanol(texto, tema_elegido)
    texto = humanizar_texto(texto, tema_elegido)
    texto = asegurar_texto_en_espanol(texto, tema_elegido)

    print(f"✅ Texto generado: {texto[:70]}...")
    return texto, tema_elegido


# --- Agente 2: El Guardián de la Emoción ---
def agente_guardian(
    texto: str, tema: dict[str, str]
) -> tuple[str | list[str], bool, dict[str, Any]]:
    print("🛡️ El Guardián de la Emoción revisa...")

    sospechosos = detectar_tokens_sospechosos(texto)
    if sospechosos:
        violaciones = [
            "El texto contiene palabras o fragmentos que no parecen estar completamente en español: "
            + ", ".join(sospechosos)
        ]
        print(f"❌ Rechazado: {violaciones}")
        return violaciones, False, {
            "es_valido": False,
            "violaciones": violaciones,
            "puntuacion_emocional": 0,
            "comentario_editorial": "Se detectaron restos de inglés o mezcla de idiomas.",
        }

    motivos_bloqueados = detectar_motivos_bloqueados(texto)
    if motivos_bloqueados:
        violaciones = [
            "El texto usa motivos bloqueados por repetición editorial: "
            + ", ".join(motivos_bloqueados)
        ]
        print(f"❌ Rechazado: {violaciones}")
        return violaciones, False, {
            "es_valido": False,
            "violaciones": violaciones,
            "puntuacion_emocional": 0,
            "comentario_editorial": "Se detectó un motivo sobreusado.",
        }

    check_prompt = f"""
Actúa como editor literario. Evalúa si este texto puede publicarse en {PROJECT_NAME}.

Tema: {tema['nombre']} - {tema['descripcion']}

## Criterios
1. Evita clichés y frases hechas.
2. Usa imágenes sensoriales concretas.
3. Suena humano, vulnerable y natural.
4. Respeta la restricción: {GUIA['restriccion_adicional']}
5. No parece texto corporativo ni autoayuda genérica.
6. Mantiene una extensión razonable para una publicación poética breve.
7. Debe estar total y completamente en español. Si detectas una sola palabra en inglés, spanglish, camelCase o un token extraño, debes rechazarlo.
8. Debe pasar una lectura humanizer: sin importancia impostada, sin cierre de manual, sin tríos mecánicos, sin gerundios acumulados, sin frases como "recordatorio", "belleza en lo cotidiano", "en este espacio", "desde la sombra hacia la luz" o "no es solo".
9. No puede usar estos motivos bloqueados: {', '.join(_lista_guia('motivos_bloqueados'))}.
10. Debe evitar apoyarse por costumbre en estos motivos vigilados: {', '.join(_lista_guia('motivos_vigilados'))}.

## Texto
{texto}

Responde únicamente con JSON válido, sin markdown, con esta estructura exacta:
{{
  "es_valido": true,
  "violaciones": [],
  "puntuacion_emocional": 8,
  "comentario_editorial": "comentario breve"
}}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": check_prompt}],
        temperature=0.0,
        max_tokens=260,
    )

    raw = response.choices[0].message.content or "{}"

    try:
        resultado = extraer_json(raw)
    except Exception as exc:
        resultado = {
            "es_valido": False,
            "violaciones": [f"No se pudo interpretar la revisión editorial: {exc}"],
            "puntuacion_emocional": 0,
            "comentario_editorial": "Respuesta inválida del revisor.",
        }

    es_valido = bool(resultado.get("es_valido"))
    puntuacion = int(resultado.get("puntuacion_emocional", 0) or 0)

    if es_valido and puntuacion >= 8:
        print(f"✅ Aprobado ({puntuacion}/10)")
        return texto, True, resultado

    violaciones = resultado.get("violaciones") or ["No alcanzó la puntuación mínima."]
    print(f"❌ Rechazado: {violaciones}")
    return violaciones, False, resultado


# --- Agente 3: El Titulador ---
def agente_titulador(texto: str, tema: dict[str, str]) -> str:
    print("🏷️ El Titulador busca un nombre breve...")

    prompt = f"""
Eres editor de títulos para {PROJECT_NAME}. Crea un título breve para este escrito.

Tema editorial: {tema['nombre']}

Reglas:
- Debe tener entre 2 y 5 palabras.
- Debe sonar íntimo, sobrio y un poco misterioso.
- No repitas el nombre del tema.
- No uses la palabra "alma".
- No uses frases genéricas como "nuevo comienzo", "luz interior" o "camino de vida".
- No uses comillas, punto final ni explicación.
- Aplica humanizer: título concreto, natural, sin dramatismo impostado.

Texto:
{texto}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.35,
        max_tokens=40,
    )

    titulo = limpiar_respuesta(response.choices[0].message.content or "")
    titulo = re.sub(r"[\n\r]+", " ", titulo).strip(" .:;\"'")

    if not titulo or normalizar_token(titulo) == normalizar_token(tema["nombre"]):
        return "Lo que queda"

    return titulo[:70]


# --- Agente 4: El Visualizador ---
def agente_visualizador(texto: str, tema: dict[str, str]) -> tuple[str, str]:
    print("🎨 El Visualizador crea la dirección visual...")

    prompt = f"""
Create an English image prompt for a square editorial background that will sit behind a Spanish poetic text card.

Theme: {tema['nombre']}
Text for emotional context: {texto[:650]}

Visual style: emotional editorial photography, soft paper texture, subtle grain, warm minimalism, muted tones, cinematic natural light, clean negative space for overlaid text, no readable text, no letters, no logos, no detailed faces. Avoid cups, mugs and coffee unless the text explicitly needs them.

Return only the image prompt. Maximum 70 words.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.75,
        max_tokens=130,
    )

    prompt_imagen = limpiar_respuesta(response.choices[0].message.content or "")
    imagen_url = (
        "https://image.pollinations.ai/prompt/"
        f"{quote(prompt_imagen)}?width=1080&height=1080&nologo=true&enhance=true"
    )

    print(f"   Prompt visual: {prompt_imagen[:90]}...")
    return imagen_url, prompt_imagen
