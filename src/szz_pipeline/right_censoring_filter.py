# -*- coding: utf-8 -*-
"""
Right-Censoring Filter for Defect Observation Cohorts
=====================================================

This module implements the right-censoring safeguards described in Section 5.2 
of the EMSE submission:
"Review Dynamics in the Era of Agentic SE: Balancing Speed and Depth through the CARE Framework"

Academic Design Philosophy & Limitations:
-----------------------------------------
In empirical software engineering, assigning a binary "Defect-Free" (False) label to a 
recently merged Pull Request introduces severe False Negative Bias. A defect may exist 
but has not yet been discovered or reported. This phenomenon is known as Right-Censoring.

This module enforces a strict maturation window (T_mature). 
- If a PR has an observed defect (δ_p = 1), it is kept regardless of its age.
- If a PR has NO observed defect (δ_p = 0), it is only retained for binary calibration 
  if its observation time (T_p) strictly exceeds T_mature. 
- Immature, defect-free PRs are filtered out of the static evaluation cohort to prevent 
  the model from learning that "new AI code is always bug-free."

CRITICAL REPRODUCIBILITY SAFEGUARD:
This module strictly forbids the use of dynamic time (e.g., `datetime.now()`). 
Calculating observation time must be anchored to a static `study_cutoff_date` 
(e.g., Dec 31, 2025) to guarantee bit-for-bit reproducibility of the evaluation cohort 
during peer review.

Standards Complied:
- Survival Analysis Principles for observational cohort selection.
- PEP 484 Type Hinting.
"""

import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Tuple

# Import the formalized label space
from src.care_framework.phase5_ipw_calibration import TieredLabelSpace, LabelStrength

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class CensoringConfig:
    """
    Configuration parameters for the right-censoring filter.
    Immutable to prevent runtime alteration of evaluation boundaries.
    """
    study_cutoff_date: datetime
    maturation_window_days: float = 180.0  # Standard practice: 6 months observation

    def __post_init__(self):
        # Academic Safeguard: Ensure timezone awareness to prevent cross-region evaluation drifts
        if self.study_cutoff_date.tzinfo is None:
            raise ValueError(
                "Academic Malpractice Prevention: study_cutoff_date MUST be timezone-aware. "
                "Implicit local times ruin bit-for-bit reproducibility across different machines."
            )
        if self.maturation_window_days <= 0:
            raise ValueError("Maturation window must be strictly positive.")


class RightCensoringFilter:
    """
    Enforces maturity thresholds on observational defect cohorts.
    """
    
    def __init__(self, config: CensoringConfig):
        self.config = config
        logger.debug(
            f"RightCensoringFilter initialized. "
            f"Cutoff: {self.config.study_cutoff_date.isoformat()}, "
            f"Maturation Threshold: {self.config.maturation_window_days} days."
        )

    def _calculate_observation_days(self, merge_timestamp: datetime) -> float:
        """
        Calculates T_p strictly against the static study cutoff date.
        """
        if merge_timestamp.tzinfo is None:
             raise ValueError("Merge timestamps must be timezone-aware.")
             
        if merge_timestamp > self.config.study_cutoff_date:
            raise ValueError(
                f"Data Leakage Detected: Found commit merged at {merge_timestamp.isoformat()}, "
                f"which is AFTER the study cutoff {self.config.study_cutoff_date.isoformat()}."
            )
            
        delta = self.config.study_cutoff_date - merge_timestamp
        return delta.total_seconds() / 86400.0  # Convert seconds to days

    def filter_immature_negatives(
        self, 
        raw_labels: List[TieredLabelSpace], 
        merge_timestamps: dict[str, datetime]
    ) -> Tuple[List[TieredLabelSpace], dict]:
        """
        Filters out right-censored negative samples that have not met the maturation threshold.
        
        Args:
            raw_labels: The list of raw SZZ labels (both WeakSZZ and NA).
            merge_timestamps: A mapping of PR ID to its timezone-aware merge datetime.
            
        Returns:
            Tuple containing:
                - List[TieredLabelSpace]: The filtered, mature evaluation cohort.
                - dict: Audit statistics detailing the filtering process.
        """
        logger.info("Applying Right-Censoring filter to evaluation cohort...")
        
        mature_cohort: List[TieredLabelSpace] = []
        
        stats = {
            "initial_count": len(raw_labels),
            "kept_positives_early": 0,
            "kept_positives_mature": 0,
            "kept_negatives_mature": 0,
            "dropped_negatives_immature": 0,
            "dropped_missing_timestamp": 0
        }

        for label in raw_labels:
            pr_id = label.pr_id
            if pr_id not in merge_timestamps:
                logger.warning(f"Missing merge timestamp for PR {pr_id}. Dropping to preserve integrity.")
                stats["dropped_missing_timestamp"] += 1
                continue

            # Recalculate observation time based on static cutoff to guarantee reproducibility
            obs_days = self._calculate_observation_days(merge_timestamps[pr_id])
            
            is_mature = obs_days >= self.config.maturation_window_days

            if label.defect_observed:
                # Positives (Defects found) are ALWAYS kept. 
                # A bug found in 2 days is still a valid bug.
                mature_cohort.append(label)
                if is_mature:
                    stats["kept_positives_mature"] += 1
                else:
                    stats["kept_positives_early"] += 1
            else:
                # Negatives (No defect found) are ONLY kept if they have matured.
                if is_mature:
                    mature_cohort.append(label)
                    stats["kept_negatives_mature"] += 1
                else:
                    # The core action of this module: Dropping immature negatives
                    stats["dropped_negatives_immature"] += 1

        # Log formal audit results
        logger.info(
            f"Censoring Filter Audit: Dropped {stats['dropped_negatives_immature']} immature negative PRs. "
            f"Cohort size reduced from {stats['initial_count']} to {len(mature_cohort)}. "
            f"False Negative Bias successfully structurally mitigated."
        )

        return mature_cohort, stats

if __name__ == "__main__":
    # Academic warning against executing library files directly
    logger.warning(
        "Right-censoring filter should be instantiated within the formal evaluation pipeline "
        "(e.g., RQ1 Historical Replay) rather than executed standalone."
    )
