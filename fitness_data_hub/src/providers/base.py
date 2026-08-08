from abc import ABC, abstractmethod
from typing import Any


class FitnessProvider(ABC):
    """Provider contract for activity acquisition.

    Analytics, persistence and Home Assistant-facing APIs must depend on this
    interface rather than on a provider-specific client.
    """

    name: str
    requires_oauth: bool = False
    requires_public_callback: bool = False

    @abstractmethod
    def list_activities(
        self,
        athlete_id: int,
        page: int = 1,
        per_page: int = 50,
        after: int | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError
