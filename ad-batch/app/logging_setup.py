"""structlog 기반 로깅 설정 — ad-batch.

structlog 이벤트를 Python stdlib logging으로 위임한 뒤,
RotatingFileHandler를 통해 logs 디렉토리에 파일로 기록합니다.

로그 파일 구조:
    logs/
    └── ad-batch/
        ├── app.log      전체 로그 (10 MB 회전, 7일 보관)
        └── error.log    ERROR 이상 전용 (10 MB 회전, 30일 보관)
"""
import logging
import logging.handlers
import sys
from pathlib import Path

import structlog


def setup_logging(
    service_name: str = "ad-batch",
    log_level: str = "INFO",
    log_dir: str = "/app/logs",
) -> None:
    """structlog + stdlib RotatingFileHandler 로깅 설정.

    Args:
        service_name: 로그 서브디렉토리 이름
        log_level: 로그 레벨 문자열 (예: "INFO", "DEBUG")
        log_dir: 로그 루트 디렉토리
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # ── 로그 디렉토리 생성 ────────────────────────────────────────
    service_log_dir = Path(log_dir) / service_name
    service_log_dir.mkdir(parents=True, exist_ok=True)

    # ── stdlib 포맷터 ─────────────────────────────────────────────
    plain_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── 콘솔 핸들러 ──────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(plain_fmt)

    # ── app.log 핸들러 (10 MB 회전, 최대 7개 백업) ───────────────
    app_handler = logging.handlers.RotatingFileHandler(
        filename=str(service_log_dir / "app.log"),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=7,
        encoding="utf-8",
    )
    app_handler.setLevel(numeric_level)
    app_handler.setFormatter(plain_fmt)

    # ── error.log 핸들러 (ERROR 이상, 10 MB 회전, 최대 30개 백업) ─
    error_handler = logging.handlers.RotatingFileHandler(
        filename=str(service_log_dir / "error.log"),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=30,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(plain_fmt)

    # ── root logger 설정 ─────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(app_handler)
    root.addHandler(error_handler)

    # ── structlog 설정 — stdlib logging으로 위임 ─────────────────
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # stdlib 핸들러에 structlog ProcessorFormatter 적용
    structlog_fmt = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=False),
    )
    app_handler.setFormatter(structlog_fmt)
    error_handler.setFormatter(structlog_fmt)

    log = structlog.get_logger()
    log.info(
        "logging.setup_complete",
        service=service_name,
        level=log_level.upper(),
        log_dir=str(service_log_dir),
    )
