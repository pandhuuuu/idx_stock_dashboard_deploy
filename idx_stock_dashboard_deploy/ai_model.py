import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

def prepare_features(df):
    df = df.copy()

    df["Return"] = df["Close"].pct_change()

    # MA
    df["MA10"] = df["Close"].rolling(10).mean()
    df["MA30"] = df["Close"].rolling(30).mean()

    # RSI
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    exp1 = df["Close"].ewm(span=12).mean()
    exp2 = df["Close"].ewm(span=26).mean()
    df["MACD"] = exp1 - exp2

    # Target (next day up/down)
    df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)

    df = df.dropna()

    features = df[["Return", "MA10", "MA30", "RSI", "MACD"]]
    target = df["Target"]

    return features, target


def train_model(df):
    X, y = prepare_features(df)

    model = RandomForestClassifier(n_estimators=100)
    model.fit(X, y)

    return model


def predict_signal(model, df):
    X, _ = prepare_features(df)

    latest = X.iloc[-1:]
    prob = model.predict_proba(latest)[0][1]  # probability UP

    return prob
