"""
Configuration Settings
======================

All paths, API keys, and constants in one place.
Load from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# PATHS
# =============================================================================

# Base directory is the project root (parent of config/)
BASE_DIR = Path(__file__).parent.parent

# Data paths (from environment or defaults)
PAPERS_DIR = Path(os.getenv("PAPERS_DIR", BASE_DIR / "data" / "papers"))
GROUND_TRUTH_PATH = Path(os.getenv(
    "GROUND_TRUTH_PATH", 
    BASE_DIR / "data" / "ground_truth" / "all_combined_extracted_data_refined.xlsx"
))
OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", BASE_DIR / "outputs"))
LOGS_DIR = Path(os.getenv("LOGS_DIR", BASE_DIR / "logs"))

# Ensure output directories exist
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# EXTRACTION SETTINGS
# =============================================================================

# Maximum number of Extractor-Critic iterations before forcing completion
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))

# Maximum conversation turns for the agent
MAX_TURNS = int(os.getenv("MAX_TURNS", "50"))

# =============================================================================
# MODEL SETTINGS
# =============================================================================

# Default model for main extraction (most capable)
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "opus")

# Model for planning (fast, good at analysis)
PLANNER_MODEL = os.getenv("PLANNER_MODEL", "sonnet")

# Model for validation/critique (fast, good at rules)
CRITIC_MODEL = os.getenv("CRITIC_MODEL", "sonnet")

# =============================================================================
# API SETTINGS (for normalization lookups)
# =============================================================================

# MyGene.info API
MYGENE_API_URL = "https://mygene.info/v3"

# MyVariant.info API  
MYVARIANT_API_URL = "https://myvariant.info/v1"

# Ontology Lookup Service (OLS)
OLS_API_URL = "https://www.ebi.ac.uk/ols/api"

# API timeout in seconds
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "15"))