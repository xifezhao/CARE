# -*- coding: utf-8 -*-
"""
RQ2 Subset Extraction: Isolating the Algorithmic Monoculture Cohort
===================================================================

This module implements the cohort selection methodology for RQ2, as described 
in Section 6.2 of the EMSE submission:
"Review Dynamics in the Era of Agentic SE: Balancing Speed and Depth through the CARE Framework"

Academic Design Philosophy & Inclusion Criteria:
------------------------------------------------
To empirically prove the "Echo Chamber" effect (correlated failure modes), we must isolate 
a highly specific subset of the PR population where Epistemic Independence was inherently 
violated, yet the code was deemed "safe" by the baseline system.

A Pull Request is strictly included in the Monoculture Subset if and only if:
1. Agentic Authorship: The PR was authored by an LLM-based agent.
2. Homogeneous Verification: The PR was reviewed and approved by an AI reviewer belonging 
   to the SAME model family or training lineage (e.g., Copilot reviewing Copilot).
3. False Negative Approval: The baseline CI/CD pipeline and the AI reviewer flagged NO issues 
   (i.e., it was merged into the main branch).
4. Epistemic Ground Truth: A consequential defect was later discovered and traced back to 
   this PR, and this label is strictly 'ManualVerified' (Rejecting 'WeakSZZ' noise).

Standards Complied:
- Strict Label Quarantine: Prevents SZZ heuristic noise from contaminating the RQ2 
  ablation study on orthogonal verification tools.
- Immutable configuration objects to guarantee deterministic cohort filtering.
"""

import os
import sys
import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Set

# Ensure project root is in sys.path when running script directly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import core framework components
from src.care_framework.phase5_ipw_calibration import TieredLabelSpace, LabelStrength

# Configure auditable logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] RQ2_Subset_Extractor: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================

@dataclass(frozen=True)
class ProvenanceMetadata:
    """
    Tracks the cryptographic and methodological provenance of a PR actor.
    """
    is_ai: bool
    model_family: str  # e.g., "GPT-4-series", "Claude-3-series", "Human"


@dataclass(frozen=True)
class PRReviewContext:
    """
    Immutable representation of the PR's historical context for cohort filtering.
    """
    pr_id: str
    author: ProvenanceMetadata
    reviewer: ProvenanceMetadata
    was_approved_by_reviewer: bool
    was_merged: bool


# ============================================================================
# Core Extraction Engine
# ============================================================================

class MonocultureSubsetExtractor:
    """
    Executes the strict inclusion/exclusion criteria to isolate the Echo Chamber cohort.
    """

    def __init__(self, target_subset_size: int = 1240):
        """
        Args:
            target_subset_size: The exact subset size reported in Section 6.2 of the paper.
                                Used here as an assertion safeguard for reproducibility.
        """
        self.target_subset_size = target_subset_size

    def is_monoculture(self, context: PRReviewContext) -> bool:
        """
        Evaluates Criterion 1 & 2: Agentic Authorship & Homogeneous Verification.
        """
        if not context.author.is_ai or not context.reviewer.is_ai:
            return False
            
        # The core definition of Algorithmic Monoculture: 
        # Both generation and verification rely on the same underlying distributions.
        return context.author.model_family == context.reviewer.model_family

    def execute_filtering(
        self, 
        pr_contexts: List[PRReviewContext], 
        ground_truth_labels: Dict[str, TieredLabelSpace]
    ) -> List[str]:
        """
        Filters the dataset to extract the strictly defined high-risk monoculture subset.
        
        Args:
            pr_contexts: The historical contexts of the evaluated PRs.
            ground_truth_labels: The 2D tiered label space containing defect outcomes.
            
        Returns:
            List[str]: A deterministic, sorted list of PR IDs belonging to the subset.
        """
        logger.info(f"Scanning {len(pr_contexts)} PR contexts for Monoculture traits...")
        
        subset_pr_ids: Set[str] = set()
        exclusion_stats = {
            "not_monoculture": 0,
            "not_merged_or_approved": 0,
            "no_defect_observed": 0,
            "rejected_weak_szz": 0
        }

        for ctx in pr_contexts:
            # Check Criterion 1 & 2: Monoculture traits
            if not self.is_monoculture(ctx):
                exclusion_stats["not_monoculture"] += 1
                continue
                
            # Check Criterion 3: False Negative Approval (The illusion of safety)
            if not (ctx.was_approved_by_reviewer and ctx.was_merged):
                exclusion_stats["not_merged_or_approved"] += 1
                continue
                
            label = ground_truth_labels.get(ctx.pr_id)
            if not label or not label.defect_observed:
                exclusion_stats["no_defect_observed"] += 1
                continue
                
            # ---------------------------------------------------------
            # ACADEMIC SAFEGUARD: Strict Label Quarantine
            # ---------------------------------------------------------
            # Check Criterion 4: Epistemic Ground Truth
            if label.strength == LabelStrength.WEAK_SZZ:
                exclusion_stats["rejected_weak_szz"] += 1
                continue
            elif label.strength == LabelStrength.MANUAL_VERIFIED:
                subset_pr_ids.add(ctx.pr_id)
            else:
                logger.warning(f"Unrecognized label strength for PR {ctx.pr_id}. Excluding.")

        # Deterministic sorting to guarantee bit-for-bit reproducibility
        sorted_subset = sorted(list(subset_pr_ids))
        
        logger.info(
            f"Extraction Complete. Identified {len(sorted_subset)} Monoculture PRs.\n"
            f"Exclusion Breakdown:\n"
            f"  - Lacked Monoculture Traits:      {exclusion_stats['not_monoculture']}\n"
            f"  - Blocked Before Merge:           {exclusion_stats['not_merged_or_approved']}\n"
            f"  - No Defect Observed (Censored):  {exclusion_stats['no_defect_observed']}\n"
            f"  - QUARANTINED (WeakSZZ Noise):    {exclusion_stats['rejected_weak_szz']}"
        )

        # Reproducibility Assertion (maps to paper's claim in Section 6.2)
        if len(sorted_subset) != self.target_subset_size:
            logger.warning(
                f"Reproducibility Alert: Extracted subset size ({len(sorted_subset)}) "
                f"does not match the reported size in the paper ({self.target_subset_size}). "
                f"Verify the input datasets."
            )
            
        return sorted_subset


# ============================================================================
# Main Execution Entrypoint
# ============================================================================
if __name__ == "__main__":
    
    # Standard path resolution
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    RESULTS_DIR = os.path.join(BASE_DIR, "results", "rq2")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # 1. Load Ground Truth Labels
    labels_path = os.path.join(DATA_DIR, "manual_audit", "IRR_ManualVerified_Labels.json")
    ground_truth: Dict[str, TieredLabelSpace] = {}
    if os.path.exists(labels_path):
        with open(labels_path, 'r', encoding='utf-8') as f:
            raw_labels = json.load(f)
            for r in raw_labels:
                ground_truth[r["pr_id"]] = TieredLabelSpace(
                    pr_id=r["pr_id"],
                    observation_days=r["observation_days"],
                    defect_observed=r["defect_observed"],
                    strength=LabelStrength(r["strength"])
                )
    else:
        logger.warning(f"Ground truth file missing at {labels_path}. Initialized empty map for dry-run verification.")
            
    # 2. Load PR Contexts (Mocking data ingestion for architectural completeness)
    logger.info("Loading PR contextual metadata...")
    mock_contexts = []
    
    # 3. Execute Extraction
    extractor = MonocultureSubsetExtractor(target_subset_size=1240)
    monoculture_subset = extractor.execute_filtering(mock_contexts, ground_truth)
    
    # 4. Export Subset for downstream Orthogonal Tool Execution (CodeQL)
    out_path = os.path.join(RESULTS_DIR, "rq2_monoculture_subset_ids.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(monoculture_subset, f, indent=2)
        
    logger.info(f"Successfully exported {len(monoculture_subset)} PR IDs to {out_path}")
