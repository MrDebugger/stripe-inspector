"""HTML and PDF report generators."""

import io
import json
import os
import re
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

from stripe_inspector import __version__


def get_template_dir():
    return os.path.join(os.path.dirname(__file__), "web", "templates")


def generate_html_report(result: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(get_template_dir()),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html")

    return template.render(
        result=result,
        result_json=json.dumps(result, indent=2, default=str),
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        version=__version__,
    )


# CSS variable -> hardcoded color map for PDF
_CSS_VAR_MAP = {
    "var(--bg)": "#0f1117",
    "var(--card)": "#1a1d27",
    "var(--border)": "#2d3140",
    "var(--accent)": "#6c63ff",
    "var(--green)": "#10b981",
    "var(--red)": "#ef4444",
    "var(--yellow)": "#f59e0b",
    "var(--text)": "#e4e4e7",
    "var(--dim)": "#71717a",
    "var(--bright)": "#fafafa",
    "var(--bright,#fafafa)": "#fafafa",
}


def _resolve_css_vars(html: str) -> str:
    """Replace CSS var() with hardcoded values for PDF renderers."""
    for var, val in _CSS_VAR_MAP.items():
        html = html.replace(var, val)
    # Catch any remaining var() calls
    html = re.sub(r'var\(--[a-z-]+\)', '#71717a', html)
    return html


def generate_pdf_report(result: dict) -> bytes:
    try:
        from xhtml2pdf import pisa
    except ImportError:
        raise ImportError(
            "PDF generation requires xhtml2pdf. Install with: "
            "pip install stripe-inspector[pdf]"
        )

    env = Environment(
        loader=FileSystemLoader(get_template_dir()),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report_pdf.html")
    html_content = template.render(
        result=result,
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        version=__version__,
    )

    pdf_buffer = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html_content), dest=pdf_buffer, raise_exception=False)
    return pdf_buffer.getvalue()
