# src/soccer/report.py

"""
HTML report rendering using Jinja2.

This module loads the Jinja2 environment pointed at the project's `templates/`
directory and renders the summary dictionary into `report.html`.

Typical usage:
    >>> from pathlib import Path
    >>> from soccer.report import build_html_report
    >>> build_html_report(df, summary, Path("out/report.html"))
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import pandas as pd
import shutil
from jinja2 import Environment, FileSystemLoader, select_autoescape


def _get_template_env() -> Environment:
    """Return a Jinja2 environment rooted at the project's `templates/` directory.

    The `templates/` path is resolved relative to this file:
    `src/soccer/report.py` -> project root (two parents up) → `templates/`.

    Returns:
        A configured `jinja2.Environment` with HTML/XML auto-escaping enabled.
    """

    # templates/src/soccer/report.py  ->  templates/
    template_dir = Path(__file__).resolve().parents[2] / "templates"

    # Load templates from <project>/templates and auto-escape HTML/XML.
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def build_html_report(df: pd.DataFrame, summary: Dict[str, Any], out_path: Path) -> None:
    """Render `templates/report.html` with summary data and write it /out.

    Args:
        df: Cleaned matches DataFrame 
        summary: Aggregated metrics dictionary (from `metrics.build_summary`).
        out_path: Destination for the rendered HTML (e.g., `out/report.html`).


    Examples:
        >>> from pathlib import Path
        >>> build_html_report(df, summary, Path("out/report.html"))  # doctest: +SKIP
    """

    env = _get_template_env()
    template = env.get_template("report.html")
    html = template.render(summary=summary)
    out_path = Path(out_path)
    out_path.write_text(html, encoding="utf-8")

    # --- Copy styles.css next to the generated HTML (so relative <link> works) ---
    # Prefer the directory the template actually loaded from.
    tpl_dir = Path(getattr(template, "filename", "")).parent if getattr(template, "filename", None) else None
    if not tpl_dir or not tpl_dir.exists():
        # Fallbacks if template.filename isn’t available
        # repo-root/templates
        tpl_dir = Path(__file__).resolve().parents[3] / "templates"
        if not tpl_dir.exists():
            # second fallback: src/../templates (just in case)
            tpl_dir = Path(__file__).resolve().parents[2] / "templates"

    src_css = tpl_dir / "styles.css"
    dst_css = out_path.parent / "styles.css"
    if src_css.exists():
        dst_css.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_css, dst_css)