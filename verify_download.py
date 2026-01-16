import json
import sys
import os
from pathlib import Path
import re

def sanitize_folder_name(name):
    """Clean folder name by removing invalid characters and metadata"""
    # Remove timing information and completion markers
    name = re.sub(r'\d+[smh](\s+\d+[sm])?\s+(remaining)?', '', name)
    name = name.replace('Complete', '').strip()
    
    # Remove invalid filesystem characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '')
    
    # Normalize whitespace
    name = ' '.join(name.split())
    
    # Limit length to 100 characters
    return name[:100].strip() if len(name) > 100 else name.strip()

def sanitize_filename(filename):
    """Remove invalid characters and limit filename length"""
    # Remove invalid filesystem characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Limit length
    return filename[:200].strip() if len(filename) > 200 else filename.strip()

def _should_skip_item(url, name):
    """Check if item should be skipped (quiz/continue/unknown)"""
    is_quiz = '/quiz/' in url or '/continue/' in url
    is_unknown = "Unknown" in name
    return is_quiz, is_unknown

def verify(structure_file, course_folder):
    print(f"🔍 Verifying course integrity...")
    print(f"📚 Structure: {structure_file}")
    print(f"📁 Course Folder: {course_folder}")
    
    course_path = Path(course_folder)
    if not course_path.exists():
        print(f"❌ Course folder not found: {course_folder}")
        return

    with open(structure_file, 'r', encoding='utf-8') as f:
        structure = json.load(f)

    missing = []
    found_count = 0
    total_count = 0
    skipped_count = 0
    
    module_count = 0
    for module_name, lessons in structure.items():
        module_count += 1
        
        is_quiz, is_unknown = _should_skip_item("", module_name)
        if is_unknown and len(structure) > 1:
            continue
            
        module_folder_name = f"{module_count:02d} - {sanitize_folder_name(module_name)}"
        module_path = course_path / module_folder_name
        
        lesson_count = 0
        for lesson_name, videos in lessons.items():
            lesson_count += 1
            
            is_quiz, is_unknown = _should_skip_item("", lesson_name)
            if is_unknown and len(lessons) > 1:
                continue
                
            lesson_folder_name = f"{lesson_count:02d} - {sanitize_folder_name(lesson_name)}"
            lesson_path = module_path / lesson_folder_name
            
            video_count = 0
            for video in videos:
                url = video['url']
                title = video['title']
                
                is_quiz, _ = _should_skip_item(url, "")
                if is_quiz:
                    skipped_count += 1
                    continue
                
                total_count += 1
                video_count += 1
                
                # Check video file
                video_filename = f"{video_count:02d} - {sanitize_filename(title)}.mp4"
                video_path = lesson_path / video_filename
                
                if video_path.exists() and video_path.stat().st_size > 0:
                    found_count += 1
                    # print(f"✓ Found: {video_filename}")
                else:
                    print(f"❌ Missing: {module_folder_name}/{lesson_folder_name}/{video_filename}")
                    missing.append({
                        'module': module_name,
                        'lesson': lesson_name,
                        'title': title,
                        'url': url,
                        'path': str(video_path)
                    })

    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    print(f"Total Videos Expected: {total_count}")
    print(f"✅ Found: {found_count}")
    print(f"❌ Missing: {len(missing)}")
    print(f"⏭️  Skipped (Quizzes): {skipped_count}")
    
    if missing:
        print("\n📝 Missing Files List:")
        for item in missing:
            print(f"  - {item['title']} ({item['url']})")
            
        # Generate a retry list or commands?
        retry_file = "missing_files.json"
        with open(retry_file, 'w', encoding='utf-8') as f:
            json.dump(missing, f, indent=2, ensure_ascii=False)
        print(f"\nSaved missing files list to: {retry_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python verify_download.py <structure_json> <course_folder_path>")
        sys.exit(1)
        
    verify(sys.argv[1], sys.argv[2])
