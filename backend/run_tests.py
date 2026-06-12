import unittest
import sys
import os

def run_all_tests():
    print("Running app-wide backend test suite...")
    print("-" * 50)
    
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), 'tests')
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("-" * 50)
    if result.wasSuccessful():
        print("SUCCESS: ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("FAILURE: SOME TESTS FAILED.")
        sys.exit(1)

if __name__ == '__main__':
    run_all_tests()
