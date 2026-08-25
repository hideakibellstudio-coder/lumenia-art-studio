import os
import sys
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

import tests.test_phase1_layers as t1
import tests.test_phase2_groups as t2

suite = unittest.TestSuite()
suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(t1.TestPhase1Layers))
suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(t2.TestPhase2Groups))

runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)
print(f"Ran {result.testsRun} tests. Errors: {len(result.errors)}, Failures: {len(result.failures)}")
if not result.wasSuccessful():
    sys.exit(1)
