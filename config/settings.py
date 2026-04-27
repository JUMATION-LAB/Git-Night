"""
Configuration settings for the AI Forex Trading Bot.
Loads environment variables and provides typed configuration.
"""
import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Supabase Configuration
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(..., env="SUPABASE_KEY")
    
    # MetaTrader 5 Configuration
    MT5_LOGIN: int = Field(default=0, env="MT5_LOGIN")
    MT5_PASSWORD: str = Field(default="", env="MT5_PASSWORD")
    MT5_SERVER: str = Field(default="", env="MT5_SERVER")
    MT5_PATH: Optional[str] = Field(default=None, env="MT5_PATH")
    
    # Trading Configuration
    MAX_RISK_PERCENT: float = Field(default=2.0, env="MAX_RISK_PERCENT")
    MAX_TRADES_PER_DAY: int = Field(default=3, env="MAX_TRADES_PER_DAY")
    DEFAULT_LOT_SIZE: float = Field(default=0.01, env="DEFAULT_LOT_SIZE")
    DEFAULT_STOP_LOSS_PIPS: int = Field(default=50, env="DEFAULT_STOP_LOSS_PIPS")
    DEFAULT_TAKE_PROFIT_PIPS: int = Field(default=100, env="DEFAULT_TAKE_PROFIT_PIPS")
    
    # Application Settings
    APP_NAME: str = Field(default="AI Forex Trading Bot", env="APP_NAME")
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Settings
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    
    # WebSocket Settings
    WS_ENABLED: bool = Field(default=True, env="WS_ENABLED")
    
    # Mock mode for testing (no real trades)
    MOCK_TRADING: bool = Field(default=True, env="MOCK_TRADING")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
