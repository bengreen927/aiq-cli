"""Local PDF report generation using ReportLab.

Generates a professional AIQ score report that the user keeps locally.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

if TYPE_CHECKING:
    from pathlib import Path


class ReportData(BaseModel):
    """Data needed to generate the PDF report."""

    user_email: str = "Not provided"
    role_category: str = ""
    overall_score: int = 0
    model_scores: dict[str, int] = Field(default_factory=dict)
    layer_scores: dict[str, int] = Field(default_factory=dict)
    challenge_version: str = "v1.0"
    evaluation_id: str = ""
    evaluated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PdfReportGenerator:
    """Generates a local PDF report from evaluation results."""

    def generate(self, data: ReportData, output_path: Path) -> None:
        """Generate the PDF report and save to output_path."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "AIQTitle",
            parent=styles["Title"],
            fontSize=28,
            spaceAfter=6,
        )
        heading_style = ParagraphStyle(
            "AIQHeading",
            parent=styles["Heading2"],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
        )
        body_style = styles["BodyText"]

        elements: list[Flowable] = []

        # Title
        elements.append(Paragraph("AIQ Score Report", title_style))
        elements.append(Spacer(1, 12))

        # Summary info
        elements.append(Paragraph(f"Role: {data.role_category}", body_style))
        elements.append(Paragraph(f"Challenge Set: {data.challenge_version}", body_style))
        elements.append(Paragraph(f"Evaluation ID: {data.evaluation_id}", body_style))
        elements.append(Paragraph(f"Date: {data.evaluated_at[:10]}", body_style))
        elements.append(Spacer(1, 20))

        # Overall Score
        score_style = ParagraphStyle(
            "ScoreStyle",
            parent=styles["Title"],
            fontSize=48,
            textColor=self._score_color(data.overall_score),
            alignment=1,  # Center
        )
        elements.append(Paragraph(str(data.overall_score), score_style))
        elements.append(
            Paragraph(
                "<para alignment='center'>Overall AIQ Score (0-100)</para>",
                body_style,
            )
        )
        elements.append(Spacer(1, 30))

        # Per-Model Scores
        elements.append(Paragraph("Per-Model Scores", heading_style))
        model_data = [["Model", "Score"]]
        for model, score in sorted(data.model_scores.items()):
            model_data.append([model.title(), str(score)])

        model_table = Table(model_data, colWidths=[3 * inch, 2 * inch])
        model_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (1, 0), (1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                    ("TOPPADDING", (0, 0), (-1, 0), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F8F9FA")],
                    ),
                ]
            )
        )
        elements.append(model_table)
        elements.append(Spacer(1, 30))

        # Per-Layer Breakdown
        elements.append(Paragraph("Per-Layer Breakdown", heading_style))
        layer_labels = {
            "execution": "Execution",
            "robustness": "Robustness",
            "constraint_satisfaction": "Constraint Satisfaction",
            "ground_truth": "Ground Truth Comparison",
            "telemetry": "Telemetry",
            "ai_judge": "AI Judge",
        }
        layer_data = [["Layer", "Score"]]
        for key, label in layer_labels.items():
            score = data.layer_scores.get(key, 0)
            layer_data.append([label, str(score)])

        layer_table = Table(layer_data, colWidths=[3.5 * inch, 1.5 * inch])
        layer_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (1, 0), (1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                    ("TOPPADDING", (0, 0), (-1, 0), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F8F9FA")],
                    ),
                ]
            )
        )
        elements.append(layer_table)
        elements.append(Spacer(1, 30))

        # Footer
        elements.append(
            Paragraph(
                "This report was generated locally by AIQ CLI. "
                "Verify this score at https://aiq.dev/verify",
                body_style,
            )
        )

        doc.build(elements)

    def _score_color(self, score: int) -> colors.Color:
        """Return a color based on score tier."""
        if score >= 90:
            return colors.HexColor("#27AE60")  # Green
        elif score >= 70:
            return colors.HexColor("#2980B9")  # Blue
        elif score >= 50:
            return colors.HexColor("#F39C12")  # Orange
        else:
            return colors.HexColor("#E74C3C")  # Red
