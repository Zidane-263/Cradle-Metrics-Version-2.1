import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from clinical_history import ClinicalHistoryManager

def test_get_record():
    mgr = ClinicalHistoryManager()
    
    # Try to find a real record ID from index.json
    index_path = Path("c:/Projects/Zidane/clinical_history/index.json")
    if not index_path.exists():
        print("Index not found")
        return

    with open(index_path, 'r') as f:
        index = json.load(f)
    
    # Get first record ID
    patients = index.get('patients', {})
    if not patients:
        print("No patients in index")
        return
        
    first_patient = list(patients.keys())[0]
    records = patients[first_patient]
    if not records:
        print(f"No records for patient {first_patient}")
        return
        
    record_id = records[0]['record_id']
    print(f"Testing with record_id: {record_id} (Patient: {first_patient})")
    
    record = mgr.get_record(record_id)
    if record:
        print("✅ SUCCESS: Record found and loaded")
        # print(json.dumps(record, indent=2)[:200] + "...")
    else:
        print("❌ FAILED: Record not found")

if __name__ == "__main__":
    test_get_record()
