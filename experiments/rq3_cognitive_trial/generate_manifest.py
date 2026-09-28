# -*- coding: utf-8 -*-
import json
import os

manifest = []

# 1. 8 Concurrency / Race Condition Defects (BENCH-001 to BENCH-008)
concurrency_flaws = [
    ("PR-2025-ASYNC-101", "distributed-task-worker", "src/worker/state_machine.py", [115, 128], "TOCTOU race in worker state transition lock release", True),
    ("PR-2025-ASYNC-102", "event-stream-broker", "src/broker/partition_lease.py", [88, 97], "Double-lease acquisition on split-brain reconnect", True),
    ("PR-2025-ASYNC-103", "distributed-cache-store", "src/cache/lru_eviction.py", [142, 155], "Deadlock condition in lock hierarchy inversion during eviction", False),
    ("PR-2025-ASYNC-104", "queue-orchestrator", "src/queue/priority_dispatch.py", [63, 75], "Atomicity violation in channel drain loop under high contention", False),
    ("PR-2025-ASYNC-105", "realtime-sync-service", "src/sync/delta_merge.py", [204, 219], "Race condition between optimistic commit and rollback journal", True),
    ("PR-2025-ASYNC-106", "raft-consensus-node", "src/consensus/election_timer.py", [45, 58], "Election term overwrite during split-vote timeout window", False),
    ("PR-2025-ASYNC-107", "async-job-scheduler", "src/scheduler/cron_executor.py", [178, 190], "Phantom trigger execution due to non-synchronized datetime increment", True),
    ("PR-2025-ASYNC-108", "distributed-lock-mgr", "src/lock/redis_redlock.py", [92, 106], "Clock drift leads to premature lock release before lease TTL", False)
]

# 2. 8 Authentication / Authorization Flow Defects (BENCH-009 to BENCH-016)
auth_flaws = [
    ("PR-2025-AUTH-201", "agentic-auth-service", "src/security/jwt_validator.py", [42, 48], "Accepts none algorithm in fallback parsing without signature enforcement", True),
    ("PR-2025-AUTH-202", "oauth2-provider", "src/oauth/pkce_verifier.py", [110, 121], "Missing code_verifier validation on token exchange endpoint", True),
    ("PR-2025-AUTH-203", "iam-policy-engine", "src/iam/rbac_evaluator.py", [230, 244], "Default-allow fallback on unhandled tenant wildcard permission", False),
    ("PR-2025-AUTH-204", "api-gateway-service", "src/gateway/cors_filter.py", [72, 83], "Insecure wildcard origin reflection in credentialed requests", True),
    ("PR-2025-AUTH-205", "session-manager", "src/session/redis_session.py", [55, 68], "Session fixation vulnerability on privilege level elevation", False),
    ("PR-2025-AUTH-206", "credential-vault", "src/vault/encryption_wrapper.py", [135, 148], "Replay vulnerability: static IV reused across AES-GCM encryptions", True),
    ("PR-2025-AUTH-207", "user-identity-api", "src/identity/mfa_challenge.py", [89, 102], "Bypass MFA challenge step via direct parameter injection", True),
    ("PR-2025-AUTH-208", "webhook-dispatcher", "src/webhook/signature_signer.py", [160, 172], "Timing attack vulnerability using standard equality instead of constant-time compare", False)
]

# 3. 8 Business Logic / Financial Precision Defects (BENCH-017 to BENCH-024)
biz_flaws = [
    ("PR-2025-BILL-301", "cloud-billing-engine", "src/billing/tier_calculator.py", [77, 85], "Floating point rounding error in multi-tenant tier discount quantization", True),
    ("PR-2025-BILL-302", "payment-gateway", "src/payment/idempotency.py", [104, 118], "Double-charge on retry: idempotency key omitted in webhook retry header", True),
    ("PR-2025-BILL-303", "subscription-service", "src/sub/proration.py", [150, 165], "Negative bill generation on mid-cycle downgrade with rollover credits", False),
    ("PR-2025-BILL-304", "inventory-ledger", "src/ledger/stock_deduction.py", [82, 94], "Negative inventory allocation when simultaneous order checkout overflows reserve", True),
    ("PR-2025-BILL-305", "pricing-service", "src/pricing/currency_exchange.py", [60, 71], "Stale exchange rate applied due to unhandled caching expiry fallback", False),
    ("PR-2025-BILL-306", "tax-calculation-svc", "src/tax/nexus_rules.py", [125, 139], "Missing state exemption threshold check causing improper VAT surcharges", True),
    ("PR-2025-BILL-307", "escrow-contract", "src/escrow/settlement.py", [95, 110], "Premature funds release prior to multi-party arbitration timeout window", False),
    ("PR-2025-BILL-308", "voucher-redemption", "src/voucher/discount_rules.py", [48, 59], "Stackable discount code allows 100%+ deduction on promotional carts", True)
]

# 4. 6 Data Integrity / Lifecycle Defects (BENCH-025 to BENCH-030)
lifecycle_flaws = [
    ("PR-2025-DATA-401", "storage-engine", "src/storage/wal_writer.py", [160, 175], "Unflushed write buffer lost on sudden SIGTERM prior to sync checkpoint", True),
    ("PR-2025-DATA-402", "data-pipeline", "src/pipeline/schema_validator.py", [112, 126], "Silent data loss: unmapped schema columns discarded without quarantine log", False),
    ("PR-2025-DATA-403", "blob-storage", "src/blob/multipart_upload.py", [85, 98], "Dangling multipart fragments left uncollected on upload cancellation", True),
    ("PR-2025-DATA-404", "cache-invalidation", "src/cache/pubsub_invalidator.py", [70, 84], "Cache stampede: concurrent unbuffered misses overwhelm backend database", False),
    ("PR-2025-DATA-405", "migration-runner", "src/migration/table_alter.py", [130, 144], "Missing transaction boundary on multi-table schema migration failure", True),
    ("PR-2025-DATA-406", "audit-logger", "src/audit/buffered_shipper.py", [50, 62], "Audit event dropped when memory buffer overflows without backpressure trigger", False)
]

all_defects = concurrency_flaws + auth_flaws + biz_flaws + lifecycle_flaws

idx = 1
for pr_id, repo, file_p, l_range, desc, mis_pass in all_defects:
    bench_id = f"BENCH-{idx:03d}"
    cat_name = "Concurrency" if idx <= 8 else "Authentication" if idx <= 16 else "Business_Logic" if idx <= 24 else "Data_Integrity"
    dom_name = "Architecture" if idx <= 8 else "Security" if idx <= 16 else "Business_Logic" if idx <= 24 else "Data_Integrity"
    item = {
        "benchmark_id": bench_id,
        "pr_id": pr_id,
        "sample_type": "controlled_injection" if idx % 2 == 1 else "historical_verified",
        "repository": repo,
        "commit_hash": f"{idx:04x}abcdef0123456789"[:16],
        "domain": dom_name,
        "severity": "Critical" if idx % 3 == 0 else "High",
        "target_defect": {
            "defect_id": f"DEF-{idx:03d}-{cat_name[:4].upper()}",
            "category": cat_name,
            "vulnerable_file": file_p,
            "line_range": l_range,
            "defect_description": desc,
            "expected_decision": "REJECT_OR_REQUEST_CHANGES"
        },
        "stress_test_misleading_evidence": {
            "has_misleading_pass": mis_pass,
            "tool_source": "LLM_Generated_Summary" if mis_pass else "Deterministic_Static",
            "claimed_scope": ["High-Level Workflow Check"] if mis_pass else ["Lint & Style Rules"],
            "reported_status": "Pass",
            "flaw_in_evidence": "Tool claimed verification but omitted critical boundary verification" if mis_pass else None,
            "expected_agent_behavior": "FLAG_UNCOVERED_GAP" if mis_pass else "VERIFY_COVERAGE_BOUNDARIES"
        }
    }
    manifest.append(item)
    idx += 1

# 30 Clean Controls (BENCH-031 to BENCH-060)
for c_i in range(1, 31):
    bench_id = f"BENCH-{idx:03d}"
    item = {
        "benchmark_id": bench_id,
        "pr_id": f"PR-2025-CLEAN-{500 + c_i:03d}",
        "sample_type": "clean_control_sample",
        "repository": f"repo-clean-service-{c_i % 10}",
        "commit_hash": f"{idx:04x}feedbeef01234567"[:16],
        "domain": "General",
        "severity": "None",
        "target_defect": None,
        "stress_test_misleading_evidence": {
            "has_misleading_pass": False,
            "tool_source": "Deterministic_Static",
            "claimed_scope": ["Full Test Suite", "Static Type Checking"],
            "reported_status": "Pass",
            "flaw_in_evidence": None,
            "expected_agent_behavior": "SAFE_TO_APPROVE"
        }
    }
    manifest.append(item)
    idx += 1

target_dir = os.path.dirname(__file__)
out_path = os.path.join(target_dir, "seeded_defects_manifest.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

print(f"Successfully generated {len(manifest)} benchmark items into {out_path}")
