import pandas as pd
from ix import db
from ix import misc

logger = misc.get_logger(__name__)


class Regime:

    @property
    def code(self) -> str:
        return self.__class__.__name__

    def __init__(self) -> None:
        self.db = db.Regime.find_one(db.Regime.code == self.code).run() or db.Regime(
            code=self.code
        )

    def fit(self) -> pd.Series:
        raise NotImplementedError("Subclasses must implement `fit` method.")

    def refresh(self) -> "Regime":
        """
        Refresh the data by calling fit method, validating the result, and updating the record.

        Raises:
            TypeError: If the data doesn't meet the expected format.
            Exception: For any other unexpected errors during the process.
        """
        try:
            logger.info("Starting data refresh")
            states = self.fit()
            self._validate_states(states)
            self.db.data = states.to_dict()
            db.Regime.save(self.db)
            logger.info(
                f"Data refresh completed successfully. Updated record with {len(states)} entries"
            )
        except TypeError as e:
            logger.error(f"Data validation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during refresh: {str(e)}")
            raise
        return self

    @staticmethod
    def _validate_states(states: pd.Series) -> None:
        if not isinstance(states, pd.Series):
            raise TypeError("States is not a pandas Series")
        if not isinstance(states.index, pd.DatetimeIndex):
            raise TypeError("Index is not a DatetimeIndex")
        if (
            states.dtype != "object"
            or not states.apply(lambda x: isinstance(x, str)).all()
        ):
            raise TypeError("Not all values are strings")
        if states.empty:
            raise TypeError("States Series is empty")
        if not states.index.is_monotonic_increasing:
            raise TypeError("Index is not sorted in ascending order")

    def get_states(self) -> pd.Series:
        if self.db.data is None:
            self.refresh()
        states = pd.Series(self.db.data)
        states.index = pd.to_datetime(states.index)
        states = states.sort_index()
        states.name = "states"
        states.index.name = "date"
        return states

    def get_state(self, date: str | pd.Timestamp) -> str:
        return self.get_states().loc[:date].iloc[-1]
