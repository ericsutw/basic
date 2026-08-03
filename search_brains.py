import os

brain_dir = r"C:\Users\eric.su\.gemini\antigravity\brain"
for item in os.listdir(brain_dir):
    p = os.path.join(brain_dir, item)
    if os.path.isdir(p) and item != "tempmediaStorage" and item != "f92d01f0-5ead-4db7-81d0-7d3b02ad7f5e":
        transcript_path = os.path.join(p, ".system_generated", "logs", "transcript.jsonl")
        if os.path.exists(transcript_path):
            print(f"Searching in brain: {item}")
            try:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if "git" in line.lower() and "push" in line.lower():
                            # Print matching raw lines (shortened)
                            print(line[:300] + "...")
            except Exception as e:
                print(f"Error reading {item}: {e}")
