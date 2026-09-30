import os
import requests

api_key = os.environ.get("NASDAQ_API_KEY")

if not api_key:
    raise RuntimeError("NASDAQ_API_KEY not found")

url = "https://data.nasdaq.com/api/v3/datasets/FRED/GDP.json"

response = requests.get(
    url,
    params={"api_key": api_key},
    timeout=30
)

print("HTTP STATUS:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise RuntimeError("Nasdaq Data Link API test failed")

data = response.json()

print("Nasdaq Data Link API connection: OK")
print("Dataset:", data.get("dataset", {}).get("name"))
