# 🧿 MarketLens

**See the Market Clearly**


---

## 🚀 Overview

**MarketLens** is a data-driven stock analysis platform for the Indonesia Stock Exchange (IDX).
It helps traders and analysts identify opportunities using a combination of **technical indicators, volume intelligence, and a smart scoring system**.

The goal is simple:

> Turn complex market data into clear, actionable insights.

---

## ✨ Key Features

### 🔍 Market Scanner

* Scan multiple IDX stocks automatically
* Generate **BUY / SELL / HOLD** signals
* Rank opportunities using a scoring system

### 📈 Technical Analysis

* **Trend** → SMA, ADX
* **Momentum** → RSI, MACD, KST
* **Strength Confirmation** → DMI (+DI / -DI)

### 📊 Volume Intelligence (Bandarmology)

* Volume Spike Detection
* Extreme Volume Signals
* Accumulation / Distribution behavior
* Battle Zone detection (high activity, low movement)

### 🎯 Smart Signal Engine

* Multi-indicator scoring model
* Outputs:

  * **Lens Signal** (BUY / SELL / HOLD)
  * **Clarity Score (%)**
  * **Bull vs Bear Strength**

### ⚖️ Risk Management

* ATR-based Stop Loss & Take Profit
* Dynamic Risk-Reward Ratio

---

## 🖥️ Dashboard

Interactive dashboard built with Streamlit:

* Real-time market overview
* Broker activity analysis
* Custom filters (Top N, Date selection)
* Clean and responsive UI

---

## 📂 Project Structure

```bash
market_lens/
│
├── app/                        # 🎨 Streamlit UI
│   ├── streamlit_app.py
│   ├── pages/
│   ├── ui/
│   │   └── components/
│   └── services/
│
├── core/                       # 🧠 Core Logic Engine
│   ├── data/                  # Data fetching
│   ├── signal/                # Indicators & scoring
│   │   ├── indicators/
│   │   ├── scoring.py
│   │   └── engine.py
│   └── utils/
│
├── processors/                # 📊 Data processing
├── scanner/                   # 🔄 CLI scanner
│
├── config.py
├── requirements.txt
└── README.md
```


## 🧠 How It Works

MarketLens uses a **multi-layer analysis engine**:

1. **Trend Detection** → SMA, ADX
2. **Momentum Analysis** → RSI, MACD, KST
3. **Volume Analysis** → Spike & Bandarmology
4. **Volatility** → ATR
5. **Scoring Engine** → Final Signal


```


## 📌 Roadmap

* [ ] Backtesting engine
* [ ] Machine learning-based signals
* [ ] Real-time data integration
* [ ] Portfolio tracking system
* [ ] REST API (FastAPI)

---

## 🤝 Contributing

Contributions are welcome.
Feel free to fork this repository and submit a pull request.

---

## ⚠️ Disclaimer

This project is for **educational and research purposes only**.
It does not constitute financial advice.

---

## 👤 Author

Developed by **Pandhu**
GitHub: https://github.com/pandhuuuu

---
