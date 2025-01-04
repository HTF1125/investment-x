import pandas as pd
from xgboost import XGBRegressor
from ix import get_ts, get_timeseries

class SPX_EPS_Forcastor_6M:

    FEATURES = [
        {"code": "^DXY", "field": "PX_DIFF_12M_ME", "name": "DXY_12M_CHG"},
        {"code": "^LF98OAS", "field": "PX_DIFF_12M_ME", "name": "HTY_SPRD_12M_CHG"},
        {"code": "^CONCCONF", "field": "PX_DIFF_12M_ME", "name": "ConsConf12MChg"},
        {"code": "^PCI", "field": "PX_YOY", "name": "PPI_YOY"},
        {"code": "^NAPMNEWO", "field": "PX_LAST", "name": "ISM_NEW_ORDERS_US"},
        {"code": "^LEI_YOY", "field": "PX_LAST", "name": "Leading"},
        {"code": "^COI_YOY", "field": "PX_LAST", "name": "Coincident"},
        {"code": "^WGTROVRA", "field": "PX_LAST", "name": "WageGrowth"},
    ]
    TARGET = {
        "code": "^SPX",
        "field": "TRAIL_12M_EPS_YOY_ME",
        "name": "SPX_TTM_EPS_YOY_ME",
    }

    def __init__(self) -> None:
        self.features = get_ts(*self.FEATURES).resample("ME").last()
        self.target = get_timeseries(**self.TARGET)
        self.model = XGBRegressor(
            n_estimators=500,
            learning_rate=0.2,
            max_depth=20,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric="rmse",
        )
        self.prediction = pd.Series()

    def fit(self) -> "SPX_EPS_Forcastor_6M":
        features = self.features.copy()
        for col in features.columns:
            for lag in [1, 2, 3]:
                features[f"{col}_{lag}"] = features[col].shift(lag)
                features[f"{col}_m_{lag}"] = features[col].rolling(6).mean().shift(lag)
                features[f"{col}_s_{lag}"] = features[col].rolling(6).std().shift(lag)
        features.index += pd.offsets.MonthEnd(6)

        idx = features.index.intersection(self.target.index)
        X = features.loc[idx]
        y = self.target.loc[idx]
        self.model.fit(X, y)
        self.prediction = pd.Series(self.model.predict(features), index=features.index, name="EPS_YOY_ME").loc[self.target.index[-1]:]
        return self

