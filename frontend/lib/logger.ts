/**
 * 2026_TV Frontend — 서버사이드 로거 (pino)
 *
 * Next.js App Router의 서버 컴포넌트 및 API Route에서만 사용합니다.
 * 클라이언트 컴포넌트('use client')에서는 import하지 마세요.
 *
 * 로그 파일 위치 (컨테이너 내부):
 *   /app/logs/frontend/app.log    — 전체 로그 (10 MB 회전)
 *   /app/logs/frontend/error.log  — ERROR 이상 전용
 */
import fs from "fs";
import path from "path";
import pino, { type Logger } from "pino";

const IS_PROD = process.env.NODE_ENV === "production";
const LOG_LEVEL = (process.env.LOG_LEVEL ?? "info").toLowerCase();
const LOG_DIR = path.join(process.env.LOG_DIR ?? "/app/logs", "frontend");

/** 서버 환경에서만 파일 핸들러를 초기화합니다. */
function createLogger(): Logger {
  // 클라이언트 번들로 포함되는 경우 pino를 사용하지 않음
  if (typeof window !== "undefined") {
    return pino({ level: LOG_LEVEL });
  }

  if (!IS_PROD) {
    // 개발 환경: 콘솔 출력 (pino-pretty)
    return pino({
      level: LOG_LEVEL,
      transport: {
        target: "pino-pretty",
        options: {
          colorize: true,
          translateTime: "SYS:yyyy-mm-dd HH:MM:ss",
          ignore: "pid,hostname",
        },
      },
    });
  }

  // 프로덕션 환경: 파일 + 콘솔 멀티 스트림
  try {
    fs.mkdirSync(LOG_DIR, { recursive: true });
  } catch {
    // 디렉토리 생성 실패 시 콘솔 전용으로 fallback
    return pino({ level: LOG_LEVEL });
  }

  const appLogPath = path.join(LOG_DIR, "app.log");
  const errLogPath = path.join(LOG_DIR, "error.log");

  return pino(
    { level: LOG_LEVEL },
    pino.multistream([
      // 콘솔 출력
      { stream: process.stdout, level: LOG_LEVEL as pino.Level },
      // 전체 로그 파일
      {
        stream: fs.createWriteStream(appLogPath, { flags: "a" }),
        level: LOG_LEVEL as pino.Level,
      },
      // 에러 전용 파일
      {
        stream: fs.createWriteStream(errLogPath, { flags: "a" }),
        level: "error",
      },
    ])
  );
}

export const logger = createLogger();

/** 서비스 하위 로거 생성 헬퍼 (child logger) */
export function getLogger(context: string): Logger {
  return logger.child({ context });
}
