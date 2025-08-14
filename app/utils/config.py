import os
import yaml
from typing import Any, Dict
from dotenv import load_dotenv

from app.utils.logger import AppLogger


class YamlConfigurationManager:
    """YAML-based configuration manager."""

    def load_schema(self, path: str) -> Dict[str, Any]:
        """Load validation schema from YAML file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Schema file not found: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in schema file {path}: {e}")

    def load_config(self, path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file {path}: {e}")


class LoadEnvironmentVariables:
    def __init__(self, conf_path):
        self.conf_path = conf_path
        self.API_BASE_URL = ""
        self.API_TIMEOUT = ""
        self.SYMBOL = ""
        self.CONF_FOLDER_PATH = ""
        self.PIP_VALUE = 0

        self._load_env_variables()

    def _load_env_variables(self):
        """Load environment variables from the .env file."""
        dotenv_path = self.conf_path
        if not os.path.exists(dotenv_path):
            raise FileNotFoundError(f"{dotenv_path} file not found.")

        load_dotenv(dotenv_path)
        self.API_BASE_URL = os.getenv('API_BASE_URL')
        self.API_TIMEOUT = int(os.getenv('API_TIMEOUT'))
        self.SYMBOL = os.getenv('SYMBOL')
        self.CONF_FOLDER_PATH = os.getenv('CONF_FOLDER_PATH')
        self.PIP_VALUE = int(os.getenv('PIP_VALUE'))

