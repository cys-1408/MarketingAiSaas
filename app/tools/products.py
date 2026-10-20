"""Approved product facts: the only permitted source of product claims.

Content generation must validate factual claims against these approved
facts; claims lacking approved evidence are flagged (never silently passed
through).  Workspace-scoped and read-only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tenancy import WorkspaceContext, authorize_workspace
from app.db.models import Product


@dataclass(slots=True)
class ProductFactRequest:
    product_id: str | None
    topic: str | None = None


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_products(self, *, workspace_id: str, user_id: str) -> list[dict[str, Any]]:
        authorize_workspace(self.db, user_id=user_id, workspace_id=workspace_id)
        products = self.db.execute(
            select(Product).where(Product.workspace_id == workspace_id)
        ).scalars().all()
        return [self._serialize(p) for p in products]

    def get_product_facts(
        self, *, workspace_id: str, user_id: str, product_id: str | None, topic: str | None = None
    ) -> dict[str, Any]:
        authorize_workspace(self.db, user_id=user_id, workspace_id=workspace_id)
        stmt = select(Product).where(Product.workspace_id == workspace_id)
        if product_id:
            product = self.db.get(Product, product_id)
            if product is None or product.workspace_id != workspace_id:
                return {"found": False, "facts": [], "approved_claims": []}
        else:
            product = self.db.scalars(stmt.limit(1)).first()
            if product is None:
                return {"found": False, "facts": [], "approved_claims": []}
        facts = list(product.features) + list(product.limitations)
        if topic:
            lowered = topic.lower()
            facts = [f for f in facts if any(w in str(f).lower() for w in lowered.split())]
        return {
            "found": True,
            "product": self._serialize(product),
            "facts": facts,
            "approved_claims": list(product.approved_claims),
            "freshness": {"source_version": product.source_version, "source_id": product.source_id},
        }

    def validate_claim(
        self, *, workspace_id: str, claim: str
    ) -> dict[str, Any]:
        """Check a content claim against approved facts (deterministic)."""
        product = self.db.scalars(
            select(Product).where(Product.workspace_id == workspace_id).limit(1)
        ).first()
        if product is None:
            return {
                "status": "no_approved_source",
                "supported": False,
                "detail": "no approved product facts exist in this workspace",
            }
        approved_corpus = product.approved_claims + product.features + product.limitations
        claim_words = set(re.findall(r"[a-z0-9]+", claim.lower()))
        for fact in approved_corpus:
            fact_words = set(re.findall(r"[a-z0-9]+", str(fact).lower()))
            overlap = claim_words & fact_words
            if len(overlap) >= 2:
                return {
                    "status": "supported",
                    "supported_by": str(fact)[:200],
                    "source_id": product.source_id,
                    "source_version": product.source_version,
                }
        return {
            "status": "unsupported",
            "supported": False,
            "detail": "claim does not overlap enough with approved facts; remove or qualify it",
        }

    @staticmethod
    def _serialize(product: Product) -> dict[str, Any]:
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "features": list(product.features),
            "limitations": list(product.limitations),
            "source_id": product.source_id,
            "source_version": product.source_version,
        }
