"""
Custom exceptions for task-related operations.

These exceptions are caught by FastAPI exception handlers
and converted to appropriate HTTP responses.
"""


class TaskNotFoundError(Exception):
    """
    Raised when a requested task does not exist in the database.

    Attributes:
        task_id: The ID of the task that was not found.
    """

    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        super().__init__(f"Task with id={task_id} not found")