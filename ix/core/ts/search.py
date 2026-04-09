"""Timeseries search filtering and ranking (PostgreSQL FTS + LIKE fallback)."""

from __future__ import annotations

import re


def build_search_filter_and_order(query, search: str, Timeseries_model):
    """Apply search filtering and ranking to a timeseries SQLAlchemy query.

    Returns the modified query with filters and ordering applied.
    Works with both PostgreSQL (weighted FTS) and other backends (LIKE fallback).
    """
    from sqlalchemy import and_, case, func, or_

    term = search.strip().lower()
    tokens = [t for t in re.split(r"\s+", term) if t]

    if not tokens:
        return query

    code_l = func.lower(func.coalesce(Timeseries_model.code, ""))
    name_l = func.lower(func.coalesce(Timeseries_model.name, ""))
    source_l = func.lower(func.coalesce(Timeseries_model.source, ""))
    category_l = func.lower(func.coalesce(Timeseries_model.category, ""))
    provider_l = func.lower(func.coalesce(Timeseries_model.provider, ""))
    asset_class_l = func.lower(func.coalesce(Timeseries_model.asset_class, ""))
    country_l = func.lower(func.coalesce(Timeseries_model.country, ""))
    source_code_l = func.lower(func.coalesce(Timeseries_model.source_code, ""))

    dialect_name = (
        getattr(getattr(query.session, "bind", None), "dialect", None).name
        if getattr(getattr(query.session, "bind", None), "dialect", None) is not None
        else ""
    )

    if dialect_name == "postgresql":
        # Weighted FTS vector:
        # code/name strongest; metadata moderate; source_code lower.
        search_vector = (
            func.setweight(
                func.to_tsvector("simple", func.coalesce(Timeseries_model.code, "")),
                "A",
            )
            .op("||")(
                func.setweight(
                    func.to_tsvector(
                        "simple", func.coalesce(Timeseries_model.name, "")
                    ),
                    "A",
                )
            )
            .op("||")(
                func.setweight(
                    func.to_tsvector(
                        "simple", func.coalesce(Timeseries_model.source, "")
                    ),
                    "B",
                )
            )
            .op("||")(
                func.setweight(
                    func.to_tsvector(
                        "simple", func.coalesce(Timeseries_model.category, "")
                    ),
                    "B",
                )
            )
            .op("||")(
                func.setweight(
                    func.to_tsvector(
                        "simple", func.coalesce(Timeseries_model.provider, "")
                    ),
                    "C",
                )
            )
            .op("||")(
                func.setweight(
                    func.to_tsvector(
                        "simple", func.coalesce(Timeseries_model.asset_class, "")
                    ),
                    "C",
                )
            )
            .op("||")(
                func.setweight(
                    func.to_tsvector(
                        "simple", func.coalesce(Timeseries_model.country, "")
                    ),
                    "D",
                )
            )
            .op("||")(
                func.setweight(
                    func.to_tsvector(
                        "simple", func.coalesce(Timeseries_model.source_code, "")
                    ),
                    "D",
                )
            )
        )
        ts_query = func.plainto_tsquery("simple", term)

        # Keep prefix path so incremental typing ("sp", "usd") still feels responsive.
        prefix_match = or_(
            code_l.like(f"{term}%"),
            name_l.like(f"{term}%"),
            source_l.like(f"{term}%"),
            category_l.like(f"{term}%"),
        )
        if len(term) >= 3:
            prefix_match = or_(prefix_match, source_code_l.like(f"{term}%"))

        fts_match = search_vector.op("@@")(ts_query)
        query = query.filter(or_(fts_match, prefix_match))

        rank_expr = (
            func.ts_rank_cd(search_vector, ts_query)
            + case((code_l == term, 5.0), else_=0.0)
            + case((code_l.like(f"{term}%"), 2.6), else_=0.0)
            + case((name_l.like(f"{term}%"), 1.2), else_=0.0)
            + case((source_l.like(f"{term}%"), 0.6), else_=0.0)
            + case((category_l.like(f"{term}%"), 0.5), else_=0.0)
        )

        query = query.order_by(
            rank_expr.desc(),
            Timeseries_model.favorite.desc(),
            Timeseries_model.code.asc(),
        )
    else:
        # Fallback: token-aware LIKE ranking for non-PostgreSQL backends.
        token_filters = []
        for tok in tokens:
            tok_like = f"%{tok}%"
            token_columns = [
                code_l.like(tok_like),
                name_l.like(tok_like),
                source_l.like(tok_like),
                category_l.like(tok_like),
                provider_l.like(tok_like),
                asset_class_l.like(tok_like),
                country_l.like(tok_like),
            ]
            if len(tok) >= 3:
                token_columns.append(source_code_l.like(tok_like))
            token_filters.append(or_(*token_columns))

        query = query.filter(and_(*token_filters))

        rank_expr = (
            case((code_l == term, 1000), else_=0)
            + case((code_l.like(f"{term}%"), 600), else_=0)
            + case((name_l == term, 350), else_=0)
            + case((name_l.like(f"{term}%"), 220), else_=0)
            + case((source_code_l.like(f"{term}%"), 180), else_=0)
            + case((code_l.like(f"%{term}%"), 150), else_=0)
            + case((name_l.like(f"%{term}%"), 120), else_=0)
            + case((source_l.like(f"%{term}%"), 70), else_=0)
            + case((category_l.like(f"%{term}%"), 60), else_=0)
        )

        for tok in tokens:
            tok_like = f"%{tok}%"
            rank_expr = (
                rank_expr
                + case((code_l.like(tok_like), 70), else_=0)
                + case((name_l.like(tok_like), 45), else_=0)
                + case((source_l.like(tok_like), 25), else_=0)
                + case((category_l.like(tok_like), 20), else_=0)
                + case((provider_l.like(tok_like), 18), else_=0)
                + case((asset_class_l.like(tok_like), 15), else_=0)
                + case((country_l.like(tok_like), 12), else_=0)
            )
            if len(tok) >= 3:
                rank_expr = rank_expr + case(
                    (source_code_l.like(tok_like), 10), else_=0
                )

        query = query.order_by(
            rank_expr.desc(),
            Timeseries_model.favorite.desc(),
            Timeseries_model.code.asc(),
        )

    return query
