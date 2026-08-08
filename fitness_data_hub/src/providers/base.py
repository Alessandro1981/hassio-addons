from abc import ABC, abstractmethod
from typing import Any


class FitnessProvider(ABC):
    """Provider contract for acquisition and authentication.

    Persistence, analytics and Home Assistant-facing code should depend on this
    interface instead of importing a provider-specific client directly.
    """

    name: str
    requires_oauth: bool = False
    requires_public_callback: bool = False

    def build_authorize_url(self) -> str:
        raise NotImplementedError(f"Provider {self.name} does not support OAuth authorization")

    def complete_authorization(self, code: str, scope: str | None = None) -> Any:
        raise NotImplementedError(f"Provider {self.name} does not support OAuth authorization")

    @abstractmethod
    def list_activities(
        self,
        athlete_id: int,
        page: int = 1,
        per_page: int = 50,
        after: int | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError
