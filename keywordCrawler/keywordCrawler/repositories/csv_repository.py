import csv
import logging
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_KEYWORD_PATH = PROJECT_ROOT / "keywords.csv"


class CSVKeywordRepository:
    """키워드 목록을 CSV 파일로 저장한다."""

    def __init__(self, default_path=DEFAULT_KEYWORD_PATH, encoding="utf-8"):
        self.default_path = Path(default_path)
        self.encoding = encoding

    def save(self, keywords, output_path=None):
        """키워드를 CSV로 저장하고 경로를 반환한다."""
        path = Path(output_path) if output_path else self.default_path
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding=self.encoding, newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["키워드"])
            writer.writerows([[k] for k in keywords])

        logging.info(f"키워드 저장 완료: {path}")
        return path
