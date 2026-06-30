import csv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "feedback.csv")
MD_FILE = os.path.join(BASE_DIR, "feedback_summary.md")

def generate_report():
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} not found.")
        return

    total = 0
    helpful = 0

    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            if row.get("Feedback Type") == "Helpful":
                helpful += 1

    not_helpful = total - helpful
    pct = (helpful / total * 100) if total > 0 else 0

    report = f"""# Feedback Summary

## Analytics
- **Total Feedback:** {total}
- **Helpful Count:** {helpful}
- **Not Helpful Count:** {not_helpful}
- **Helpful Percentage:** {pct:.1f}%
"""
    with open(MD_FILE, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"Successfully generated {MD_FILE}")

if __name__ == "__main__":
    generate_report()
