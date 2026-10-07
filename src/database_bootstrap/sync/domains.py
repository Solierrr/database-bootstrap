from __future__ import annotations

from dataclasses import dataclass

DATASETS = (
    "local_units",
    "panel_offers",
    "professions",
    "technicians",
    "registrations",
    "affiliations",
    "shifts",
    "technical_services",
    "service_experiences",
    "assignments",
)


@dataclass(frozen=True)
class Stage:
    name: str
    query: str
    dataset: str
    key: tuple[str, ...]


NODE_STAGES = (
    Stage("LocalUnit", "local_units", "local_units", ("id",)),
    Stage("SolarModel", "solar_models", "panel_offers", ("model_id",)),
    Stage("Supplier", "suppliers", "panel_offers", ("supplier_id",)),
    Stage("SolarOffer", "solar_offers", "panel_offers", ("offer_id",)),
    Stage("Profession", "professions", "professions", ("profession_id",)),
    Stage("Technician", "technicians", "technicians", ("technician_id",)),
    Stage("TechnicianAffiliation", "affiliations", "affiliations", ("affiliation_id",)),
    Stage("Shift", "shifts", "shifts", ("shift_id",)),
    Stage("TechnicalService", "technical_services", "technical_services", ("service_id",)),
    Stage(
        "ServiceExperience",
        "service_experiences",
        "service_experiences",
        ("technician_id", "normalized_purpose"),
    ),
)

RELATIONSHIP_STAGES = (
    Stage("OF_MODEL", "offer_model", "panel_offers", ("offer_id", "model_id")),
    Stage("FROM_SUPPLIER", "offer_supplier", "panel_offers", ("offer_id", "supplier_id")),
    Stage("REGISTERED_AS", "technician_profession", "registrations", ("technician_id", "profession_id")),
    Stage("OF_TECHNICIAN", "affiliation_technician", "affiliations", ("affiliation_id", "technician_id")),
    Stage("HAS_SHIFT", "technician_shift", "shifts", ("technician_id", "shift_id")),
    Stage(
        "HAS_EXPERIENCE",
        "technician_experience",
        "service_experiences",
        ("technician_id", "normalized_purpose"),
    ),
    Stage(
        "ASSIGNED_TO",
        "affiliation_service",
        "assignments",
        ("executor_id", "affiliation_id", "service_id"),
    ),
)
