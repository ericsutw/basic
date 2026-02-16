import requests
import re
import json

def inspect():
    url = "https://rate.bot.com.tw/gold/chart/year/TWD"
    print(f"Fetching {url}...")
    res = requests.get(url)
    
    # Look for "quote" variable which often holds the data
    # Patterns like: var quote = [...];
    patterns = [
        r'var quote = (\[.*?\]);',
        r'val_quote = (\[.*?\]);',
        r'data: (\[.*?\])'
    ]
    
    found = False
    for p in patterns:
        matches = re.findall(p, res.text, re.DOTALL)
        if matches:
            print(f"Found match for pattern {p}!")
            print(f"Data length: {len(matches[0])}")
            print(f"Snippet: {matches[0][:200]}...")
            found = True
            
            # Try to parse JSON
            try:
                data = json.loads(matches[0])
                print(f"Successfully parsed JSON! Item count: {len(data)}")
                if len(data) > 0:
                    print(f"First item: {data[0]}")
            except Exception as e:
                print(f"JSON parse error: {e}")
                
    if not found:
        print("No data found matching patterns.")
        # Print a few lines around "quote"
        lines = res.text.splitlines()
        for i, line in enumerate(lines):
            if "quote" in line:
                print(f"Line {i}: {line.strip()[:200]}")

if __name__ == "__main__":
    inspect()
