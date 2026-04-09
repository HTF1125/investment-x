"""Universe ORM model."""

from __future__ import annotations

from typing import Dict, Optional

import pandas as pd
from sqlalchemy import Column, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ix.db.conn import Base


class Universe(Base):
    """Universe model."""

    __tablename__ = "universe"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name = Column(String, nullable=True)
    assets = Column(JSONB, default=list)  # List of Asset dicts

    @classmethod
    def from_name(cls, name: str):
        """Get universe by name."""
        from ix.db.conn import Session

        with Session() as session:
            universe = session.query(cls).filter(cls.name == name).first()
            if not universe:
                raise KeyError
            return universe

    def add_asset(self, asset: Dict[str, Optional[str]]) -> None:
        """Add asset to universe."""
        assets = self.assets.copy() if self.assets else []
        if isinstance(asset, dict):
            assets.append(asset)
        else:
            # Handle case where asset might be an object with code/name attributes
            assets.append(
                {
                    "code": getattr(asset, "code", None),
                    "name": getattr(asset, "name", None),
                }
            )
        self.assets = assets

    def delete_asset(self, asset: Dict[str, Optional[str]]) -> None:
        """Delete asset from universe."""
        assets = self.assets.copy() if self.assets else []
        if isinstance(asset, dict):
            asset_dict = asset
        else:
            asset_dict = {
                "code": getattr(asset, "code", None),
                "name": getattr(asset, "name", None),
            }
        assets = [
            a
            for a in assets
            if not (
                a.get("code") == asset_dict.get("code")
                and a.get("name") == asset_dict.get("name")
            )
        ]
        self.assets = assets

    def get_series(
        self,
        field: str = "PX_LAST",
        freq: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ):
        """Get series for universe assets."""
        from ix.db.query import Series as QuerySeries

        series_list = []
        for asset in self.assets or []:
            alias = asset.get("name", "")
            code = asset.get("code", "")
            s = QuerySeries(f"{code}:{field}", freq=freq)
            if alias:
                s.name = alias
            if not s.empty:
                series_list.append(s)
        if not series_list:
            return pd.DataFrame()
        multiseries = pd.concat(series_list, axis=1)
        multiseries.index = pd.to_datetime(multiseries.index)
        multiseries = multiseries.sort_index()
        multiseries.index.name = "Date"
        if start:
            multiseries = multiseries.loc[start:]
        if end:
            multiseries = multiseries.loc[:end]
        return multiseries

    def get_pct_change(self, periods: int = 1):
        """Get percentage change for universe."""
        return self.get_series(field="PX_LAST").pct_change(periods=periods)
