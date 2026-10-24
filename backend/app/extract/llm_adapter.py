"""
Optional LLM Extractor Adapter and Hybrid Merger.
Provides a pluggable LLM interface (default OFF) that merges with lower priority
than deterministic extraction, ensuring 100% offline functionality.
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

from backend.app.extract.deterministic_extractor import DeterministicExtractor
from backend.app.extract.models import ExtractedRequirements


@runtime_checkable
class ILlmExtractor(Protocol):
    """Protocol for optional large language model extractors."""

    def is_enabled(self) -> bool:
        """Returns True if the LLM extractor is active and configured."""
        ...

    def extract(self, announcement_text: str) -> ExtractedRequirements:
        """Extracts requirements using an LLM. Receives ONLY announcement text."""
        ...


class MockLlmExtractor:
    """
    Reference/example implementation of ILlmExtractor.
    Disabled by default via environment variable 'ENABLE_LLM_EXTRACTOR'.
    """

    def __init__(self, enabled: bool = False) -> None:
        env_flag = os.getenv("ENABLE_LLM_EXTRACTOR", "false").lower() == "true"
        self._enabled = enabled or env_flag

    def is_enabled(self) -> bool:
        return self._enabled

    def extract(self, announcement_text: str) -> ExtractedRequirements:
        if not self.is_enabled():
            raise RuntimeError("LlmExtractor is disabled. Enable it explicitly via flag or ENABLE_LLM_EXTRACTOR=true.")

        # In offline/mock mode, delegate to fallback parser with lower baseline confidence
        deterministic = DeterministicExtractor()
        extracted = deterministic.extract(announcement_text)
        # Assign lower confidence to signify LLM origin
        return extracted.model_copy(update={"overall_confidence": round(extracted.overall_confidence * 0.85, 3)})


class HybridExtractionEngine:
    """
    Coordinates extraction by running the deterministic extractor first,
    and optionally falling back to an LLM extractor for unfilled fields.
    Deterministic results ALWAYS take precedence.
    """

    def __init__(
        self,
        deterministic_extractor: DeterministicExtractor | None = None,
        llm_extractor: ILlmExtractor | None = None,
    ) -> None:
        self.deterministic = deterministic_extractor or DeterministicExtractor()
        self.llm = llm_extractor

    def extract(self, text: str) -> ExtractedRequirements:
        # Step 1: Run primary deterministic extractor
        primary = self.deterministic.extract(text)

        # Step 2: If LLM is not provided or disabled, return deterministic output directly
        if self.llm is None or not self.llm.is_enabled():
            return primary

        # Step 3: Run LLM extractor with lower priority
        try:
            secondary = self.llm.extract(text)
        except Exception:
            # Resilient: never fail deterministic extraction due to LLM failure
            return primary

        # Step 4: Merge secondary fields only where primary was empty
        updates: dict[str, object] = {}

        for field_name in (
            "company_name",
            "drive_date",
            "mode",
            "ctc_lpa",
            "stipend_monthly",
            "role",
            "location",
            "bond_details",
            "cgpa_min",
            "tenth_percentage_min",
            "twelfth_percentage_min",
            "diploma_percentage_min",
            "allowed_branches",
            "allowed_programs",
            "batch_year",
            "active_backlogs_max",
            "historical_backlogs_max",
            "gap_years_max",
            "allow_gap_during_degree",
        ):
            primary_val = getattr(primary, field_name)
            secondary_val = getattr(secondary, field_name)

            if primary_val is None and secondary_val is not None:
                # Fill missing field with lower priority/confidence
                updates[field_name] = secondary_val

        if not primary.rounds and secondary.rounds:
            updates["rounds"] = secondary.rounds

        if updates:
            return primary.model_copy(update=updates)

        return primary
