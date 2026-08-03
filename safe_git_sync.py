import subprocess
import os

git_path = r"C:\Users\eric.su\AppData\Local\GitHubDesktop\app-3.6.3\resources\app\git\cmd\git.exe"

def run_git(args):
    cmd = [git_path] + args
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    print(f"Running: git {' '.join(args)}")
    print(f"Exit code: {res.returncode}")
    if res.stdout:
        print(f"STDOUT:\n{res.stdout}")
    if res.stderr:
        print(f"STDERR:\n{res.stderr}")
    return res.returncode

# 1. Read files into memory
print("Backing up modified files...")
with open("scripts/gold_tracker.py", "r", encoding="utf-8") as f:
    gold_tracker_content = f.read()

with open("data/gold_prices.csv", "r", encoding="utf-8-sig") as f:
    gold_prices_content = f.read()

# 2. Hard reset to remote main
print("Syncing with origin/main...")
run_git(["reset", "--hard", "origin/main"])

# 3. Restore files
print("Restoring modified files...")
with open("scripts/gold_tracker.py", "w", encoding="utf-8") as f:
    f.write(gold_tracker_content)

with open("data/gold_prices.csv", "w", encoding="utf-8-sig") as f:
    f.write(gold_prices_content)

# 4. Commit and Push
print("Committing and pushing...")
run_git(["add", "."])
run_git(["commit", "-m", "Fix: gold tracker self-healing logic and updated gold prices"])
run_git(["push", "origin", "main"])
