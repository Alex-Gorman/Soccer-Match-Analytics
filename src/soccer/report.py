from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

def _get_template_env() -> Environment:
    """
    Create a Jinja2 environment that looks for templates/
    at the project root (…/templates).
    """
    # This file lives at …/src/soccer/report.py
    # Project root is two directories up from here.
    template_dir = Path(__file__).resolve().parents[2] / "templates"
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )

def build_html_report(df: pd.DataFrame, summary: Dict[str, Any], out_path: Path) -> None:
    """
    Render templates/report.html.j2 using the summary dict and write to out_path.
    """
    env = _get_template_env()
    template = env.get_template("report.html")
    html = template.render(summary=summary)
    out_path = Path(out_path)
    out_path.write_text(html, encoding="utf-8")
