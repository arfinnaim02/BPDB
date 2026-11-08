"""Research dataset policy, separate from source observations and model parameters."""

GOAL = (
    "A trustworthy dataset for each research question, using verified "
    "comparable variables and reporting periods."
)
RULE_VERSION = "research_dataset_profiles_v1"
PROPOSED_MODERN_START = "2025-01-01"
CORE_METRICS = frozenset(
    {
        "day_peak_generation",
        "evening_peak_generation",
        "evening_peak_demand",
        "maximum_generation",
        "energy_generated",
    }
)
