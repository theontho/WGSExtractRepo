import unittest
from e2e_base import TestE2EBase

class TestE2EFocused(TestE2EBase):
    """
    Focused E2E tests targeting specific regions (usually chrM).
    Fast and suitable for routine verification.
    """
    REGION = "chrM"
    MODE = "CHRM"

if __name__ == '__main__':
    unittest.main()
