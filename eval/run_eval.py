import json
import requests
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / ".env")  # Up to project root

API = "http://localhost:8000"
GOLDEN_PATH = Path(__file__).parent / "golden.json"

def get_token(username: str, password: str = "pass") -> str:
    """Login and get JWT token for a user."""
    r = requests.post(f"{API}/auth/login", json={"username": username, "password": password})
    if r.status_code != 200:
        raise RuntimeError(f"Login failed for {username}: {r.text}")
    return r.json()["access_token"]

def run_single_test(test: dict) -> dict:
    """Run one golden test case."""
    headers = {"Authorization": f"Bearer {get_token(test['username'])}"}
    
    r = requests.post(f"{API}/chat/query", json={"question": test["question"]}, headers=headers)
    
    result = {
        "test_id": test["test_id"],
        "status_code": r.status_code,
        "answer": r.json()["answer"][:100] + "..." if r.status_code == 200 else None,
        "retrieved_doc_ids": [c["doc_id"] for c in r.json().get("citations", [])],
        "passed": False
    }
    
    if r.status_code != 200:
        print(f"{test['test_id']}: HTTP {r.status_code}")
        return result
    
    # Check security: right documents retrieved?
    expected_docs = test["expected_doc_ids"]
    actual_docs = result["retrieved_doc_ids"]
    security_pass = set(expected_docs) == set([d for d in actual_docs if d != -1])
    
    # Check quality: keywords in answer?
    answer = r.json()["answer"].lower()
    keywords_pass = all(kw.lower() in answer for kw in test["expected_keywords"])
    
    result["passed"] = security_pass and keywords_pass
    result["security_pass"] = security_pass
    result["keywords_pass"] = keywords_pass
    
    status = "PASS" if result["passed"] else "FAIL"
    print(f"{status} {test['test_id']}: docs={actual_docs}, keywords={test['expected_keywords']}")
    
    return result

def main():
    """Run all golden tests. Fail CI if any test fails."""
    if not GOLDEN_PATH.exists():
        print("No golden.json - create test data first!")
        return
    
    with open(GOLDEN_PATH) as f:
        tests = json.load(f)
    
    print(f"Running {len(tests)} golden tests...\n")
    
    results = []
    passed = 0
    
    # PRECONDITION: Upload test document first
    print("📤 Step 1: Upload test document...")
    test_token = get_token("t1_admin")
    test_upload = requests.post(
        f"{API}/documents/upload_url",
        params={
            "title": "Python Test Doc",
            "url": "https://www.python.org/about/",
            "roles_allowed": "member",
            "sensitive": "true"
        },
        headers={"Authorization": f"Bearer {test_token}"}
    )
    if test_upload.status_code != 200:
        print(f"Failed to upload test doc: {test_upload.text}")
        return
    
    print("✅ Test document uploaded\n")
    
    # Run tests
    for test in tests:
        result = run_single_test(test)
        results.append(result)
        if result["passed"]:
            passed += 1
    
    # Summary
    print("\n" + "="*60)
    print(f"RESULTS: {passed}/{len(tests)} PASSED")
    
    if passed == len(tests):
        print("ALL TESTS PASSED! ✅")
        exit(0)
    else:
        print("QUALITY GATE FAILED! Fix RAG/security issues.")
        print("\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['test_id']}: {r}")
        exit(1)

if __name__ == "__main__":
    main()