"""
Tool 2: ProviderManager
Lee información de proveedores/partners (organizaciones).
"""
import json
import os
from langchain_core.tools import Tool

from src.config import settings

DATA_DIR = settings.data_dir
PROVIDERS_DIR = os.path.join(DATA_DIR, "proveedores")


def provider_manager(query: str) -> str:
    """
    Consulta información de proveedores/partners.
    Input: 'list_all' para listar todos, o un provider_id para ver detalle.
    """
    if query.strip() == "list_all":
        providers = []
        for filename in sorted(os.listdir(PROVIDERS_DIR)):
            if filename.endswith(".json"):
                filepath = os.path.join(PROVIDERS_DIR, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    p = json.load(f)
                dep = p.get("dependencia", "N/A")
                providers.append(f"{p['id']}: {p['nombre']} (dependencia: {dep})")
        return "\n".join(providers) if providers else "No hay proveedores registrados"

    # Buscar por ID
    provider_id = query.strip()
    filepath = os.path.join(PROVIDERS_DIR, f"{provider_id}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.dumps(json.load(f), ensure_ascii=False, indent=2)

    # Buscar en todos los archivos por ID interno
    for filename in os.listdir(PROVIDERS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(PROVIDERS_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                p = json.load(f)
            if p.get("id") == provider_id:
                return json.dumps(p, ensure_ascii=False, indent=2)

    return f"Proveedor '{provider_id}' no encontrado"


provider_manager_tool = Tool(
    name="ProviderManager",
    description="""Lee información de proveedores/partners (organizaciones) de NV Mexico.
    Input: 'list_all' para listar todos los proveedores, o un provider_id para ver detalle completo
    incluyendo tipo, dependencia y riesgos conocidos.""",
    func=provider_manager,
)
