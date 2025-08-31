from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    Centralized application settings using Pydantic.
    It automatically loads variables from a .env file and the environment.
    """
    # model_config tells Pydantic to load from a .env file and ignore extra vars
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Google Cloud
    # Note: In a real GCP environment, GOOGLE_APPLICATION_CREDENTIALS is often
    # set in the environment itself, not the .env file.
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    GCS_BUCKET_NAME: Optional[str] = None

    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None

    # Zilliz Cloud
    ZILLIZ_CLOUD_URI: Optional[str] = None
    ZILLIZ_CLOUD_TOKEN: Optional[str] = None

    # Generative AI (Gemini)
    GEMINI_API_KEY: Optional[str] = None

    # Video Editing (Creatomate)
    CREATOMATE_API_KEY: Optional[str] = None
    CREATOMATE_TEMPLATE_ID: Optional[str] = None

# Create a single, reusable instance of the settings for the application
settings = Settings()
