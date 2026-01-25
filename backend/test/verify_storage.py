from pathlib import Path

def check():
    raw = Path("storage/raw")
    proc = Path("storage/processed")
    
    print("=== RAW ===")
    if raw.exists():
        for f in raw.iterdir():
            print(f"{f.name} - {f.stat().st_size}")
    else:
        print("storage/raw does not exist")

    print("\n=== PROCESSED ===")
    if proc.exists():
        for f in proc.rglob("*"):
            if f.is_file():
                print(f"{f.relative_to(proc)} - {f.stat().st_size}")
    else:
        print("storage/processed does not exist")

if __name__ == "__main__":
    check()
