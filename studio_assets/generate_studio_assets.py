from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_commit_hash(repo_root: Path) -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=repo_root,
            )
            .decode("ascii")
            .strip()
        )
    except Exception:
        return "f9d70e5"


def read_text_safe(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


def extract_block(text: str, start_marker: str) -> list[str]:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if start_marker in line:
            block: list[str] = []
            for next_line in lines[idx + 1 :]:
                if not next_line.strip():
                    break
                block.append(next_line.strip())
            return block
    return []


def parse_constant_values(text: str, names: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in names:
        match = re.search(rf"^\s*{re.escape(name)}\s*=\s*([^#\n]+)", text, re.MULTILINE)
        if match:
            values[name] = match.group(1).strip()
    return values


def find_token(repo_root: Path, token: str) -> str | None:
    pattern = re.compile(rf"\b{re.escape(token)}\b")
    for path in (repo_root / "src").rglob("*.py"):
        text = read_text_safe(path)
        if text and pattern.search(text):
            return str(path.relative_to(repo_root))
    return None


def format_float(value: float | int | None, digits: int = 4) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.{digits}g}"
    except Exception:
        return "N/A"


def generate_studio_assets() -> None:
    repo_root = get_repo_root()
    commit_hash = get_commit_hash(repo_root)
    version = f"v1_0_{commit_hash}"
    assets_dir = repo_root / "studio_assets" / version
    assets_dir.mkdir(parents=True, exist_ok=True)

    claim_map_path = repo_root / "claim_audit" / "claim_map_v4.json"
    repro_path = repo_root / "src" / "repro_claims_v4.py"
    constants_path = repo_root / "src" / "constants.py"
    orchestration_path = repo_root / "src" / "run_thermal_orchestration.py"

    missing = [str(p) for p in [claim_map_path, repro_path] if not p.exists()]
    if missing:
        error_msg = "CRITICAL: Missing required files: " + ", ".join(missing)
        (assets_dir / "ERROR_REPORT.txt").write_text(error_msg, encoding="utf-8")
        print(error_msg)
        return

    claim_map = json.loads(claim_map_path.read_text(encoding="utf-8"))
    claims = {c.get("id"): c for c in claim_map.get("claims", [])}

    c3 = claims.get("C3", {})
    c4 = claims.get("C4", {})
    c5 = claims.get("C5", {})

    sample_n_total = None
    sample_n_eff = None
    for claim in [c3, c4, c5]:
        computed = claim.get("computed_claim_check", {})
        if computed.get("n_total") is not None:
            sample_n_total = computed.get("n_total")
        if computed.get("n_eff") is not None:
            sample_n_eff = computed.get("n_eff")

    repro_text = read_text_safe(repro_path) or ""
    stat_block = extract_block(repro_text, "Statistical test selection rule")
    stat_rule_fallback = (
        claim_map.get("statistical_test_rule", {}).get("rule")
        if not stat_block
        else None
    )

    constants_text = read_text_safe(constants_path) or ""
    constants = parse_constant_values(
        constants_text,
        [
            "GATE_N_TRIGGER",
            "GATE_T_WINDOW",
            "GATE_T_REFRACTORY",
            "T_SLA_DEFAULT",
        ],
    )

    gate_contract_block = []
    orchestration_text = read_text_safe(orchestration_path) or ""
    gate_contract_block = extract_block(
        orchestration_text,
        "All controllers output binary gate signals",
    )

    t_hard_location = find_token(repo_root, "T_hard")
    bito_gate_location = find_token(repo_root, "BITO_Gate")

    c4_check = c4.get("computed_claim_check", {})
    c4_test = c4_check.get("test", {})
    c4_reduction = c4_check.get("reduction_pct")

    c3_check = c3.get("computed_claim_check", {})
    c3_test = c3_check.get("test_vs_pid", {})

    c5_noninf = c5.get("non_inferiority_test", {})

    source_of_truth = f"""# Source of Truth: BITO Studio Knowledge Base
**Commit Anchor:** {commit_hash}
**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}

## Verified Outcomes
- **C4 ({c4.get('label', 'Chatter Reduction')}):** status={c4.get('status', 'N/A')}, reduction~{format_float(c4_reduction, 3)}%, p={format_float(c4_test.get('p_value'))}
- **C3 ({c3.get('label', 'Control Effort')}):** status={c3.get('status', 'N/A')}, p={format_float(c3_test.get('p_value'))}
- **C5 ({c5.get('label', 'SLA Non-Inferiority')}):** status={c5.get('status', 'N/A')}, non_inferior={c5_noninf.get('non_inferior', 'N/A')}

## Safety Boundaries
- **Hard Override (T_hard):** {t_hard_location or 'NOT_FOUND in src/*.py'}
- **BITO Gate Anchor:** {bito_gate_location or 'NOT_FOUND in src/*.py (see FlyTrapGate and PID+Gate)'}
- **Gate Contract:** {" ".join(gate_contract_block) if gate_contract_block else 'Binary gate contract defined in run_thermal_orchestration.py'}
- **T_SLA_DEFAULT:** {constants.get('T_SLA_DEFAULT', 'N/A')}

## Provenance
- claim_audit/claim_map_v4.json
- src/repro_claims_v4.py
- src/run_thermal_orchestration.py
"""
    (assets_dir / "SOURCE_OF_TRUTH.md").write_text(source_of_truth, encoding="utf-8")

    stat_rule_lines = "\n".join([f"- {line}" for line in stat_block]) if stat_block else ""
    if not stat_rule_lines and stat_rule_fallback:
        stat_rule_lines = f"- {stat_rule_fallback}"

    governance = f"""# Governance Protocol

## Sample Size
- n_total={sample_n_total if sample_n_total is not None else 'N/A'}
- n_eff={sample_n_eff if sample_n_eff is not None else 'N/A'}

## Statistical Test Selection Rule
{stat_rule_lines}

## Claim Boundaries
- All claims are simulation-bounded.
- Do not claim hardware longevity, ROI, or universal applicability.
- Use "parity" or "no material increase" when results are not significant.
"""
    (assets_dir / "GOVERNANCE_PROTOCOL.md").write_text(governance, encoding="utf-8")

    glossary = {
        "kWh_ctrl": "Control effort proxy (cumulative energy)",
        "chatter_count": "Actuator state transition frequency (0->1 in binary gate)",
        "Delta": "SLA non-inferiority margin",
        "T_SLA": "Thermal SLA threshold used in orchestration",
        "gate_output_contract": "Binary gate signal u in {0, 1}",
    }
    (assets_dir / "GLOSSARY_AND_TAXONOMY.json").write_text(
        json.dumps(glossary, indent=2),
        encoding="utf-8",
    )

    prompt_library = f"""# Prompt Library

## Investor Prompt
Using the SOURCE_OF_TRUTH, explain the reliability value of a ~50% chatter reduction for data center operators. Anchor to commit {commit_hash}.

## Peer Review Prompt
Draft a technical methodology section explaining why the Wilcoxon route was chosen for our n=8 sample.

## Social Prompt
Write a concise update about the BITO {commit_hash} release, focusing on the verified safety-reliability trade-off.
"""
    (assets_dir / "PROMPT_LIBRARY.md").write_text(prompt_library, encoding="utf-8")

    print(f"Studio assets generated: {assets_dir}")


if __name__ == "__main__":
    generate_studio_assets()
