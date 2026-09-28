# -*- coding: utf-8 -*-
"""
Phase 3: Traceable Evidence and Compliance Gates
================================================

This module implements the formalization described in Section 4.3 of the EMSE submission:
"Review Dynamics in the Era of Agentic SE: Balancing Speed and Depth through the CARE Framework"

Academic Design Philosophy:
---------------------------
Traditional CI pipelines treat verifications as opaque scalar metrics or binary Pass/Fail flags,
which leads to the "Overlap Fallacy" (redundant checks inflating coverage) and algorithmic 
monocultures (homogenous AI models validating each other's blind spots).

This phase enforces Merge Eligibility via three strict mathematical conditions (Equation 3):
1. Gate 1 (Coverage): ⋃ e.scope ⊇ Ω_d (Set union of passing scopes must cover all obligations).
2. Gate 2 (Validation): ∄ e.result = Fail (No unresolved explicit failures).
3. Gate 3 (Diversity): EpistemicIndependenceSatisfied(E) (Methodological diversity enforced).

Standards Complied:
- Pure set-theoretic operations for evaluating Gate 1 to structurally eliminate the overlap fallacy.
- Strict decoupling of cryptographic provenance (who triggered it) from methodological 
  independence (how it was evaluated).
- Immutable data structures to preserve auditability for Phase 5 (IPW Calibration).
"""

import logging
from enum import Enum, unique
from dataclasses import dataclass, field
from typing import FrozenSet, Iterable, Tuple, List

from .phase2_obligations import RiskDomain, ReviewObligation

# Module-level logger for auditable simulation trails
logger = logging.getLogger(__name__)

@unique
class EvidenceResult(Enum):
    """Discrete outcome states for an evidence record."""
    PASS = "Pass"
    FAIL = "Fail"
    UNKNOWN = "Unknown"
    NA = "NA"


@unique
class MethodologyClass(Enum):
    """
    Categorization of verification methodologies. 
    Crucial for differentiating methodological independence from mere provenance.
    """
    LLM_GENERATED = "LLM_Generated"             # E.g., LLM-based summary or review agent
    DETERMINISTIC_STATIC = "Deterministic_Static" # E.g., CodeQL, AST parsing
    SYMBOLIC_EXECUTION = "Symbolic_Execution"     # E.g., Formal methods, fuzzing
    HUMAN_EXPERT = "Human_Expert"                 # E.g., Manual code review


@dataclass(frozen=True)
class EvidenceTuple:
    """
    Formal representation of traceable evidence:
    e = <h, d, source, method, scope, result, timestamp, inputs>
    
    Immutability ensures that once evidence is logged, it cannot be tampered with,
    preserving the integrity of the compliance gates.
    """
    commit_hash: str
    domain: RiskDomain
    source_identity: str           # Cryptographic provenance (e.g., 'GitHub_Action_Bot_X')
    methodology: MethodologyClass  # Epistemic nature of the check
    scope: FrozenSet[ReviewObligation] # The subset of Ω_d this evidence claims to cover
    result: EvidenceResult
    timestamp: float
    inputs_hash: str               # Hash of dependencies (e.g., prompt template, ruleset version)
    is_resolved: bool = False      # If True, a FAIL result has been explicitly overridden/resolved

    def __post_init__(self):
        if not self.commit_hash:
            raise ValueError("Evidence must be strictly bound to a commit hash (Phase 1 axiom).")


class EpistemicIndependenceChecker:
    """
    Encapsulates the logic for evaluating Gate 3: Epistemic Independence.
    Addresses the 'Algorithmic Monoculture' (Section 3.2 & RQ2).
    """
    
    @staticmethod
    def is_satisfied(evidence_set: FrozenSet[EvidenceTuple], strict_mode: bool = True) -> bool:
        """
        Evaluates methodological diversity.
        
        Args:
            evidence_set: The set of PASSING evidence tuples for a specific domain.
            strict_mode: If True, requires at least one non-LLM methodology for high-risk domains.
            
        Returns:
            bool: True if epistemic independence is satisfied, thereby breaking the echo chamber.
        """
        methodologies_used = {e.methodology for e in evidence_set}
        
        if not strict_mode:
            # In non-strict mode, differing inputs (e.g., different LLM prompts) might suffice
            input_hashes = {e.inputs_hash for e in evidence_set}
            return len(input_hashes) > 1 or len(methodologies_used) > 1

        # Strict Mode: To break the LLM Monoculture, there MUST be at least one 
        # non-LLM methodology (Deterministic, Symbolic, or Human) contributing to the PASS.
        has_non_llm = any(
            m in [MethodologyClass.DETERMINISTIC_STATIC, 
                  MethodologyClass.SYMBOLIC_EXECUTION, 
                  MethodologyClass.HUMAN_EXPERT]
            for m in methodologies_used
        )
        return has_non_llm


class ComplianceGateEvaluator:
    """
    The central evaluator that operationalizes Equation 3.
    Decides Merge Eligibility purely based on observables, rejecting heuristics here.
    """

    @staticmethod
    def evaluate(
        commit_hash: str, 
        domain: RiskDomain, 
        obligations: FrozenSet[ReviewObligation], 
        evidence_log: Iterable[EvidenceTuple]
    ) -> Tuple[bool, str]:
        r"""
        Evaluates the three compliance gates for a specific domain.
        
        Args:
            commit_hash: The current HEAD commit $h_t$.
            domain: The risk domain $d$ being evaluated.
            obligations: The project-defined obligations $\Omega_d(p, h_t)$.
            evidence_log: The global or scoped log of gathered evidence $\mathcal{E}$.
            
        Returns:
            Tuple[bool, str]: (IsEligible, JustificationReason)
        """
        # Filter evidence strictly to the current commit and domain
        valid_evidence = frozenset(
            e for e in evidence_log 
            if e.commit_hash == commit_hash and e.domain == domain
        )
        
        # Edge case: If no obligations were defined for this domain, it is trivially eligible
        # provided no explicit failing evidence exists for the commit.
        if not obligations:
            failing = [e for e in valid_evidence if e.result == EvidenceResult.FAIL and not e.is_resolved]
            if failing:
                return False, f"Gate 2 Failed: Unresolved failure exists despite empty obligation set."
            return True, f"Eligible: No obligations defined for domain {domain.value}."

        # ---------------------------------------------------------
        # Gate 2: Unresolved Failure Check (∄ e.result = Fail)
        # ---------------------------------------------------------
        # Evaluated first for fail-fast efficiency.
        unresolved_failures = [
            e for e in valid_evidence 
            if e.result == EvidenceResult.FAIL and not e.is_resolved
        ]
        if unresolved_failures:
            logger.info(f"Gate 2 Failed [{domain.value}]: Found {len(unresolved_failures)} unresolved failure(s).")
            return False, "Gate 2 Failed: Unresolved failures present."

        # ---------------------------------------------------------
        # Gate 1: Coverage via Set Union (⋃ e.scope ⊇ Ω_d)
        # ---------------------------------------------------------
        # This mathematically eliminates the Overlap Fallacy.
        passing_evidence = frozenset(e for e in valid_evidence if e.result == EvidenceResult.PASS)
        
        union_of_scopes = set()
        for e in passing_evidence:
            union_of_scopes.update(e.scope)
            
        if not obligations.issubset(union_of_scopes):
            missing = obligations - union_of_scopes
            logger.info(f"Gate 1 Failed [{domain.value}]: Overlap fallacy bypassed. Missing obligations: {missing}")
            return False, f"Gate 1 Failed: Missing coverage for {len(missing)} obligation(s)."

        # ---------------------------------------------------------
        # Gate 3: Epistemic Independence
        # ---------------------------------------------------------
        # If there are obligations to fulfill, check if they were fulfilled independently.
        if obligations and not EpistemicIndependenceChecker.is_satisfied(passing_evidence, strict_mode=True):
            logger.warning(f"Gate 3 Failed [{domain.value}]: Epistemic Independence violated (Monoculture detected).")
            return False, "Gate 3 Failed: Algorithmic monoculture detected. Requires orthogonal verification."

        # All gates passed
        logger.info(f"All Compliance Gates passed for commit {commit_hash[:7]} in domain {domain.value}.")
        return True, "Eligible: All gates passed successfully."


# Aliases to align cleanly with __init__.py exports and historical conventions
ComplianceGate = ComplianceGateEvaluator
EvidenceLog = List[EvidenceTuple]
