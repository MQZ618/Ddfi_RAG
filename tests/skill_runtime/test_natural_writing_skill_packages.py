from pathlib import Path
from zipfile import ZipFile

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]


def read_zip_text(package: str, member: str) -> str:
    with ZipFile(ROOT / "skills" / package) as archive:
        return archive.read(member).decode("utf-8")


def test_results_skill_does_not_force_formulaic_subsection_closures():
    text = read_zip_text(
        "results-section-revision.zip", "results-section-revision/SKILL.md"
    )

    assert "End each subsection with a sentence that changes" not in text
    assert "Does the paragraph close by stating what changes in interpretation?" not in text
    assert "A closing inference is optional" in text
    assert "Do not add a transition only to make the subsection feel complete" in text
    assert "Subsection length follows evidence and argumentative importance" in text


def test_nature_polishing_uses_sentence_load_as_a_soft_signal():
    text = read_zip_text(
        "nature-polishing.zip", "nature-polishing/static/fragments/language/en.md"
    )
    results = read_zip_text(
        "nature-polishing.zip", "nature-polishing/static/fragments/section/results.md"
    )

    assert "Keep every sentence at `<= 30` words" not in text
    assert "Do not produce full sentences under `10` words" not in text
    combined = text + "\n" + results
    assert "35–40 words" in combined
    assert "review signal" in combined
    assert "multiple logical functions" in combined
    assert "Do not split a sentence solely because of visual length" in combined


def test_nature_writing_does_not_turn_structure_heuristics_into_templates():
    workflow = read_zip_text("nature-writing.zip", "nature-writing/static/core/workflow.md")
    experiments = read_zip_text(
        "nature-writing.zip", "nature-writing/static/fragments/section/experiments.md"
    )
    method = read_zip_text(
        "nature-writing.zip", "nature-writing/static/fragments/section/method.md"
    )

    assert "must do exactly one job" not in workflow
    assert "Each subsection has a claim-first opening" not in experiments
    assert "Close each coherent evidence unit" not in experiments
    assert "one controlling job" in workflow
    assert "section-level option, not a subsection template" in experiments
    assert "A short ablation may require only one compact paragraph" in experiments
    assert "The motivation–mechanism–role triad is a completeness check" in method


def test_nature_writing_default_delivery_returns_only_requested_prose():
    output_format = read_zip_text(
        "nature-writing.zip", "nature-writing/static/core/output-format.md"
    )

    assert "Default delivery:" in output_format
    assert "Return the requested manuscript prose once." in output_format
    assert "Keep planning, detected axes, Skill activity, word-count checks" in output_format
    assert "Do not repeat a draft after checking it." in output_format
    assert "Do not append section outlines, assumptions, claim-evidence maps" in output_format
    assert "Section outline:" not in output_format
    assert "Assumptions or missing inputs:" not in output_format
    assert "Claim-evidence map:" not in output_format
    assert "Why this structure:" not in output_format
    assert "To redirect me:" not in output_format


def test_nature_writing_alignment_is_internal_by_default():
    workflow = read_zip_text("nature-writing.zip", "nature-writing/static/core/workflow.md")

    assert "Keep the alignment block internal by default." in workflow
    assert "Only ask a user question when a missing choice would materially change the prose." in workflow
    assert "Before writing full prose, show the user a short alignment block" not in workflow
    assert "**One-sentence argument**" not in workflow
    assert "detected paper type" not in workflow
    assert "paragraph map" not in workflow


def test_nature_polishing_default_delivery_returns_only_polished_text():
    output_format = read_zip_text(
        "nature-polishing.zip", "nature-polishing/static/core/output-format.md"
    )

    assert "Return only the polished text." in output_format
    assert "Do not expose Skill loading, detected axes, internal review" in output_format
    assert "Do not append Revision notes unless the user explicitly requests" in output_format
    assert "Revision notes:" not in output_format


def test_academic_review_checks_naturalness_failure_modes_before_rewriting():
    text = read_zip_text("academic-writing-review.zip", "academic-writing-review/SKILL.md")

    assert "subsection length symmetry" in text
    assert "overloaded sentence density" in text
    assert "formulaic paragraph closure" in text
    assert "diagnose before rewriting" in text


def test_prompt_v4_contains_style_conflict_arbitration():
    prompt = (ROOT / "prompts" / "科研助手-production-v4.md").read_text(encoding="utf-8")

    assert "# Style Conflict Resolution" in prompt
    assert "Skill heuristics are diagnostic signals" in prompt
    assert "不得把句长范围当作输出硬约束" in prompt
    assert "不得为了章节不对称而随机改变篇幅" in prompt


def test_v4_candidate_changes_only_system_prompt():
    source_path = ROOT / "agentDSL" / "科研助手-production-v3-live.yml"
    candidate_path = ROOT / "agentDSL" / "科研助手-production-v4-naturalness-candidate.yml"
    prompt = (ROOT / "prompts" / "科研助手-production-v4.md").read_text(encoding="utf-8")
    source = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    candidate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))

    source_prompt = source["agent_packages"]["agent_1"]["soul"]["prompt"]["system_prompt"]
    candidate_prompt = candidate["agent_packages"]["agent_1"]["soul"]["prompt"]["system_prompt"]
    assert source_prompt != candidate_prompt
    assert candidate_prompt == prompt

    source["agent_packages"]["agent_1"]["soul"]["prompt"]["system_prompt"] = "<prompt>"
    candidate["agent_packages"]["agent_1"]["soul"]["prompt"]["system_prompt"] = "<prompt>"
    assert candidate == source
    assert "api_key" not in candidate_prompt.lower()


@pytest.mark.parametrize(
    "package,member",
    [
        ("academic-writing-review.zip", "academic-writing-review/SKILL.md"),
        ("results-section-revision.zip", "results-section-revision/SKILL.md"),
        ("nature-polishing.zip", "nature-polishing/static/fragments/language/en.md"),
        ("nature-writing.zip", "nature-writing/static/core/workflow.md"),
    ],
)
def test_target_skill_members_are_utf8_text(package: str, member: str):
    assert read_zip_text(package, member)
