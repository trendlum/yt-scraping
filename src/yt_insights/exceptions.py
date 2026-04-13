class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing."""


class YouTubeAPIError(RuntimeError):
    """Raised when the YouTube Data API returns an error or invalid payload."""


class SupabaseAPIError(RuntimeError):
    """Raised when the Supabase REST API returns an error or invalid payload."""
