
import yfinance as yf
import pandas as pd

ticker = "TWD=X"
df = yf.download(ticker, period="1d", interval="15m", progress=False)
print("Columns:", df.columns)
print("Index name:", df.index.name)
print("Index type:", type(df.index))
print("First few rows:")
print(df.head())
