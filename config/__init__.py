"""
Configuration loader.

Reads config/default.yaml and provides a simple interface
for all modules to access settings.

Usage:
    from config import cfg

    index_dir = cfg.retrieval.index_dir
    model = cfg.llm.model
    port = cfg.server.port
"""

import os
import yaml


class ConfigSection:
    """Allows dot-access to config values: cfg.retrieval.index_dir"""

    def __init__(self, data: dict):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigSection(value))
            else:
                setattr(self, key, value)

    def __repr__(self):
        return str(self.__dict__)


class Config:
    """Loads and provides access to project configuration."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            # Find config relative to project root
            project_root = self._find_project_root()
            config_path = os.path.join(project_root, "config", "default.yaml")

        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n"
                f"Make sure config/default.yaml exists in your project root."
            )

        with open(config_path) as f:
            data = yaml.safe_load(f)

        # Create dot-accessible sections
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigSection(value))
            else:
                setattr(self, key, value)

        self._raw = data

    def _find_project_root(self):
        """Walk up from current dir to find the project root (has config/ folder)."""
        # Try current working directory first
        cwd = os.getcwd()
        if os.path.exists(os.path.join(cwd, "config", "default.yaml")):
            return cwd

        # Try relative to this file
        this_dir = os.path.dirname(os.path.abspath(__file__))
        parent = os.path.dirname(this_dir)
        if os.path.exists(os.path.join(parent, "config", "default.yaml")):
            return parent

        # Default to cwd
        return cwd

    def get(self, dotted_key: str, default=None):
        """Get a value by dotted key: cfg.get('retrieval.index_dir')"""
        keys = dotted_key.split(".")
        obj = self
        for key in keys:
            if hasattr(obj, key):
                obj = getattr(obj, key)
            else:
                return default
        return obj

    def __repr__(self):
        return f"Config({self._raw})"


# Global config instance — import this everywhere
cfg = Config()