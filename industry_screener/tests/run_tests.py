
import sys
import os

# Add industry_screener to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.test_calculator import TestCalculator

def run():
    print("Initializing tests...")
    t = TestCalculator()
    t.setup_method()
    
    methods = [m for m in dir(t) if m.startswith('test_')]
    passed = 0
    failed = 0
    
    print(f"Running {len(methods)} tests...")
    
    for m in methods:
        try:
            getattr(t, m)()
            print(f"✅ {m}")
            passed += 1
        except Exception as e:
            print(f"❌ {m}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            
    print(f"\nResult: {passed} passed, {failed} failed.")
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run()
