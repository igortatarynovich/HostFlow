"""Entity Profile Definition Registry exceptions."""


class EntityProfileNotFoundError(LookupError):
    """Raised when an explicit entity_profile_code does not resolve in the registry."""

    def __init__(self, profile_code: str) -> None:
        self.profile_code = str(profile_code or "").strip()
        super().__init__(f"Entity profile not found: {self.profile_code}")
