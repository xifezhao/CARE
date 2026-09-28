# -*- coding: utf-8 -*-
"""
Phase 1: Commit-Bound State Machine
===================================

This module implements the formalization described in Section 4.1 of the EMSE submission:
"Review Dynamics in the Era of Agentic SE: Balancing Speed and Depth through the CARE Framework"

Academic Design Philosophy:
---------------------------
In Agentic SE, autonomous agents rapidly push iterative commits. Tracking evidence at the
Pull Request (PR) level introduces 'Temporal Ambiguity' (e.g., old approvals validating new
hallucinations). 

This module enforces the **Axiom of Temporal Invalidation**:
1. All evaluation states S(p, h_t) are strictly bound to a specific commit hash (h_t).
2. Any newly registered commit h_{t+1} strictly invalidates prior states and intersecting evidence.
3. The state transitions are governed by a deterministic precedence hierarchy (Equation 1).

Standards Complied:
- PEP 484 Type Hinting for static verification.
- PEP 257 Docstrings for theoretical traceability.
- Immutable data structures to prevent state mutation side-effects.
"""

import logging
from enum import Enum, unique
from dataclasses import dataclass, field
from typing import Optional, FrozenSet, Dict

# Module-level logger for auditable simulation trails
logger = logging.getLogger(__name__)

@unique
class EvaluationState(Enum):
    """
    Formal state space for PR evaluation bounded to a specific commit.
    Maps exactly to the piecewise function (Equation 1) in Section 4.1.
    """
    BLOCK = "Block"   # Explicitly failed machine-verifiable hard constraints.
    MANUAL = "Manual" # Infrastructure timeouts or unknown states (fail-safe).
    WARN = "Warn"     # Soft constraints failed; requires logged justification.
    ROUTE = "Route"   # Baseline passed; eligible for Phase 4 (Heuristic Scheduling).


@dataclass(frozen=True)
class Commit:
    """
    An immutable representation of a git commit. 
    Immutability is critical to ensure that historical replay simulations (RQ1)
    do not accidentally mutate historical features (Data Leakage).
    """
    pr_id: str
    commit_hash: str
    timestamp: float
    modified_files: FrozenSet[str] = field(default_factory=frozenset)
    
    def __post_init__(self):
        if not self.commit_hash or len(self.commit_hash) < 7:
            raise ValueError(f"Invalid commit hash provided: {self.commit_hash}")


@dataclass(frozen=True)
class CIConstraintContext:
    """
    A deterministic snapshot of continuous integration (CI) constraints 
    evaluated against a specific commit h_t.
    """
    has_hard_failures: bool = False
    has_infra_timeout_or_unknown: bool = False
    has_soft_failures: bool = False


class TemporalInvalidationError(Exception):
    """
    Raised when a temporal violation occurs (e.g., trying to evaluate an old commit 
    after a newer one has already been registered). Prevents chronological data leakage.
    """
    pass


class CommitStateMachine:
    """
    Maintains the state S(p, h_t) for a given Pull Request p.
    Enforces the precedence hierarchy and the Principle of Temporal Invalidation.
    """

    def __init__(self, pr_id: str):
        """
        Initializes the state machine for a specific Pull Request.
        
        Args:
            pr_id (str): Unique identifier for the Pull Request.
        """
        self.pr_id: str = pr_id
        self.current_commit: Optional[Commit] = None
        self.current_state: Optional[EvaluationState] = None
        
        # Audit log for temporal traceability (crucial for Phase 5 IPW calibration)
        self._history: Dict[str, EvaluationState] = {}
        
        logger.debug(f"Initialized CommitStateMachine for PR: {self.pr_id}")

    @property
    def history(self) -> Dict[str, EvaluationState]:
        """Exposes an immutable snapshot of historical evaluation states."""
        return dict(self._history)

    def register_new_commit(self, new_commit: Commit) -> None:
        """
        Registers a new commit h_{t+1}, enforcing the Axiom of Temporal Invalidation.
        
        Args:
            new_commit (Commit): The incoming commit to bind to the state machine.
            
        Raises:
            TemporalInvalidationError: If the incoming commit is chronologically older 
                                       than the current HEAD.
        """
        if self.current_commit is not None:
            if new_commit.timestamp <= self.current_commit.timestamp:
                raise TemporalInvalidationError(
                    f"Temporal violation: New commit {new_commit.commit_hash} "
                    f"({new_commit.timestamp}) is not newer than current HEAD "
                    f"{self.current_commit.commit_hash} ({self.current_commit.timestamp})."
                )
            
            # Temporal Invalidation Logic
            logger.info(
                f"[PR {self.pr_id}] Axiom of Temporal Invalidation triggered: "
                f"{self.current_commit.commit_hash} -> {new_commit.commit_hash}. "
                f"Prior state {self.current_state} explicitly invalidated."
            )
            
            # Archive the old state for offline auditing (Phase 5)
            self._history[self.current_commit.commit_hash] = self.current_state

        # Update HEAD and reset state (awaiting CI constraint evaluation)
        self.current_commit = new_commit
        self.current_state = None

    def evaluate_state(self, constraints: CIConstraintContext) -> EvaluationState:
        """
        Executes Equation 1: Deterministic Precedence Hierarchy.
        
        This method strictly maps CI constraints to the discrete state space,
        preventing 'black-box' heuristic approximations at the merge-eligibility layer.
        
        Args:
            constraints (CIConstraintContext): The observed CI outcomes for the HEAD commit.
            
        Returns:
            EvaluationState: The resolved state S(p, h_t).
            
        Raises:
            RuntimeError: If evaluate is called before registering a commit.
        """
        if self.current_commit is None:
            raise RuntimeError("Cannot evaluate state: No commit registered.")

        # Equation 1: Strict precedence evaluation
        if constraints.has_hard_failures:
            self.current_state = EvaluationState.BLOCK
        elif constraints.has_infra_timeout_or_unknown:
            self.current_state = EvaluationState.MANUAL
        elif constraints.has_soft_failures:
            self.current_state = EvaluationState.WARN
        else:
            self.current_state = EvaluationState.ROUTE

        logger.debug(
            f"[PR {self.pr_id} @ {self.current_commit.commit_hash[:7]}] "
            f"State evaluated to: {self.current_state.value}"
        )

        return self.current_state

    def get_current_state(self) -> Optional[EvaluationState]:
        """Returns the currently active evaluation state."""
        return self.current_state
