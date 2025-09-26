from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from django.core.management import BaseCommand


@dataclass
class InstallationContext:
    """Almacena información compartida durante el proceso de instalación."""

    command: BaseCommand
    options: Dict[str, Any]
    local_app_labels: Iterable[str]

    @property
    def stdout(self):  # pragma: no cover - simple delegación
        return self.command.stdout

    @property
    def style(self):  # pragma: no cover - simple delegación
        return self.command.style

    def get_option(self, key: str, default: Optional[Any] = None) -> Any:
        return self.options.get(key, default)

    @property
    def force(self) -> bool:
        return bool(self.get_option("force", False))

    @property
    def no_seed(self) -> bool:
        return bool(self.get_option("no_seed", False))

    @property
    def no_serve(self) -> bool:
        return bool(self.get_option("no_serve", False))
