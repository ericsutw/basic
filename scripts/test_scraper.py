import requests

def test_fuzzy_endpoints():
    base = "https://rate.bot.com.tw"
    
    # POST attempts
    post_targets = [
        "/gold/passbook",
        "/gold/passbook/search",
        "/gold/search/TWD"
    ]
    
    payloads = [
        {"startDate": "2026/01/01", "endDate": "2026/01/31"}, # Slash
        {"startDate": "2026-01-01", "endDate": "2026-01-31"}, # Dash
        {"startDate": "20260101", "endDate": "20260131"},     # Compact
    ]
    
    print("Testing POST endpoints...")
    for ep in post_targets:
        url = base + ep
        for p in payloads:
            try:
                res = requests.post(url, data=p, timeout=5)
                if res.status_code == 200 and len(res.content) > 1000:
                    print(f"POST {url} with {p}: {res.status_code}")
                    if "table" in res.text:
                         print("  Table found in response!")
            except Exception as e:
                pass

    # Fuzzy CSV attempts
    csv_targets = [
        "/gold/flcsv/0/day",
        "/gold/csv/0/day",
        "/gold/new/csv",
    ]
    print("\nTesting Fuzzy CSV endpoints...")
    for ep in csv_targets:
        url = base + ep
        try:
            res = requests.head(url, timeout=5)
            if res.status_code == 200:
                print(f"HEAD {url}: {res.status_code}")
        except:
            pass

if __name__ == "__main__":
    test_fuzzy_endpoints()
