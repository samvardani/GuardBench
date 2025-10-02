
from __future__ import annotations
from src.generator.adversary import run
def main():
    stats = run(max_cases_per_category=5, k_per_case=3)
    print("Adversarial generation:", stats)
if __name__ == "__main__":
    main()
