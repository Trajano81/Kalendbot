"""
Base channel adapter — defines the interface that Telegram and WhatsApp adapters implement.
Provides execute_command() to run shared handlers and dispatch results via channel-specific I/O.
"""
import logging
from abc import ABC, abstractmethod

from src.handlers.registry import CommandDef, CommandContext, CommandResult

logger = logging.getLogger("kalendbot.channels.base")


class ChannelAdapter(ABC):
    """Abstract base class for channel adapters (Telegram, WhatsApp, etc.)."""

    @abstractmethod
    async def send_text(self, recipient: str, text: str) -> bool:
        """Send a text message to a recipient."""
        ...

    @abstractmethod
    async def send_file(self, recipient: str, path: str, caption: str = "") -> bool:
        """Send a file to a recipient."""
        ...

    @abstractmethod
    async def send_image(self, recipient: str, path: str, caption: str = "") -> bool:
        """Send an image to a recipient."""
        ...

    @abstractmethod
    def format_text(self, text: str) -> str:
        """Apply channel-specific text formatting (e.g. markdown conversion)."""
        ...

    async def execute_command(self, cmd_def: CommandDef, ctx: CommandContext, recipient: str) -> None:
        """
        Run a shared handler and dispatch the result via channel-specific send methods.
        This is the main integration point between shared handlers and channel adapters.
        """
        result = await cmd_def.handler(ctx)

        if result.error:
            await self.send_text(recipient, result.error)
        elif result.file_path:
            await self.send_file(recipient, result.file_path, result.text or "")
        elif result.image_path:
            await self.send_image(recipient, result.image_path, result.text or "")
        elif result.text:
            text = self.format_text(result.text)
            await self.send_text(recipient, text)
