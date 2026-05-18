from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent
DOCS_DIR = ROOT_DIR / "docs"
POSTS_DIR = DOCS_DIR / "_posts"
SOCIAL_ASSETS_DIR = DOCS_DIR / "assets" / "social"
BACKGROUND_ASSETS_DIR = DOCS_DIR / "assets" / "backgrounds"
BIBLIA_PATH = ROOT_DIR / "biblia" / "guia_estilo.json"
MEMORIA_DIR = ROOT_DIR / "memoria"
MEMORIA_PUBLICACION_PATH = MEMORIA_DIR / "estado_publicacion.json"
MEMORIA_TEMAS_PATH = MEMORIA_DIR / "temas_usados.json"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
PROJECT_TIMEZONE = os.getenv("PROJECT_TIMEZONE", "America/Bogota")
MAX_INTENTOS = int(os.getenv("MAX_INTENTOS", "5"))
TEMAS_RECIENTES_A_EVITAR = int(os.getenv("TEMAS_RECIENTES_A_EVITAR", "6"))

PROJECT_NAME = "Ecos del Alma"
