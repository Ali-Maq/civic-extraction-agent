"""
Configuration Module
====================

All settings, paths, and constants.
"""

from .settings import (
    # Paths
    BASE_DIR,
    PAPERS_DIR,
    GROUND_TRUTH_PATH,
    OUTPUTS_DIR,
    LOGS_DIR,
    
    # Extraction settings
    MAX_ITERATIONS,
    MAX_TURNS,
    
    # Model settings
    DEFAULT_MODEL,
    PLANNER_MODEL,
    CRITIC_MODEL,
    
    # API settings
    MYGENE_API_URL,
    MYVARIANT_API_URL,
)

__all__ = [
    "BASE_DIR",
    "PAPERS_DIR",
    "GROUND_TRUTH_PATH",
    "OUTPUTS_DIR",
    "LOGS_DIR",
    "MAX_ITERATIONS",
    "MAX_TURNS",
    "DEFAULT_MODEL",
    "PLANNER_MODEL",
    "CRITIC_MODEL",
    "MYGENE_API_URL",
    "MYVARIANT_API_URL",
]


