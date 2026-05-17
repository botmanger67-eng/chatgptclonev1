"""Configuration module for the AI Chat application.

Handles loading environment variables, providing sensible defaults,
and ensuring required keys are present for production use.
"""

import os
import logging
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

# Set up module-level logger
logger = logging.getLogger(__name__)

# Determine the project root directory (parent of this file's directory)
PROJECT_ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _load_env_file() -> None:
    """Load the .env file from the project root if python-dotenv is available.

    If python-dotenv is not installed, a warning is logged and the function
    assumes environment variables are set manually.
    """
    env_path = PROJECT_ROOT / ".env"
    if load_dotenv is not None:
        load_dotenv(dotenv_path=env_path, override=True)
        logger.info("Loaded environment variables from %s", env_path)
    else:
        if env_path.exists():
            logger.warning(
                "%s exists but python-dotenv is not installed. "
                "Set environment variables manually or install dotenv.",
                env_path
            )


def _get_env(key: str, default: Optional[str] = None) -> str:
    """Retrieve an environment variable with fallback.

    Args:
        key: Environment variable name.
        default: Optional fallback value if key is not set.

    Returns:
        The value of the environment variable or the default.

    Raises:
        ValueError: If the key is not set and no default is provided.
    """
    value = os.environ.get(key, default)
    if value is None:
        raise ValueError(
            f"Missing required environment variable: {key}. "
            "Please set it in your .env file or the system environment."
        )
    return value


# ---------------------------------------------------------------------------
# Configuration class
# ---------------------------------------------------------------------------

class Config:
    """Application configuration loaded from environment variables.

    Attributes:
        SECRET_KEY: Secret key for Flask sessions and CSRF protection.
        DATABASE_URI: URI for SQLite database.
        DEEPSEEK_API_KEY: API key for DeepSeek API.
        DEEPSEEK_BASE_URL: Base URL for DeepSeek API.
        DEEPSEEK_MODEL: Model name to use.
        DEEPSEEK_MAX_TOKENS: Maximum tokens for API responses.
        DEEPSEEK_TEMPERATURE: Temperature parameter for generation.
        MAX_CONVERSATIONS: Maximum number of conversations stored per user.
        LOG_LEVEL: Logging level for the application.
    """

    # Flask
    SECRET_KEY: str
    DATABASE_URI: str

    # DeepSeek API
    DEEPSEEK_API_KEY: Optional[str]
    DEEPSEEK_BASE_URL: str
    DEEPSEEK_MODEL: str
    DEEPSEEK_MAX_TOKENS: int
    DEEPSEEK_TEMPERATURE: float

    # Application
    MAX_CONVERSATIONS: int
    LOG_LEVEL: str

    @classmethod
    def from_env(cls) -> "Config":
        """Create a Config instance by reading environment variables.

        Loads the .env file if dotenv is available, then reads each required
        and optional setting. Sensible defaults are provided where possible.

        Returns:
            A fully populated Config instance.

        Raises:
            ValueError: If a required environment variable is missing.
        """
        _load_env_file()

        # --- REQUIRED ---
        try:
            secret_key = _get_env("SECRET_KEY")
        except ValueError:
            # Generate a random key if not set (for development)
            import secrets
            secret_key = secrets.token_hex(32)
            logger.warning(
                "SECRET_KEY not set. Generated a random one for development."
            )

        database_uri = _get_env(
            "DATABASE_URI",
            default=f"sqlite:///{PROJECT_ROOT / 'chat_history.db'}"
        )

        deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY", None)
        if not deepseek_api_key:
            deepseek_api_key = None  # Allow None; ai_handler will handle it

        # --- OPTIONAL (with defaults) ---
        deepseek_base_url = _get_env(
            "DEEPSEEK_BASE_URL",
            default="https://api.deepseek.com/v1"
        )
        deepseek_model = _get_env(
            "DEEPSEEK_MODEL",
            default="deepseek-chat"
        )

        max_tokens_str = _get_env("DEEPSEEK_MAX_TOKENS", default="2048")
        try:
            deepseek_max_tokens = int(max_tokens_str)
        except ValueError:
            logger.warning(
                "Invalid DEEPSEEK_MAX_TOKENS '%s', falling back to 2048.",
                max_tokens_str
            )
            deepseek_max_tokens = 2048

        temperature_str = _get_env("DEEPSEEK_TEMPERATURE", default="0.7")
        try:
            deepseek_temperature = float(temperature_str)
        except ValueError:
            logger.warning(
                "Invalid DEEPSEEK_TEMPERATURE '%s', falling back to 0.7.",
                temperature_str
            )
            deepseek_temperature = 0.7

        max_conv_str = _get_env("MAX_CONVERSATIONS", default="50")
        try:
            max_conversations = int(max_conv_str)
        except ValueError:
            logger.warning(
                "Invalid MAX_CONVERSATIONS '%s', falling back to 50.",
                max_conv_str
            )
            max_conversations = 50

        log_level = _get_env("LOG_LEVEL", default="INFO")

        # Build instance
        config = cls()
        config.SECRET_KEY = secret_key
        config.DATABASE_URI = database_uri
        config.DEEPSEEK_API_KEY = deepseek_api_key
        config.DEEPSEEK_BASE_URL = deepseek_base_url
        config.DEEPSEEK_MODEL = deepseek_model
        config.DEEPSEEK_MAX_TOKENS = deepseek_max_tokens
        config.DEEPSEEK_TEMPERATURE = deepseek_temperature
        config.MAX_CONVERSATIONS = max_conversations
        config.LOG_LEVEL = log_level

        return config


# ---------------------------------------------------------------------------
# Singleton pattern: load config once on import
# ---------------------------------------------------------------------------

try:
    config = Config.from_env()
except ValueError as e:
    logger.critical("Failed to load configuration: %s", e)
    # Re-raise to prevent app from starting with incomplete config
    raise

# Export for easy import in other modules
__all__ = ["config", "Config"]