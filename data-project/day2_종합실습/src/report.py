"""리포트 자동화: Jinja2 템플릿에 분석 결과를 채워 reports/report.md를 생성한다."""
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path("templates")
TEMPLATE_NAME = "report_template.md.j2"
OUTPUT_PATH = Path("reports/report.md")


def run(context: dict) -> str:
    """분석 결과 context를 Jinja2 템플릿에 렌더링해 report.md로 저장한다.

    Args:
        context: 앞선 모든 run()의 반환값을 합친 dict.

    Returns:
        str: 저장된 report.md 경로
    """
    render_context = dict(context)
    for key in ("describe", "corr"):
        value = render_context.get(key)
        if isinstance(value, pd.DataFrame):
            render_context[key] = value.to_string()

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template(TEMPLATE_NAME)
    rendered = template.render(**render_context)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    return str(OUTPUT_PATH)
