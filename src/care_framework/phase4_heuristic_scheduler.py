# -*- coding: utf-8 -*-
"""
Phase 4: Heuristic Task Scheduling for Marginal Yield
=====================================================

This module implements the formalization described in Section 4.4 of the EMSE submission:
"Review Dynamics in the Era of Agentic SE: Balancing Speed and Depth through the CARE Framework"

Academic Design Philosophy:
---------------------------
Traditional review queues operate on FIFO (First-In, First-Out) or static risk scoring. 
However, human cognitive capacity is a strictly bounded resource (Budget B_t). CARE models
code review as a resource allocation (Knapsack) problem.

Crucial Epistemological Limitation:
The true Marginal Expected Yield (ΔY) of a review task is fundamentally COUNTERFACTUAL. 
We cannot observe what a human *would have* found if a skipped task had been assigned. 
Therefore, this module implements an AUDITABLE HEURISTIC PROXY (ΔY_hat), derived from 
pre-review observables, wait-time escalators, and existing automated evidence.

Key Formalizations (Equations 5 & 6):
1. Bifurcation: Mandatory tasks (required by Phase 3 Epistemic policies) bypass optimization.
2. Diminishing Returns: High machine verifiability (V_machine) decays the marginal human yield.
3. Submodular Approximation: Discretionary tasks are scheduled via a greedy knapsack 
   approximation (sorted by ΔY_hat / Cost) to maximize defect discovery under budget B_t.

Standards Complied:
- PEP 484 Type Hinting.
- Deterministic tie-breaking for absolute bit-for-bit reproducibility (RQ1 Historical Replay).
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Set, Optional

# Assuming relative imports from prior phases
from .phase2_obligations import RiskDomain, PreReviewObservables

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ReviewTask:
    """
    Formal representation of a candidate review task (τ).
    τ = <p, h_t, d, role>
    """
    pr_id: str
    commit_hash: str
    domain: RiskDomain
    is_mandatory: bool            # True if Phase 3 dictates human sign-off is non-negotiable
    cost_estimate: float          # Estimated human cognitive budget required (e.g., hours/slots)
    wait_time_days: float         # Time elapsed since task became eligible (for starvation prevention)
    observables: PreReviewObservables # The pre-review feature vector X

    def __post_init__(self):
        if self.cost_estimate <= 0:
            raise ValueError(f"Task cost must be positive, got {self.cost_estimate}")


class MarginalExpectedYieldProxy:
    """
    Computes the heuristic proxy ΔY_hat (Marginal Expected Yield) for discretionary tasks.
    Formalized in Equation 6 of Section 4.4.
    """
    
    # Pre-registered Operational Policy Parameters
    GAMMA_VERIFIABILITY_DECAY: float = 0.70  # Controls rate of diminishing returns under machine verification
    LAMBDA_WAIT_ESCALATOR: float = 0.10      # Linear daily wait-time escalator (per day)
    EPSILON_BASELINE_FLOOR: float = 0.05    # Minimum non-zero risk floor preventing task zeroing & starvation
    
    @classmethod
    def calculate_yield(
        cls, 
        task: ReviewTask,
        gamma: Optional[float] = None,
        lambda_wait: Optional[float] = None,
        epsilon_floor: Optional[float] = None
    ) -> float:
        """
        Estimates the counterfactual marginal yield of assigning a human reviewer to this task.
        
        Mathematical Specification (Equation 6):
        ΔY_hat(τ) = max(ε_floor, R_impact * U_context) * (1 - γ * V_machine) * (1 + λ * t_wait)
        
        Guarantees:
        1. Non-Zero Floor: Even tasks with R_impact=0 or U_context=0 retain a baseline floor ε=0.05,
           ensuring that wait_escalator always activates and prevents starvation.
        2. Bounded Machine Decay: Machine verifiability cannot reduce yield below (1 - γ) = 0.30.
        3. Explicit Units: t_wait is strictly measured in elapsed calendar days.
        """
        g = gamma if gamma is not None else cls.GAMMA_VERIFIABILITY_DECAY
        l_w = lambda_wait if lambda_wait is not None else cls.LAMBDA_WAIT_ESCALATOR
        eps = epsilon_floor if epsilon_floor is not None else cls.EPSILON_BASELINE_FLOOR
        
        obs = task.observables
        
        # 1. Base Risk Factor with Baseline Floor (ε_floor):
        raw_base_risk = obs.r_impact.get(task.domain, 0.0) * obs.u_context
        base_risk = max(eps, raw_base_risk)
        
        # 2. Diminishing Marginal Returns (Evidence Decay):
        evidence_decay = max(0.10, 1.0 - g * min(1.0, obs.v_machine))
        
        # 3. Starvation Prevention (Wait-time Escalator in days):
        t_wait_days = max(0.0, task.wait_time_days)
        wait_escalator = 1.0 + l_w * t_wait_days
        
        # Yield Proxy calculation
        yield_proxy = base_risk * evidence_decay * wait_escalator
        
        return yield_proxy


class HeuristicScheduler:
    """
    The Phase 4 Engine: Solves the Budget-Constrained Task Allocation Problem.
    """
    
    def __init__(self, daily_budget: float):
        """
        Args:
            daily_budget (float): The total available human cognitive budget B_t.
        """
        if daily_budget < 0:
            raise ValueError("Daily budget (B_t) cannot be negative.")
        self.daily_budget = daily_budget
        logger.debug(f"HeuristicScheduler initialized with Budget B_t = {self.daily_budget}")

    def optimize_queue(self, candidate_tasks: List[ReviewTask]) -> Tuple[List[ReviewTask], List[ReviewTask]]:
        """
        Allocates the budget B_t across candidate tasks to maximize expected yield.
        
        Args:
            candidate_tasks: All tasks currently eligible for scheduling.
            
        Returns:
            Tuple containing:
                - Scheduled Tasks: Tasks that made it into today's queue.
                - Deferred Tasks: Tasks deferred due to budget constraints.
        """
        remaining_budget = self.daily_budget
        scheduled_tasks: List[ReviewTask] = []
        deferred_tasks: List[ReviewTask] = []
        
        # ---------------------------------------------------------
        # Step 1: Bifurcation - Fulfill Mandatory Policy Obligations
        # ---------------------------------------------------------
        # Mandatory tasks (e.g., breaking epistemic echo chambers on critical paths) 
        # bypass the yield optimization and unconditionally consume budget.
        mandatory_tasks = [t for t in candidate_tasks if t.is_mandatory]
        discretionary_tasks = [t for t in candidate_tasks if not t.is_mandatory]
        
        for task in mandatory_tasks:
            if remaining_budget > 0:  # Allow fractional over-budgeting for the boundary task
                scheduled_tasks.append(task)
                remaining_budget -= task.cost_estimate
            else:
                # System is completely saturated; even mandatory tasks must wait.
                # In real CI, this triggers a "Capacity Alert".
                deferred_tasks.append(task)
                
        if remaining_budget <= 0:
            logger.warning("Budget exhausted by mandatory tasks. All discretionary tasks deferred.")
            deferred_tasks.extend(discretionary_tasks)
            return scheduled_tasks, deferred_tasks

        # ---------------------------------------------------------
        # Step 2: Knapsack Approximation for Discretionary Tasks
        # ---------------------------------------------------------
        # Compute ΔY_hat and cost-efficiency (Yield per unit of cognitive cost)
        efficiency_queue = []
        for task in discretionary_tasks:
            yield_proxy = MarginalExpectedYieldProxy.calculate_yield(task)
            efficiency = yield_proxy / task.cost_estimate
            efficiency_queue.append((efficiency, yield_proxy, task))
            
        # Sort using a deterministic greedy strategy for 0-1 Knapsack approximation.
        # Tie-breaker 1: Absolute Yield (favors high-value tasks if efficiency is equal)
        # Tie-breaker 2: PR ID string (Guarantees reproducibility across CPU architectures)
        efficiency_queue.sort(
            key=lambda x: (round(x[0], 9), round(x[1], 9), x[2].pr_id),
            reverse=True
        )
        
        # Greedy allocation
        for efficiency, yield_proxy, task in efficiency_queue:
            if task.cost_estimate <= remaining_budget:
                scheduled_tasks.append(task)
                remaining_budget -= task.cost_estimate
                logger.debug(f"Scheduled Task {task.pr_id} [{task.domain.value}]: Yield={yield_proxy:.3f}, Cost={task.cost_estimate}")
            else:
                deferred_tasks.append(task)
                
        logger.info(
            f"Scheduling complete. Scheduled: {len(scheduled_tasks)}, "
            f"Deferred: {len(deferred_tasks)}, Residual Budget: {remaining_budget:.2f}"
        )
        
        return scheduled_tasks, deferred_tasks
