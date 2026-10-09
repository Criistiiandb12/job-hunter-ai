import os
import json

from dotenv import load_dotenv
from groq import Groq

from config.profile import PROFILE


load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "No se encontró GROQ_API_KEY en el archivo .env"
    )


client = Groq(api_key=GROQ_API_KEY)


MODEL = "openai/gpt-oss-20b"


def construir_prompt(job):

    return f"""
Eres un asistente especializado en analizar ofertas de empleo.

Debes comparar el perfil profesional del candidato con la oferta
de trabajo y determinar qué tan compatible es.

PERFIL DEL CANDIDATO:

{json.dumps(PROFILE, ensure_ascii=False, indent=2)}

OFERTA DE TRABAJO:

Cargo:
{job.title}

Empresa:
{job.company}

Ubicación:
{job.location}

Trabajo remoto:
{job.remote}

Salario mínimo:
{job.salary_min}

Salario máximo:
{job.salary_max}

Descripción:

{job.description}

Fuente:
{job.source}

INSTRUCCIONES:

1. Determina un porcentaje de compatibilidad entre 0 y 100.
2. Resume brevemente la oferta.
3. Indica las principales habilidades del candidato que coinciden.
4. Indica los requisitos importantes de la oferta que faltan
   o que no aparecen en el perfil.
5. Explica brevemente por qué el candidato encaja o no.

IMPORTANTE:

- No inventes experiencia que no aparezca en el perfil.
- No supongas que una habilidad existe si no está indicada.
- El porcentaje debe representar la compatibilidad real.
- Considera especialmente cargo, habilidades, experiencia,
  modalidad, ubicación y requisitos técnicos.
"""


async def analizar_oferta(job):

    prompt = construir_prompt(job)

    try:

        response = client.chat.completions.create(

            model=MODEL,

            messages=[
                {
                    "role": "system",
                    "content": (
                        "Analiza ofertas laborales "
                        "de forma objetiva y devuelve "
                        "únicamente los datos solicitados."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0,

            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "job_analysis",
                    "strict": True,
                    "schema": {
                        "type": "object",

                        "properties": {

                            "match": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            },

                            "summary": {
                                "type": "string"
                            },

                            "strengths": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            },

                            "missing": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            },

                            "reason": {
                                "type": "string"
                            }
                        },

                        "required": [
                            "match",
                            "summary",
                            "strengths",
                            "missing",
                            "reason"
                        ],

                        "additionalProperties": False
                    }
                }
            }
        )

        contenido = response.choices[0].message.content

        if not contenido:
            print("❌ Groq devolvió una respuesta vacía.")
            return None

        resultado = json.loads(contenido)

        # Validación adicional por seguridad
        if not isinstance(resultado.get("match"), int):
            print("❌ Match inválido.")
            return None

        if not 0 <= resultado["match"] <= 100:
            print("❌ Match fuera del rango 0-100.")
            return None

        if not isinstance(resultado.get("summary"), str):
            print("❌ Summary inválido.")
            return None

        if not isinstance(resultado.get("strengths"), list):
            print("❌ Strengths inválido.")
            return None

        if not isinstance(resultado.get("missing"), list):
            print("❌ Missing inválido.")
            return None

        if not isinstance(resultado.get("reason"), str):
            print("❌ Reason inválido.")
            return None

        print("✅ Respuesta de Groq validada correctamente.")

        return resultado

    except Exception as e:

        print(
            f"❌ Error consultando Groq: {e}"
        )

        return None