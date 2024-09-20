from bunnet import Document


class User(Document):

    username: str
    password: str

    class Settings:
        collection = "user"

        # indexes = [
        #     {"fields" : ["username"],
        #      "unique" : True,}
        # ]