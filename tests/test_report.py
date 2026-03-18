"""Tests for local PDF report generation."""

from pathlib import Path

from aiq.report.pdf import PdfReportGenerator, ReportData


def test_report_data_creation() -> None:
    data = ReportData(
        user_email="[EMAIL]",
        role_category="Engineering",
        overall_score=82,
        model_scores={"claude": 85, "gpt5": 80, "gemini": 81, "llama": 82},
        layer_scores={
            "execution": 90,
            "robustness": 78,
            "constraint_satisfaction": 85,
            "ground_truth": 75,
            "telemetry": 80,
            "ai_judge": 82,
        },
        challenge_version="v1.0",
        evaluation_id="eval-abc123",
    )
    assert data.overall_score == 82
    assert len(data.model_scores) == 4


def test_pdf_generation(tmp_path: Path) -> None:
    data = ReportData(
        user_email="[EMAIL]",
        role_category="Engineering",
        overall_score=82,
        model_scores={"claude": 85, "gpt5": 80, "gemini": 81, "llama": 82},
        layer_scores={
            "execution": 90,
            "robustness": 78,
            "constraint_satisfaction": 85,
            "ground_truth": 75,
            "telemetry": 80,
            "ai_judge": 82,
        },
        challenge_version="v1.0",
        evaluation_id="eval-abc123",
    )
    output_path = tmp_path / "report.pdf"
    generator = PdfReportGenerator()
    generator.generate(data, output_path)
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    # Verify it's a valid PDF (starts with %PDF)
    with open(output_path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"


def test_pdf_contains_score(tmp_path: Path) -> None:
    data = ReportData(
        user_email="[EMAIL]",
        role_category="Regulatory",
        overall_score=91,
        model_scores={"claude": 93, "gpt5": 89, "gemini": 91, "llama": 91},
        layer_scores={
            "execution": 88,
            "robustness": 92,
            "constraint_satisfaction": 95,
            "ground_truth": 90,
            "telemetry": 85,
            "ai_judge": 93,
        },
        challenge_version="v1.0",
        evaluation_id="eval-xyz789",
    )
    output_path = tmp_path / "report.pdf"
    generator = PdfReportGenerator()
    generator.generate(data, output_path)
    # Basic check that file was generated with meaningful size
    assert output_path.stat().st_size > 1000
