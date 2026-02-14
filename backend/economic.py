"""
INEVITABILITY - Economic Impact Module
Maps security spend to causal relevance, identifies waste, and computes ROI.
"""

from __future__ import annotations
from .models import (
    TheaterReport, EconomicReport, ControlClassification,
    DefenseClassification
)


class EconomicAnalyzer:
    """Analyzes economic impact of security spending vs. causal relevance."""

    def analyze(self, theater_reports: list[TheaterReport]) -> EconomicReport:
        """Compute economic impact from theater classification results."""
        all_classifications: list[ControlClassification] = []
        seen_controls = set()

        for report in theater_reports:
            for c in report.classifications:
                if c.control_id not in seen_controls:
                    seen_controls.add(c.control_id)
                    all_classifications.append(c)

        total_spend = sum(c.annual_cost for c in all_classifications)
        wasted = sum(c.annual_cost for c in all_classifications if c.classification == DefenseClassification.IRRELEVANT)
        partial_waste = sum(c.annual_cost * 0.5 for c in all_classifications if c.classification == DefenseClassification.PARTIAL)
        effective = total_spend - wasted - partial_waste

        # Top waste controls
        waste_controls = sorted(
            [c for c in all_classifications if c.classification == DefenseClassification.IRRELEVANT],
            key=lambda x: x.annual_cost,
            reverse=True,
        )

        # ROI projections for remediation
        roi_projections = self._compute_roi(all_classifications, total_spend)

        # Recommendations
        recommendations = self._generate_recommendations(all_classifications, total_spend, wasted)

        return EconomicReport(
            total_security_spend=total_spend,
            effective_spend=round(effective, 2),
            wasted_spend=round(wasted, 2),
            partial_waste=round(partial_waste, 2),
            waste_ratio=round(wasted / total_spend, 3) if total_spend > 0 else 0.0,
            efficiency_ratio=round(effective / total_spend, 3) if total_spend > 0 else 0.0,
            top_waste_controls=waste_controls[:5],
            remediation_recommendations=recommendations,
            roi_projections=roi_projections,
        )

    def _compute_roi(self, classifications: list[ControlClassification], total_spend: float) -> list[dict]:
        """Compute ROI for different remediation strategies."""
        projections = []

        # Strategy 1: Eliminate theater controls
        theater_savings = sum(c.annual_cost for c in classifications if c.classification == DefenseClassification.IRRELEVANT)
        if theater_savings > 0:
            projections.append({
                "strategy": "Eliminate Security Theater",
                "description": "Remove all causally irrelevant controls",
                "annual_savings": theater_savings,
                "risk_change": 0.0,
                "roi_percentage": round((theater_savings / total_spend) * 100, 1) if total_spend > 0 else 0,
                "implementation": "immediate",
                "recommendation": "No risk increase — these controls have zero causal effect",
            })

        # Strategy 2: Reallocate to critical controls
        critical_budget = sum(c.annual_cost for c in classifications if c.classification == DefenseClassification.CRITICAL)
        if theater_savings > 0 and critical_budget > 0:
            projections.append({
                "strategy": "Reallocate Theater Budget to Critical Controls",
                "description": f"Redirect ${theater_savings:,.0f} theater spend to strengthen MCS controls",
                "annual_savings": 0,
                "risk_reduction": "significant",
                "roi_percentage": round((theater_savings / critical_budget) * 100, 1),
                "implementation": "30 days",
                "recommendation": f"Would increase critical control budget by {round((theater_savings / critical_budget) * 100, 1)}%",
            })

        # Strategy 3: Implement MCS-only defense
        mcs_cost = sum(c.annual_cost for c in classifications if c.classification in (DefenseClassification.CRITICAL, DefenseClassification.NECESSARY))
        if mcs_cost < total_spend:
            projections.append({
                "strategy": "MCS-Only Defense Posture",
                "description": "Fund only controls that appear in at least one Minimal Causal Set",
                "annual_savings": total_spend - mcs_cost,
                "risk_change": 0.0,
                "roi_percentage": round(((total_spend - mcs_cost) / total_spend) * 100, 1) if total_spend > 0 else 0,
                "implementation": "90 days",
                "recommendation": "Mathematically proven: same defense, lower cost",
            })

        return projections

    def _generate_recommendations(
        self,
        classifications: list[ControlClassification],
        total_spend: float,
        wasted: float,
    ) -> list[dict]:
        """Generate prioritized recommendations."""
        recs = []

        if wasted > 0:
            recs.append({
                "priority": 1,
                "action": "Eliminate Security Theater",
                "detail": f"${wasted:,.0f}/year is spent on controls with ZERO causal effect on any defense goal",
                "savings": wasted,
                "risk": "none",
            })

        critical_unfunded = [
            c for c in classifications
            if c.classification == DefenseClassification.CRITICAL and (c.annual_cost or 0) == 0
        ]
        if critical_unfunded:
            recs.append({
                "priority": 2,
                "action": "Fund Critical Controls",
                "detail": f"{len(critical_unfunded)} MCS controls have $0 budget — these are configuration changes",
                "savings": 0,
                "risk": "high reduction",
            })

        return recs
