"""Create a reproducible, fictional 1,000-row classroom dataset with edge cases."""
import csv, random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rng = random.Random(7307)
first = ["Aarav","Diya","Kabir","Ira","Neel","Anaya","Rohan","Meera","Vivaan","Sara","Arjun","Tara","Dev","Mira","Kian","Nisha","Reyansh","Aditi","Ishaan","Leela"]
last = ["Shah","Mehta","Patil","Desai","Joshi","Rao","Nair","Kapoor","Iyer","Kulkarni","Sen","Pillai","Verma","Das","Bose","Malhotra","Saxena","Khan","Menon","Ghosh"]
fields = ["candidate_id","candidate_name","email","skills_score","experience_score","assessment_score","application_role"]
rows = []
for i in range(1, 1001):
    name = f"{first[(i-1)%len(first)]} {last[((i-1)//len(first)+i)%len(last)]}"
    rows.append({"candidate_id":f"C{i:04d}","candidate_name":name,"email":f"candidate{i:04d}@example.test","skills_score":rng.randint(25,100),"experience_score":rng.randint(10,100),"assessment_score":rng.randint(20,100),"application_role":"Junior Software Developer"})
# Intentional known cases are included in the total row count and documented in the README.
for i, score in enumerate([75,74.99,50,49.99,100,0], 0):
    row = rows[i]; row["skills_score"] = score; row["experience_score"] = score; row["assessment_score"] = score
rows[10]["email"] = ""
rows[11]["email"] = "not-an-email"
rows[12]["skills_score"] = 101
rows[13]["experience_score"] = -1
rows[14]["assessment_score"] = "unknown"
rows[15]["candidate_name"] = "  "
rows[16]["candidate_id"] = rows[15]["candidate_id"]
rows[17]["candidate_id"] = rows[0]["candidate_id"]
rows[18]["application_role"] = "Junior Software Developer "
rows[19]["skills_score"] = " 88 "
with (ROOT/"candidates.csv").open("w", newline="", encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print(f"Wrote {len(rows)} synthetic rows to candidates.csv")
