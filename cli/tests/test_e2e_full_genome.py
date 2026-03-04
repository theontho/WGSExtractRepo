import unittest
from e2e_base import TestE2EBase

class TestE2EFull(TestE2EBase):
    """
    Full genome E2E tests. Slow and rigorous.
    Removes region filters to process all available data.
    """
    REGION = None
    MODE = "FULL GENOME"

if __name__ == '__main__':
    unittest.main()
