class BotError(Exception):
    pass


class UserNotFoundError(BotError):
    """Raised when a user is not found in the database."""

    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(f"User with ID {user_id} was not found.")
