import os
import argparse
from pathlib import Path

def process_directory(directory):
    # Get all mp4 files
    mp4_files = {}
    try:
        for f in directory.iterdir():
            if f.is_file() and f.suffix.lower() == '.mp4':
                # Map original name (without number) to numbered name
                # Format is "01 - Original Name.mp4"
                name_parts = f.name.split(' - ', 1)
                if len(name_parts) == 2 and name_parts[0].isdigit():
                    original_name_stem = name_parts[1].rsplit('.', 1)[0]
                    mp4_files[original_name_stem] = f.name.rsplit('.', 1)[0]
    except Exception as e:
        print(f"Error reading directory {directory}: {e}")
        return

    if not mp4_files:
        return

    print(f"Processing directory: {directory}")
    
    # Process srt files
    for f in directory.iterdir():
        if f.is_file() and f.suffix.lower() == '.srt':
            # Check if file is already numbered
            if len(f.name) > 5 and f.name[:2].isdigit() and f.name[2:5] == " - ":
                continue
                
            # Determine stem to match with mp4
            # Handle .zh.srt or .srt
            is_zh = f.name.endswith('.zh.srt')
            if is_zh:
                original_stem = f.name[:-7] # remove .zh.srt
            else:
                original_stem = f.stem # remove .srt
            
            if original_stem in mp4_files:
                numbered_stem = mp4_files[original_stem]
                if is_zh:
                    new_name = f"{numbered_stem}.zh.srt"
                else:
                    new_name = f"{numbered_stem}.srt"
                
                new_path = directory / new_name
                try:
                    f.rename(new_path)
                    print(f"    Renamed: {f.name} -> {new_name}")
                except Exception as e:
                    print(f"    Error renaming {f.name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Sync srt filenames with numbered mp4 files.")
    parser.add_argument("root_dir", help="Root directory to scan")
    args = parser.parse_args()
    
    root = Path(args.root_dir)
    if not root.exists():
        print(f"Directory not found: {root}")
        return

    # Walk recursively
    for root_path, dirs, files in os.walk(root):
        process_directory(Path(root_path))

if __name__ == "__main__":
    main()
