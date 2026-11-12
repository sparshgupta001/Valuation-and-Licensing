"""Security extension points; authentication is intentionally not implemented yet."""


def require_authenticated_user() -> None:
    """Placeholder dependency to replace with the application's auth provider."""

    raise NotImplementedError("Configure an authentication provider before exposing this service.")
