# 📈 Market Data ETL Pipeline — Python & MySQL

A production-style ETL pipeline that fetches live stock market data from a public API,
stores it in MySQL, detects price anomalies using statistical analysis, and triggers alerts.

Built by **Shakthi Kumar Naik** · [LinkedIn](https://www.linkedin.com/in/shakthikumarnaik/) · [Portfolio](https://github.com/Shakthi003-Naik)

---

## 🏗 Architecture

```
Alpha Vantage API
      │
      ▼
  extract.py        ← Fetch raw JSON from API
      │
      ▼
  transform.py      ← Clean, validate, normalise data
      │
      ▼
  load.py           ← Insert into MySQL (upsert logic)
      │
      ▼
  anomaly.py        ← Z-score + IQR anomaly detection
      │
      ▼
  alerts.py         ← Log alerts + console output
      │
      ▼
  scheduler.py      ← Run pipeline every N minutes
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Data Source | Alpha Vantage REST API (free) |
| Database | MySQL 8+ |
| Data Processing | Pandas, NumPy |
| Scheduling | APScheduler |
| Logging | Python logging module |
| Testing | pytest |

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/Shakthi003-Naik/python-sql-pipeline.git
cd python-sql-pipeline
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up MySQL
```bash
mysql -u root -p < sql/schema.sql
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env with your API key and DB credentials
```

### 5. Run the pipeline once
```bash
python src/pipeline.py --run-once
```

### 6. Run on a schedule (every 15 minutes)
```bash
python src/scheduler.py
```

---

## 🔑 Getting a Free API Key

1. Go to [alphavantage.co](https://www.alphavantage.co/support/#api-key)
2. Sign up for free — no credit card required
3. Paste the key into your `.env` file

---

## 📁 Project Structure

```
pipeline/
├── src/
│   ├── extract.py        # API data fetching
│   ├── transform.py      # Data cleaning & validation
│   ├── load.py           # MySQL insert/upsert
│   ├── anomaly.py        # Anomaly detection engine
│   ├── alerts.py         # Alert dispatcher
│   ├── db.py             # DB connection manager
│   └── pipeline.py       # Main orchestrator
├── sql/
│   └── schema.sql        # MySQL table definitions
├── tests/
│   ├── test_transform.py
│   └── test_anomaly.py
├── logs/                 # Auto-generated alert logs
├── .env.example
├── requirements.txt
└── README.md
```

---

## 📊 Sample Output

```
[2024-01-15 09:30:00] INFO  — Pipeline started for symbols: AAPL, MSFT, GOOGL
[2024-01-15 09:30:02] INFO  — Extracted 180 rows from Alpha Vantage API
[2024-01-15 09:30:02] INFO  — Transformed: 180 valid rows, 0 dropped
[2024-01-15 09:30:03] INFO  — Loaded 180 rows into MySQL (3 upserted)
[2024-01-15 09:30:03] ⚠ ALERT — AAPL price anomaly detected!
                               Current: $187.32 | Z-score: 3.21 | Threshold: ±3.0
[2024-01-15 09:30:03] INFO  — Pipeline completed in 3.2s
```

---

## 🧠 Anomaly Detection Logic

Two methods run in parallel:

- **Z-score:** Flags values more than 3 standard deviations from the 30-day mean
- **IQR (Interquartile Range):** Flags values outside 1.5× the interquartile fence

Both methods must agree before an alert fires — reducing false positives.

---

## 📄 License
MIT — free to use and adapt.
