"""
Gestor de memoria persistente por proveedor/contacto.
Usa FileChatMessageHistory para persistir conversaciones en JSON.
"""
import os
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain.memory import ConversationBufferMemory

from src.config import settings

DATA_DIR = settings.data_dir
MEMORIES_DIR = os.path.join(DATA_DIR, "memories")


class ProviderMemoryManager:
    """Una memoria persistente en JSON por cada contacto/proveedor."""

    def __init__(self, memory_dir: str = MEMORIES_DIR):
        self.memory_dir = memory_dir
        os.makedirs(memory_dir, exist_ok=True)
        self._memories: dict[str, ConversationBufferMemory] = {}

    def get_memory(self, contact_id: str) -> ConversationBufferMemory:
        if contact_id not in self._memories:
            history = FileChatMessageHistory(
                file_path=os.path.join(self.memory_dir, f"{contact_id}.json")
            )
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                chat_memory=history,
            )
            self._memories[contact_id] = memory
        return self._memories[contact_id]

    def list_active_memories(self) -> list[str]:
        """Lista contactos con historial de conversación."""
        files = [
            f.replace(".json", "")
            for f in os.listdir(self.memory_dir)
            if f.endswith(".json") and os.path.getsize(os.path.join(self.memory_dir, f)) > 2
        ]
        return sorted(files)
