"""
Algorithmic learner-state estimation framework based on observable interaction behavior.

This package contains exact, testable mathematical models for estimating:
- Mastery (Bayesian Knowledge Tracing)
- Confidence (EWMA behavioral estimator)
- Confusion (EWMA over behavioral confusion signals)
- Cognitive Load (EWMA over observable interaction-based load indicators)
"""

from .bkt import update_mastery
from .confidence import calculate_confidence_evidence, update_confidence
from .confusion import calculate_confusion_signal, update_confusion
from .cognitive_load import (
    calculate_time_stress,
    calculate_attempt_stress,
    calculate_error_stress,
    calculate_hint_stress,
    calculate_load_signal,
    update_cognitive_load
)
from .progress import calculate_concept_progress, calculate_overall_progress
from .scaffolding import calculate_scaffolding_score, determine_scaffolding_level
