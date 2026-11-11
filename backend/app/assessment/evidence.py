"""Deterministic evidence and governance metadata for suitability decisions."""
from __future__ import annotations

from typing import Any, Dict, Iterable

from app.core.config import get_registration_config, get_suitability_rules, load_yaml


def _sources() -> Dict[str, Any]:
    return load_yaml("regulatory_sources.yaml")


def _rule_sources() -> Dict[str, str]:
    return {
        "R-COMPLIANCE": "rbi-kyc",
        "R-KYC": "rbi-kyc",
        "R-RISK": "sebi-investment-adviser",
        "R-HORIZON": "sebi-investment-adviser",
        "R-LOSS": "sebi-investment-adviser",
        "R-CONCENTRATION": "sebi-investment-adviser",
        "R-COMPLEX": "sebi-investment-adviser",
        "R-FX": "rbi-fx-deposits",
    }


def _source_ref(source_id: str) -> Dict[str, Any]:
    for source in _sources().get("sources", []):
        if source.get("id") == source_id:
            return {k: source[k] for k in ("id", "authority", "title", "url", "accessed")}
    return {"id": source_id, "status": "NOT_FOUND"}


def _classification(rule_id: str) -> str:
    if rule_id in {"R-COMPLIANCE", "R-KYC"}:
        return "regulatory_reference"
    if rule_id in _rule_sources():
        return "interpretation_pending_review"
    return "institution_policy"


def build_evidence(assessment: Dict[str, Any], data_gaps: Iterable[str]) -> Dict[str, Any]:
    """Create reviewable facts without changing the deterministic verdict."""
    rules = []
    checks = dict(assessment.get("checks", {}))
    checks.update(assessment.get("additional_checks", {}))
    checks.update({
        f"compliance_{name}": {
            **value,
            "rule_id": "R-COMPLIANCE",
            "facts": {"client": name, "comparison": "gate status"},
        }
        for name, value in assessment.get("compliance_flags", {}).items()
    })
    for check in checks.values():
        rule_id = check.get("rule_id", "R-COMPLIANCE")
        source_id = _rule_sources().get(rule_id)
        facts = check.get("facts") or {}
        rules.append({
            "rule_id": rule_id,
            "status": check.get("status"),
            "dimension": rule_id,
            "client_fact": facts.get("client"),
            "product_or_market_fact": facts.get("product"),
            "comparison": facts.get("comparison"),
            "threshold": facts.get("threshold"),
            "formula_or_rationale": check.get("reason"),
            "classification": _classification(rule_id),
            "source": _source_ref(source_id) if source_id else None,
            "missing_data": bool(facts.get("missing")) or False,
            "required_human_action": (
                "Resolve before finalisation."
                if check.get("status") != "PASS" else None
            ),
        })
    policy = get_suitability_rules()
    registration = get_registration_config()
    return {
        "schema_version": "1.0",
        "decision_scope": "single_product",
        "portfolio_ready": True,
        "portfolio_fields_reserved": [
            "underlying_concentration", "issuer_concentration",
            "currency_exposure", "structured_product_share", "correlated_stress",
        ],
        "governance": {
            "policy_version": policy.get("version", "unknown"),
            "registration_version": registration.get("version", "unknown"),
            "source_catalog_version": _sources().get("version"),
            "approval_status": "DRAFT_PENDING_COMPLIANCE_APPROVAL",
            "finalisation_requires_human_review": True,
        },
        "rules": rules,
        "data_gaps": list(data_gaps),
        "review_blockers": list(data_gaps) + [
            "Compliance approval is required before production finalisation."
        ],
    }
