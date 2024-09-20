import os
import pickle
import numpy as np
import pandas as pd

from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import BaggingClassifier


class BaggingMlpClassifier:

    def __init__(
        self,
        lags: int = 5,
        lookback_window: int = 50,
        hidden_layer_sizes: tuple = (256,),
        random_state: int = 100,
        max_iter: int = 1000,
        early_stopping: bool = True,
        validation_fraction: float = 0.15,
        shuffle: bool = False,
        n_estimators: int = 100,
        max_features: float = 0.50,
        max_samples: float = 0.50,
        bootstrap: bool = False,
        bootstrap_features: bool = False,
        n_jobs: int = -1,
    ):

        self.lags = lags
        self.lookback_window = lookback_window

        base_estimator = MLPClassifier(
            hidden_layer_sizes=hidden_layer_sizes,
            random_state=random_state,
            max_iter=max_iter,
            early_stopping=early_stopping,
            validation_fraction=validation_fraction,
            shuffle=shuffle,
        )
        # Bagging Classifier with the base estimator.
        self.model = BaggingClassifier(
            base_estimator=base_estimator,
            n_estimators=n_estimators,
            max_samples=max_samples,
            max_features=max_features,
            bootstrap=bootstrap,
            bootstrap_features=bootstrap_features,
            n_jobs=n_jobs,
            random_state=random_state,
        )


    