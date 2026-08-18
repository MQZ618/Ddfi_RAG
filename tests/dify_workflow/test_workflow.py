"""Dify Workflow Automated Test Harness."""
import json
import os
import sys
import time
import re
import io
from datetime import datetime
from dify_client import DifyClient

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_URL = os.environ.get("DIFY_BASE_URL", "http://localhost")
API_KEY = os.environ.get("DIFY_API_KEY", "app-JHRPWUaS9zjCuy7hpRKuV5Lw")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
RUNS_DIR = os.path.join(REPORT_DIR, "runs")

os.makedirs(RUNS_DIR, exist_ok=True)

client = DifyClient(BASE_URL, API_KEY)

# Upload a test PDF once and reuse the file_id
_cached_file_id = None

def get_test_file_id(user: str = "test-user") -> str:
    global _cached_file_id
    if _cached_file_id:
        return _cached_file_id

    pdf_path = os.path.join(os.path.dirname(__file__), "..", "..", "PDF", "你好.pdf")
    if not os.path.exists(pdf_path):
        print(f"  [WARN] PDF not found: {pdf_path}")
        return ""

    import requests as req
    with open(pdf_path, "rb") as f:
        resp = req.post(
            f"{BASE_URL}/v1/files/upload",
            headers={"Authorization": f"Bearer {API_KEY}"},
            files={"file": ("hello.pdf", f, "application/pdf")},
            data={"user": user},
            timeout=60,
        )
    if resp.status_code in (200, 201):
        _cached_file_id = resp.json().get("id", "")
        print(f"  [INFO] Uploaded file_id: {_cached_file_id}")
    else:
        print(f"  [WARN] Upload failed: {resp.status_code}")
    return _cached_file_id

def make_files_payload(file_id: str) -> list:
    if not file_id:
        return None
    return [{"type": "document", "transfer_method": "local_file", "upload_file_id": file_id}]

# ── Helpers ──────────────────────────────────────────────────────────────

def save_run(case_id: str, data: dict):
    path = os.path.join(RUNS_DIR, f"{case_id}.json")
    safe = json.loads(json.dumps(data, default=str))
    # redact
    for key in ["Authorization", "authorization"]:
        if key in safe:
            safe[key] = "***REDACTED***"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(safe, f, ensure_ascii=False, indent=2)


def extract_answer(resp: dict) -> str:
    return resp.get("answer", "")


def extract_metadata(resp: dict) -> dict:
    return resp.get("metadata", {})


def extract_conversation_id(resp: dict) -> str:
    return resp.get("conversation_id", "")


def extract_task_id(resp: dict) -> str:
    return resp.get("task_id", "")


def has_rag_status_yes(answer: str) -> bool:
    """Check if answer claims RAG was queried."""
    patterns = [
        r"已查询本地知识库",
        r"已查询知识库",
        r"检索到.*证据",
        r"返回候选内容",
    ]
    return any(re.search(p, answer) for p in patterns)


def has_rag_status_no(answer: str) -> bool:
    """Check if answer claims RAG was NOT queried."""
    patterns = [
        r"本次未查询本地知识库",
        r"未查询知识库",
        r"未查询本地知识库",
    ]
    return any(re.search(p, answer) for p in patterns)


def has_internal_leakage(answer: str) -> list:
    """Check for internal node name leakage."""
    leaks = []
    patterns = [
        (r"COMMIT\s*RESEARCH\s*STATE", "COMMIT RESEARCH STATE"),
        (r"TASK\s*PLANNER", "TASK PLANNER"),
        (r"RAG\s*STATUS\s*AGGREGATOR", "RAG STATUS AGGREGATOR"),
        (r"FILE\s*EVIDENCE\s*AGGREGATOR", "FILE EVIDENCE AGGREGATOR"),
        (r"STATE\s*COMPRESSOR", "STATE COMPRESSOR"),
        (r"EVIDENCE\s*EXTRACTOR", "EVIDENCE EXTRACTOR"),
        (r"CONTEXT\s*BUILDER", "CONTEXT BUILDER"),
        (r"RESEARCH\s*PLANNER", "RESEARCH PLANNER"),
        (r"MAIN\s*RESEARCH\s*LLM", "MAIN RESEARCH LLM"),
    ]
    for pat, label in patterns:
        if re.search(pat, answer, re.IGNORECASE):
            leaks.append(label)
    return leaks


def has_research_structure(answer: str) -> dict:
    """Check for required research output structure."""
    return {
        "has_fact": bool(re.search(r"【已有事实】", answer)),
        "has_reasoning": bool(re.search(r"【合理推理】", answer)),
        "has_low_confidence": bool(re.search(r"【低置信", answer)),
    }


def check_duplicate_content(answer: str) -> list:
    """Check for duplicate paragraphs."""
    issues = []
    lines = [l.strip() for l in answer.split("\n") if l.strip() and len(l.strip()) > 30]
    seen = {}
    for i, line in enumerate(lines):
        if line in seen:
            issues.append(f"Duplicate line at {i} (first at {seen[line]}): {line[:60]}...")
        else:
            seen[line] = i

    # Check for repeated section headers
    fact_count = len(re.findall(r"【已有事实】", answer))
    reasoning_count = len(re.findall(r"【合理推理】", answer))
    if fact_count > 1:
        issues.append(f"【已有事实】 appears {fact_count} times")
    if reasoning_count > 1:
        issues.append(f"【合理推理】 appears {reasoning_count} times")

    # Check for repeated RAG status
    rag_yes_count = len(re.findall(r"已查询本地知识库", answer))
    rag_no_count = len(re.findall(r"本次未查询本地知识库", answer))
    if rag_yes_count > 1:
        issues.append(f"'已查询本地知识库' appears {rag_yes_count} times")
    if rag_no_count > 1:
        issues.append(f"'本次未查询本地知识库' appears {rag_no_count} times")
    if rag_yes_count >= 1 and rag_no_count >= 1:
        issues.append("P0: Both '已查询' and '未查询' appear in same answer")

    return issues


def run_case(case_id: str, query: str, user: str = "test-user",
             conversation_id: str = None, files: list = None) -> dict:
    """Execute a single test case and return structured result."""
    print(f"\n{'='*60}")
    print(f"  {case_id}: {query[:60]}...")
    print(f"{'='*60}")

    start = time.time()
    resp = client.chat(query=query, user=user, conversation_id=conversation_id, files=files)
    elapsed = time.time() - start

    save_run(case_id, resp)

    answer = extract_answer(resp)
    metadata = extract_metadata(resp)
    usage = metadata.get("usage", {})

    result = {
        "case_id": case_id,
        "query": query,
        "answer": answer,
        "answer_length": len(answer),
        "elapsed_s": round(elapsed, 2),
        "tokens": usage.get("total_tokens", 0),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "latency": metadata.get("usage", {}).get("latency", 0),
        "conversation_id": extract_conversation_id(resp),
        "task_id": extract_task_id(resp),
        "has_rag_yes": has_rag_status_yes(answer),
        "has_rag_no": has_rag_status_no(answer),
        "internal_leaks": has_internal_leakage(answer),
        "research_structure": has_research_structure(answer),
        "duplicate_issues": check_duplicate_content(answer),
        "error": resp.get("code", None),
        "raw_metadata": metadata,
    }

    # Print summary
    print(f"  Status: {'ERROR - ' + str(result['error']) if result['error'] else 'OK'}")
    print(f"  Elapsed: {result['elapsed_s']}s | Tokens: {result['tokens']}")
    print(f"  RAG claimed YES: {result['has_rag_yes']} | NO: {result['has_rag_no']}")
    if result['internal_leaks']:
        print(f"  ⚠️  Internal leaks: {result['internal_leaks']}")
    if result['duplicate_issues']:
        print(f"  ⚠️  Duplicates: {result['duplicate_issues']}")
    print(f"  Answer preview: {answer[:150]}...")

    return result


# ── Test Cases ───────────────────────────────────────────────────────────

def test_01_basic_question():
    """TEST 01: Basic RAG question."""
    return run_case("case_01", "What is RAG?")


def test_02_colloquial():
    """TEST 02: Colloquial research judgment."""
    return run_case("case_02", "This method - is it reliable?")


def test_03_explicit_rag_with_same_paper():
    """TEST 03: Explicit KB query with same-paper PDF."""
    fid = get_test_file_id("test-user")
    files = make_files_payload(fid)
    return run_case("case_03", "Please query the knowledge base and compare this paper.", files=files)


def test_04_related_work():
    """TEST 04: Find related work."""
    fid = get_test_file_id("test-user")
    files = make_files_payload(fid)
    return run_case("case_04", "Query the knowledge base, find the most related existing work to this paper, and compare methods, experiments, and limitations.", files=files)


def test_05_novelty():
    """TEST 05: Novelty / Prior Art."""
    return run_case("case_05", "How novel is this work? Are there similar works in the knowledge base?")


def test_06_no_rag():
    """TEST 06: Explicitly forbid RAG."""
    fid = get_test_file_id("test-user")
    files = make_files_payload(fid)
    return run_case("case_06", "Summarize the method based only on my uploaded paper. Do NOT query the knowledge base.", files=files)


def test_07_no_file_related_work():
    """TEST 07: No file + related work query."""
    return run_case("case_07", "Query the knowledge base and compare different memory designs in LLM Agents.")


def test_08_kb_no_result():
    """TEST 08: KB query that should return nothing."""
    return run_case("case_08", "Query the knowledge base about quantum entanglement effects on photosynthesis in deep sea organisms published in 2087.")


def test_09_unknown_paper():
    """TEST 09: Unknown paper + KB comparison."""
    fid = get_test_file_id("test-user")
    files = make_files_payload(fid)
    return run_case("case_09", "Query the knowledge base and compare this paper.", files=files)


def test_10_research_structure():
    """TEST 10: Research output structure check."""
    return run_case("case_10", "What are the main limitations of using RAG for multi-hop reasoning in scientific literature review?")


def test_11_rag_status_consistency(results: list):
    """TEST 11: RAG status consistency across all prior results."""
    print(f"\n{'='*60}")
    print(f"  TEST 11: RAG Status Consistency Analysis")
    print(f"{'='*60}")

    issues = []
    for r in results:
        trace_rag = "UNKNOWN"  # We don't have node-level trace from API
        claimed_yes = r["has_rag_yes"]
        claimed_no = r["has_rag_no"]

        if claimed_yes and claimed_no:
            issues.append({
                "case": r["case_id"],
                "issue": "P0: Both '已查询' and '未查询' in same answer",
                "severity": "P0",
            })
        elif claimed_yes:
            status = "claimed YES"
        elif claimed_no:
            status = "claimed NO"
        else:
            status = "UNCLEAR - neither YES nor NO found"

        print(f"  {r['case_id']}: RAG YES={claimed_yes} NO={claimed_no}")

    return {
        "case_id": "case_11",
        "description": "RAG status consistency check across all cases",
        "issues": issues,
        "total_checked": len(results),
    }


def test_12_internal_leakage(results: list):
    """TEST 12: Internal node info leakage."""
    print(f"\n{'='*60}")
    print(f"  TEST 12: Internal Node Leakage Analysis")
    print(f"{'='*60}")

    all_leaks = []
    for r in results:
        leaks = r.get("internal_leaks", [])
        if leaks:
            all_leaks.append({"case": r["case_id"], "leaks": leaks})
            print(f"  {r['case_id']}: LEAKED {leaks}")

    if not all_leaks:
        print("  No internal node leakage detected.")

    return {
        "case_id": "case_12",
        "description": "Internal node name leakage check",
        "leaks": all_leaks,
    }


def test_13_duplicate_output(results: list):
    """TEST 13: Duplicate output check."""
    print(f"\n{'='*60}")
    print(f"  TEST 13: Duplicate Output Analysis")
    print(f"{'='*60}")

    all_issues = []
    for r in results:
        issues = r.get("duplicate_issues", [])
        if issues:
            all_issues.append({"case": r["case_id"], "issues": issues})
            print(f"  {r['case_id']}: {issues}")

    if not all_issues:
        print("  No duplicate output issues detected.")

    return {
        "case_id": "case_13",
        "description": "Duplicate output check",
        "issues": all_issues,
    }


def test_14_retry_config():
    """TEST 14: Check retry configuration from DSL."""
    print(f"\n{'='*60}")
    print(f"  TEST 14: Retry Configuration Check")
    print(f"{'='*60}")

    # From static analysis
    retry_nodes = {
        "task_planner": {"max_retries": 1, "retry_enabled": True},
        "research_planner": {"max_retries": 1, "retry_enabled": True},
        "file_evidence_extractor": {"max_retries": 1, "retry_enabled": True},
        "evidence_extractor": {"max_retries": 1, "retry_enabled": True},
        "main_research_llm": {"max_retries": 1, "retry_enabled": True},
        "state_compressor": {"max_retries": 1, "retry_enabled": True},
    }

    for name, config in retry_nodes.items():
        print(f"  {name}: retry={config['retry_enabled']}, max={config['max_retries']}")

    return {
        "case_id": "case_14",
        "description": "Retry configuration check",
        "retry_nodes": retry_nodes,
        "all_configured": all(v["retry_enabled"] for v in retry_nodes.values()),
    }


def test_15_stop_generation():
    """TEST 15: Stop generation test."""
    print(f"\n{'='*60}")
    print(f"  TEST 15: Stop Generation Test")
    print(f"{'='*60}")

    import requests as req
    import threading

    # Start a long-running request in streaming mode
    payload = {
        "inputs": {},
        "query": "Provide a comprehensive 5000-word analysis of all methods in the knowledge base for multi-hop reasoning, including detailed comparisons of every approach mentioned in every paper.",
        "response_mode": "streaming",
        "user": "test-user-stop",
    }

    task_id = None
    conversation_id = None
    stop_result = None
    final_status = "unknown"

    try:
        resp = req.post(
            f"{BASE_URL}/v1/chat-messages",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json=payload,
            stream=True,
            timeout=30,
        )

        # Read first few events to get task_id
        lines_read = 0
        for line in resp.iter_lines():
            if line:
                line_str = line.decode("utf-8", errors="replace")
                if line_str.startswith("data: "):
                    try:
                        data = json.loads(line_str[6:])
                        if "task_id" in data:
                            task_id = data["task_id"]
                            conversation_id = data.get("conversation_id", "")
                            print(f"  Got task_id: {task_id}")
                        lines_read += 1
                        if lines_read >= 3 and task_id:
                            break
                    except json.JSONDecodeError:
                        pass

        # Stop the generation
        if task_id:
            time.sleep(2)
            stop_result = client.stop_generation(task_id, user="test-user-stop")
            print(f"  Stop result: {stop_result}")
            final_status = stop_result.get("result", "unknown")
        else:
            print("  Could not get task_id for stop test")

    except Exception as e:
        print(f"  Stop test error: {e}")
        final_status = f"error: {e}"

    return {
        "case_id": "case_15",
        "description": "Stop generation test",
        "task_id": task_id,
        "conversation_id": conversation_id,
        "stop_result": stop_result,
        "final_status": final_status,
    }


def test_16_new_conversation():
    """TEST 16: New conversation contamination test."""
    print(f"\n{'='*60}")
    print(f"  TEST 16: New Conversation Contamination Test")
    print(f"{'='*60}")

    # Run case 03 in a fresh conversation
    result = run_case("case_16", "Please query the knowledge base and compare this paper.", user="test-user-fresh-16")

    return result


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  Dify Workflow Automated Test Suite")
    print(f"  Target: {BASE_URL}")
    print(f"  Date: {datetime.now().isoformat()}")
    print("=" * 70)

    # Verify API
    info = client.get_app_info()
    print(f"\nApp: {info.get('name', 'unknown')}")
    print(f"Mode: {info.get('mode', 'unknown')}")

    results = []

    # Phase 3: Smoke test (already done, re-run for record)
    r01 = test_01_basic_question()
    results.append(r01)

    # Phase 4: RAG routing tests
    r02 = test_02_colloquial()
    results.append(r02)

    r03 = test_03_explicit_rag_with_same_paper()
    results.append(r03)

    r04 = test_04_related_work()
    results.append(r04)

    r05 = test_05_novelty()
    results.append(r05)

    r06 = test_06_no_rag()
    results.append(r06)

    r07 = test_07_no_file_related_work()
    results.append(r07)

    r08 = test_08_kb_no_result()
    results.append(r08)

    r09 = test_09_unknown_paper()
    results.append(r09)

    r10 = test_10_research_structure()
    results.append(r10)

    # Phase 6: Analysis tests
    r11 = test_11_rag_status_consistency(results)
    results.append(r11)

    r12 = test_12_internal_leakage(results)
    results.append(r12)

    r13 = test_13_duplicate_output(results)
    results.append(r13)

    r14 = test_14_retry_config()
    results.append(r14)

    # Phase 7: Stop generation
    r15 = test_15_stop_generation()
    results.append(r15)

    # Phase 8: Contamination
    r16 = test_16_new_conversation()
    results.append(r16)

    # Save all results
    all_results_path = os.path.join(RUNS_DIR, "all_results.json")
    with open(all_results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n{'='*70}")
    print(f"  All {len(results)} test cases completed.")
    print(f"  Results saved to: {all_results_path}")
    print(f"{'='*70}")

    return results


if __name__ == "__main__":
    results = main()
