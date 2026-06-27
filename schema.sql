-- ============================================================
--  Market Data ETL Pipeline — MySQL Schema
--  Run: mysql -u root -p < sql/schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS market_pipeline
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE market_pipeline;

-- ── Raw stock prices ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS stock_prices (
  id            BIGINT        NOT NULL AUTO_INCREMENT,
  symbol        VARCHAR(10)   NOT NULL,
  trade_date    DATE          NOT NULL,
  open_price    DECIMAL(12,4) NOT NULL,
  high_price    DECIMAL(12,4) NOT NULL,
  low_price     DECIMAL(12,4) NOT NULL,
  close_price   DECIMAL(12,4) NOT NULL,
  volume        BIGINT        NOT NULL,
  inserted_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  UNIQUE KEY uq_symbol_date (symbol, trade_date),
  INDEX idx_symbol      (symbol),
  INDEX idx_trade_date  (trade_date)
) ENGINE=InnoDB;

-- ── Anomaly log ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS anomaly_alerts (
  id              BIGINT          NOT NULL AUTO_INCREMENT,
  symbol          VARCHAR(10)     NOT NULL,
  trade_date      DATE            NOT NULL,
  close_price     DECIMAL(12,4)   NOT NULL,
  zscore          DECIMAL(8,4)    NULL,
  iqr_flag        TINYINT(1)      NOT NULL DEFAULT 0,
  anomaly_type    VARCHAR(30)     NOT NULL,   -- 'ZSCORE', 'IQR', 'BOTH'
  baseline_mean   DECIMAL(12,4)   NULL,
  baseline_std    DECIMAL(12,4)   NULL,
  detected_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  INDEX idx_symbol_date (symbol, trade_date),
  INDEX idx_detected_at (detected_at)
) ENGINE=InnoDB;

-- ── Pipeline run log ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id              BIGINT        NOT NULL AUTO_INCREMENT,
  started_at      DATETIME      NOT NULL,
  finished_at     DATETIME      NULL,
  status          VARCHAR(20)   NOT NULL DEFAULT 'RUNNING', -- RUNNING | SUCCESS | FAILED
  rows_extracted  INT           NULL,
  rows_loaded     INT           NULL,
  anomalies_found INT           NULL,
  error_message   TEXT          NULL,

  PRIMARY KEY (id)
) ENGINE=InnoDB;
