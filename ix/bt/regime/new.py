from ix import db
from ix.misc import get_logger


logger = get_logger(__name__)


class Regime:

    def load(self) -> dict:
        try:
            ins = {"code": self.__str__}
            regime = db.Regime.find_one(ins).run()
            if regime is not None:
                return regime.data
            return {}
        except Exception as e:

            return {}

    def save(self) -> bool:

        try:
            ins = {"code": self.__str__}
            regime = db.Regime.find_one(ins).run()
            if regime is None:
                db.Regime(code=self.__str__(), data=self.data).create()
            else:
                regime.set({"data": self.data})
        except Exception as e:
            msg = "Failed to dump regime to database"
            msg += f"(code = {self.__str__()})"
            msg += "\nMessage : {e}"
            logger.error(msg)


    def __init__(self) -> None:
        self.data = self.load()
        