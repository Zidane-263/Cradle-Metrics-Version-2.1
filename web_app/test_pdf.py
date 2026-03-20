
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from report_generator import ClinicalReportGenerator

def test():
    try:
        gen = ClinicalReportGenerator(output_dir='test_reports')
        print("Generator initialized")
        path = gen.generate_report({}, {}, [])
        print(f"Report generated at: {path}")
        if os.path.exists(path):
            print("Success!")
        else:
            print("Failed: path does not exist")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
