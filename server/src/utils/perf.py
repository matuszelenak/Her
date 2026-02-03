import time
from typing import Optional

import logfire


class ElapsedTime:
    """Context manager to measure the elapsed time of a code block."""
    def __init__(self, code_block_name: Optional[str]):
        """Initialize the context manager."""
        self.start_time = None
        self.code_block_name = code_block_name
        self.duration = None

    def __enter__(self):
        """Enter the context manager."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        end_time = time.time()

        self.duration = end_time - self.start_time
        logfire.debug(f'{self.code_block_name or "Execution"} took {self.duration:.2f}s')
