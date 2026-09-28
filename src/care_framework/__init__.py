# -*- coding: utf-8 -*-
"""
CARE (Cognitive & Algorithmic Review Evaluator) Framework
=========================================================

This package implements the core algorithmic components of the CARE framework,
as described in the EMSE submission:
"Review Dynamics in the Era of Agentic SE: Balancing Speed and Depth through the CARE Framework"

The framework rigorously decouples `merge eligibility` (policy compliance) from 
`review task scheduling` (resource allocation under finite human cognitive budgets).
It is explicitly designed to process Agentic-PRs from the AIDev dataset (2023-2025).

Core Phases Implemented:
    - Phase 1: Commit-Bound State Machine (Temporal Invalidation)
    - Phase 2: Project-Defined Obligations Derivation
    - Phase 3: Traceable Evidence & Compliance Gates (Epistemic Independence)
    - Phase 4: Heuristic Task Scheduler (Marginal Expected Yield Optimization)
    - Phase 5: Bias-Aware Calibration (Inverse Probability Weighting - IPW)

Academic Standards & Reproducibility:
    - All pseudo-random operations (e.g., in IPW calibration and simulated scheduling) 
      are strictly bound to a global seed to guarantee bit-for-bit reproducibility.
    - Type hinting strictly follows PEP 484 to ensure robust static analysis.
"""

import logging
import random
import os
import warnings

# Optional but recommended scientific computing dependencies
try:
    import numpy as np
except ImportError:
    warnings.warn("numpy is not installed. Some stochastic operations in Phase 4/5 may fallback to standard library.")
    np = None

# ============================================================================
# Academic Metadata (Strictly adhering to Double-Blind Peer Review guidelines)
# ============================================================================
__version__ = "1.0.0"
__author__ = "Anonymous Authors (Masked for Double-Blind Review)"
__license__ = "MIT (Open Science Initiative)"
__paper_reference__ = "Under Review at Springer Empirical Software Engineering (EMSE)"
__dataset_dependency__ = "AIDev Dataset (https://arxiv.org/abs/2507.15003)"

# ============================================================================
# Global Reproducibility Configuration
# ============================================================================
def set_global_seed(seed: int = 42) -> None:
    """
    Enforces deterministic behavior across all CARE framework stochastic modules.
    
    In empirical software engineering, guaranteeing reproducibility across different
    computational environments is mandatory. This function locks the random states
    for standard Python, NumPy, and system-level hash seeds.
    
    Args:
        seed (int): The integer seed value for pseudo-random number generators.
    """
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    if np is not None:
        np.random.seed(seed)
    
    logger = logging.getLogger(__name__)
    logger.info(f"CARE Framework reproducibility locked with global seed: {seed}")

# ============================================================================
# Framework Module Exports (Public API mapping to Paper Sections)
# ============================================================================
# Note: These imports assume the respective files exist in the same directory.
# They are exposed here to provide a clean and strictly controlled public API.

from .phase1_state_machine import CommitStateMachine, EvaluationState
from .phase2_obligations import ObligationGenerator, RiskDomain, ObligationSet
from .phase3_evidence_gates import EvidenceLog, EvidenceTuple, ComplianceGate, EpistemicIndependenceChecker
from .phase4_heuristic_scheduler import HeuristicScheduler, MarginalExpectedYieldProxy
from .phase5_ipw_calibration import IPWCalibrator, StratifiedAuditor, TieredLabelSpace

# Restrict wildcard imports (`from care_framework import *`) to explicit definitions only.
# This prevents namespace pollution and clearly delineates the framework's architecture.
__all__ = [
    # Reproducibility
    "set_global_seed",
    
    # Phase 1: Sec 4.1 in Paper
    "CommitStateMachine",
    "EvaluationState",
    
    # Phase 2: Sec 4.2 in Paper
    "ObligationGenerator",
    "RiskDomain",
    "ObligationSet",
    
    # Phase 3: Sec 4.3 in Paper
    "EvidenceLog",
    "EvidenceTuple",
    "ComplianceGate",
    "EpistemicIndependenceChecker",
    
    # Phase 4: Sec 4.4 in Paper
    "HeuristicScheduler",
    "MarginalExpectedYieldProxy",
    
    # Phase 5: Sec 4.5 in Paper
    "IPWCalibrator",
    "StratifiedAuditor",
    "TieredLabelSpace"
]

# ============================================================================
# Framework-Level Logger Initialization
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] CARE_Framework: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
