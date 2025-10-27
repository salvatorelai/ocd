"""
O'Reilly Complete COURSE Downloader with Chapter Organization
Downloads entire courses organized by Module → Lesson → Videos
"""

import json
import time
import shutil
import traceback
import hashlib
from pathlib import Path
import re
import argparse

from oreilly_base_downloader import OReillyDownloader
from selenium.webdriver.common.by import By


# Constants
PROFILE_DIR = Path("chrome_profile")
DEFAULT_COURSE_NAME = "O'Reilly Course"
COURSE_URL_PATTERN = r'/course/([^/]+)/'


class OReillyCourseDownloader(OReillyDownloader):
    """
    Extended downloader for complete courses with chapter-based organization.
    Inherits from OReillyDownloader and adds course structure extraction.
    """
    
    def __init__(self, email=None, password=None, transcript_only=False, headless=True):
        # Email and password are optional if Chrome profile already has saved login
        super().__init__(
            email=email or "",
            password=password or "",
            download_dir="downloads",
            transcript_only=transcript_only,
            headless=headless
        )
        self.course_structure = None
        self.course_name = None
        
    def _count_videos_in_structure(self, structure):
        """Count total videos in course structure (exclude quizzes)"""
        total = 0
        for module in structure.values():
            for lesson in module.values():
                for item in lesson:
                    if '/quiz/' not in item['url'] and '/continue/' not in item['url']:
                        total += 1
        return total
    
    def load_course_structure(self, json_file):
        """Load and validate course structure from JSON file"""
        print(f"\n📚 Loading course structure from: {json_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            self.course_structure = json.load(f)
        
        total_videos = self._count_videos_in_structure(self.course_structure)
        
        print(f"   ✓ Found {len(self.course_structure)} modules")
        print(f"   ✓ Total videos to download: {total_videos}")
        return total_videos
    
    def sanitize_folder_name(self, name):
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
    
    def _should_skip_item(self, url, name):
        """Check if item should be skipped (quiz/continue/unknown)"""
        is_quiz = '/quiz/' in url or '/continue/' in url
        is_unknown = "Unknown" in name
        return is_quiz, is_unknown
    
    def _download_video_item(self, video_url, video_title, lesson_folder):
        """Download a single video item to specified folder"""
        # Check if already downloaded
        progress = self.load_progress()
        
        if video_url in progress and progress[video_url].get('success'):
            # If transcript-only mode, always skip if in progress
            if self.transcript_only:
                print(f"      ✓ Already downloaded, skipping...")
                return 'skipped'
            
            # For full download mode, check if video file actually exists
            # (user might have done transcript-only download before)
            sanitized_title = self.sanitize_filename(video_title)
            video_path = lesson_folder / f"{sanitized_title}.mp4"
            
            if video_path.exists():
                print(f"      ✓ Video already exists, skipping...")
                return 'skipped'
            else:
                print(f"      ⚠️  Found in progress but video missing - re-downloading...")
        
        try:
            # Temporarily change download directory
            original_download_dir = self.download_dir
            self.download_dir = lesson_folder
            
            result = self.process_single_video(video_url)
            
            # Restore original download directory
            self.download_dir = original_download_dir
            
            if result.get('success'):
                print(f"      ✅ Downloaded successfully!")
                return 'downloaded'
            else:
                print(f"      ❌ Download failed: {result.get('error', 'Unknown error')}")
                return 'failed'
        
        except Exception as e:
            print(f"      ❌ Error: {str(e)}")
            return 'failed'
    
    def download_course(self, course_structure_file, course_name="Course"):
        """Download entire course with chapter-based folder organization"""
        self.course_name = course_name
        
        mode_text = "TRANSCRIPT EXTRACTOR" if self.transcript_only else "COURSE DOWNLOADER"
        print("=" * 80)
        print(f"🎓 O'REILLY {mode_text} - {course_name}")
        print("=" * 80)
        
        if self.transcript_only:
            print("📝 Transcript-only mode: Skipping video downloads")
        
        # Load course structure
        total_videos = self.load_course_structure(course_structure_file)
        
        # Create course folder
        course_folder = self.download_dir / self.sanitize_folder_name(course_name)
        course_folder.mkdir(exist_ok=True)
        print(f"\n📁 Course folder: {course_folder}")
        
        # Setup driver and login
        self.setup_driver()
        self.driver.get(self.BASE_URL)
        time.sleep(3)
        
        if "Sign In" not in self.driver.page_source:
            print("\n✓ Already logged in! (Using saved profile)")
        else:
            print("\n🔐 Logging in to O'Reilly...")
            self.login()
        
        # Download statistics
        stats = {'downloaded': 0, 'failed': 0, 'skipped': 0}
        module_count = 0
        
        # Process each module
        for module_name, lessons in self.course_structure.items():
            module_count += 1
            
            # Skip unknown modules if there are valid ones
            is_quiz, is_unknown = self._should_skip_item("", module_name)
            if is_unknown and len(self.course_structure) > 1:
                continue
            
            print(f"\n{'=' * 80}")
            print(f"📦 MODULE {module_count}: {module_name}")
            print(f"{'=' * 80}")
            
            # Create module folder
            module_folder_name = f"{module_count:02d} - {self.sanitize_folder_name(module_name)}"
            module_folder = course_folder / module_folder_name
            module_folder.mkdir(exist_ok=True)
            
            lesson_count = 0
            
            # Process each lesson
            for lesson_name, videos in lessons.items():
                lesson_count += 1
                
                # Skip unknown lessons if there are valid ones
                is_quiz, is_unknown = self._should_skip_item("", lesson_name)
                if is_unknown and len(lessons) > 1:
                    continue
                
                print(f"\n  📖 LESSON {lesson_count}: {lesson_name}")
                
                # Create lesson folder
                lesson_folder_name = f"{lesson_count:02d} - {self.sanitize_folder_name(lesson_name)}"
                lesson_folder = module_folder / lesson_folder_name
                lesson_folder.mkdir(exist_ok=True)
                
                video_count = 0
                
                # Process each video
                for video_item in videos:
                    video_url = video_item['url']
                    video_title = video_item['title']
                    
                    # Skip quizzes and continue links
                    is_quiz, _ = self._should_skip_item(video_url, "")
                    if is_quiz:
                        print(f"    ⏭️  Skipping: {video_title} (quiz/continue link)")
                        stats['skipped'] += 1
                        continue
                    
                    video_count += 1
                    print(f"\n    🎥 Video {video_count}: {video_title}")
                    
                    # Download video
                    result = self._download_video_item(video_url, video_title, lesson_folder)
                    stats[result] += 1
                    
                    # Small delay between videos
                    time.sleep(2)
        
        # Final summary
        self._print_course_summary(stats, course_folder)
        self.cleanup()
    def _print_course_summary(self, stats, course_folder):
        """Print final course download summary"""
        mode_text = "TRANSCRIPT EXTRACTION" if self.transcript_only else "COURSE DOWNLOAD"
        print("\n" + "=" * 80)
        print(f"📊 {mode_text} COMPLETE")
        print("=" * 80)
        print(f"✅ Successfully processed: {stats['downloaded']} items")
        print(f"❌ Failed: {stats['failed']} items")
        print(f"⏭️  Skipped: {stats['skipped']} items (quizzes/already downloaded)")
        print(f"📁 Location: {course_folder}")
        print("=" * 80)


def extract_course_structure_from_url(course_url, output_file="course_structure.json", headless=True):
    """Extract course structure by expanding sections and parsing DOM"""
    print("=" * 80)
    print("🔍 COURSE STRUCTURE EXTRACTOR")
    print("=" * 80)
    print(f"\n📚 Course URL: {course_url}")
    print(f"📄 Output file: {output_file}\n")
    
    extractor = OReillyCourseDownloader(headless=headless)
    
    try:
        extractor.setup_driver()
        
        # Login
        extractor.driver.get(extractor.BASE_URL)
        time.sleep(3)
        
        if "Sign In" not in extractor.driver.page_source:
            print("✓ Already logged in!\n")
        else:
            print("🔐 Logging in...\n")
            extractor.login()
        
        # Navigate to course page
        print(f"📖 Opening course page...")
        extractor.driver.get(course_url)
        time.sleep(5)
        
        # Expand all collapsed sections
        expand_buttons = extractor.driver.find_elements(
            By.CSS_SELECTOR, 'button[aria-expanded="false"]'
        )
        total_buttons = len(expand_buttons)
        
        print("⏳ Expanding all sections (this may take 10-20 seconds)...")
        print(f"   Found {total_buttons} collapsed sections")
        
        if total_buttons > 0:
            print("   Expanding sections...")
            for i, button in enumerate(expand_buttons, 1):
                try:
                    button.click()
                    time.sleep(0.1)
                    
                    if i % 10 == 0:
                        print(f"   ✓ Expanded {i}/{total_buttons} sections...")
                except Exception:
                    pass
            
            print(f"   ✅ All {total_buttons} sections expanded!")
            time.sleep(2)
        else:
            print("   ✓ All sections already expanded")
        
        # Extract structure using JavaScript
        print("📊 Extracting course structure...")
        structure = extractor.driver.execute_script(_get_extraction_script())
        
        # Count videos
        total_videos = extractor._count_videos_in_structure(structure)
        
        print(f"   ✓ Found {len(structure)} modules")
        print(f"   ✓ Found {total_videos} videos")
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(structure, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Course structure saved to: {output_file}")
        print("\n" + "=" * 80)
        print("✅ EXTRACTION COMPLETE!")
        print("=" * 80)
        print(f"\nNext step: Download the course with:")
        print(f'  python oreilly_course_downloader.py --structure {output_file} --name "Your Course Name"')
        
    except Exception as e:
        print(f"\n❌ Error extracting structure: {e}")
        traceback.print_exc()
    finally:
        extractor.cleanup()


def _get_extraction_script():
    """Get JavaScript code for extracting course structure"""
    return """
        // Helper function to clean module/lesson names
        function cleanName(text) {
            // Remove timing suffixes like "28m", "1m", "42m", etc.
            return text.replace(/\\d+[smh](\\s+\\d+[sm])?\\s*$/, '').trim();
        }
        
        // Find all video links
        const allVideoLinks = document.querySelectorAll('a[href*="/videos/"][href*="/9780"]');
        
        // Extract structured data
        const courseStructure = [];
        let currentModule = "Unknown Module";
        let currentLesson = "Unknown Lesson";
        
        allVideoLinks.forEach(link => {
            const url = link.href;
            const title = link.textContent.trim();
            
            // Look for heading ancestors
            let tempParent = link.parentElement;
            let moduleFound = false;
            let lessonFound = false;
            
            // Walk up the DOM tree to find section headers
            for (let i = 0; i < 10 && tempParent; i++) {
                const prevElements = Array.from(tempParent.parentElement?.children || []);
                const currentIndex = prevElements.indexOf(tempParent);
                
                for (let j = currentIndex - 1; j >= 0; j--) {
                    const elem = prevElements[j];
                    const heading = elem.querySelector('h2, h3, h4, h5') || 
                                   (elem.tagName.match(/H[2-5]/) ? elem : null);
                    
                    if (heading) {
                        const headingText = cleanName(heading.textContent.trim());
                        
                        if (headingText.toLowerCase().includes('module') && !moduleFound) {
                            currentModule = headingText;
                            moduleFound = true;
                        } else if (headingText.toLowerCase().includes('lesson') && !lessonFound) {
                            currentLesson = headingText;
                            lessonFound = true;
                        }
                    }
                }
                
                tempParent = tempParent.parentElement;
            }
            
            courseStructure.push({
                module: currentModule,
                lesson: currentLesson,
                title: title,
                url: url
            });
        });
        
        // Group by module and lesson
        const organized = {};
        
        courseStructure.forEach(item => {
            if (!organized[item.module]) {
                organized[item.module] = {};
            }
            if (!organized[item.module][item.lesson]) {
                organized[item.module][item.lesson] = [];
            }
            organized[item.module][item.lesson].push({
                title: item.title,
                url: item.url
            });
        });
        
        return organized;
    """


def _is_profile_exists():
    """Check if Chrome profile exists with saved login"""
    return PROFILE_DIR.exists() and any(PROFILE_DIR.iterdir())


def _generate_structure_filename(course_url):
    """Generate unique structure filename from course URL"""
    url_hash = hashlib.md5(course_url.encode()).hexdigest()[:8]
    return f"course_structure_{url_hash}.json"


def _extract_course_name_from_url(course_url):
    """Extract and format course name from URL"""
    match = re.search(COURSE_URL_PATTERN, course_url)
    if match:
        return match.group(1).replace('-', ' ').title()
    return DEFAULT_COURSE_NAME


def reset_chrome_profile():
    """Delete Chrome profile directory to force re-login"""
    if PROFILE_DIR.exists():
        print("🗑️  Deleting Chrome profile...")
        try:
            shutil.rmtree(PROFILE_DIR)
            print("✅ Chrome profile deleted successfully!")
            print("   You will need to login again on next run.")
        except Exception as e:
            print(f"❌ Error deleting profile: {e}")
    else:
        print("ℹ️  No Chrome profile found to delete.")


def parse_arguments():
    """Parse and validate command line arguments"""
    parser = argparse.ArgumentParser(
        description="Download complete O'Reilly courses organized by chapters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download complete course (auto-extracts structure):
  python oreilly_course_downloader.py \\
    --url "https://learning.oreilly.com/course/aws-certified-cloud/9780138314934/" \\
    --email "your@email.com" \\
    --password "yourpassword"
  
  # Download transcripts only (no videos):
  python oreilly_course_downloader.py \\
    --url "https://learning.oreilly.com/course/aws-certified-cloud/9780138314934/" \\
    --email "your@email.com" \\
    --password "yourpassword" \\
    --transcript-only
  
  # Show browser window (debugging):
  python oreilly_course_downloader.py \\
    --url "COURSE_URL" \\
    --email "your@email.com" \\
    --password "yourpassword" \\
    --no-headless
  
  # Custom course name:
  python oreilly_course_downloader.py \\
    --url "COURSE_URL" \\
    --name "My Custom Course Name" \\
    --email "your@email.com" \\
    --password "yourpassword"
  
  # Reset Chrome profile (force re-login):
  python oreilly_course_downloader.py --reset-profile
  
  Note: After first login, credentials are saved in Chrome profile.
        Structure extraction happens automatically in the background.
        """
    )
    
    # Main action flags (mutually exclusive)
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        '--url',
        type=str,
        metavar='COURSE_URL',
        help='O\'Reilly course URL to download'
    )
    action_group.add_argument(
        '--reset-profile',
        action='store_true',
        help='Delete Chrome profile to force re-login'
    )
    
    # Download options
    parser.add_argument(
        '--name',
        type=str,
        help='Course name for folder organization (auto-detected if not provided)'
    )
    parser.add_argument(
        '--email',
        type=str,
        help='O\'Reilly account email (only required for first-time login, saved in Chrome profile)'
    )
    parser.add_argument(
        '--password',
        type=str,
        help='O\'Reilly account password (only required for first-time login, saved in Chrome profile)'
    )
    parser.add_argument(
        '--transcript-only',
        action='store_true',
        help='Only download transcripts, skip video files'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='Run browser in headless mode (default: True, use --no-headless to show browser)'
    )
    parser.add_argument(
        '--no-headless',
        dest='headless',
        action='store_false',
        help='Show browser window (useful for debugging)'
    )
    
    return parser.parse_args()
def _validate_first_time_login(args):
    """Validate credentials for first-time login"""
    if not _is_profile_exists() and (not args.email or not args.password):
        print("=" * 80)
        print("❌ FIRST-TIME LOGIN REQUIRED")
        print("=" * 80)
        print("\n📧 Email and password are required for first-time login.")
        print("After successful login, credentials will be saved in Chrome profile.")
        print("\nUsage:")
        print('  python oreilly_course_downloader.py \\')
        print('    --url "COURSE_URL" \\')
        print('    --email "your@email.com" \\')
        print('    --password "yourpassword"')
        print("\n💡 Next time you won't need to provide credentials!")
        print("=" * 80)
        return False
    elif _is_profile_exists():
        print("✓ Using saved login from Chrome profile")
    return True


def main():
    """Main entry point for course downloader"""
    args = parse_arguments()
    
    # Handle reset profile
    if args.reset_profile:
        reset_chrome_profile()
        return
    
    # Validate credentials for first-time login
    if args.url and not _validate_first_time_login(args):
        return
    
    # Main workflow: Extract + Download in one go
    if args.url:
        print("=" * 80)
        print("🎓 O'REILLY COURSE DOWNLOADER - ONE-STEP WORKFLOW")
        print("=" * 80)
        
        # Auto-generate structure filename and course name
        structure_file = _generate_structure_filename(args.url)
        course_name = args.name or _extract_course_name_from_url(args.url)
        
        print(f"\n📚 Course: {course_name}")
        print(f"🔗 URL: {args.url}")
        print(f"📝 Mode: {'Transcript-only' if args.transcript_only else 'Full download (videos + transcripts)'}")
        print(f"🌐 Browser: {'Headless' if args.headless else 'Visible'}")
        
        # Step 1: Extract structure (automatic, in background)
        print("\n" + "=" * 80)
        print("📊 STEP 1/2: EXTRACTING COURSE STRUCTURE")
        print("=" * 80)
        print("⏳ This may take 10-30 seconds...")
        
        try:
            extract_course_structure_from_url(args.url, structure_file, headless=args.headless)
        except Exception as e:
            print(f"\n❌ Failed to extract course structure: {e}")
            print("Please check the course URL and try again.")
            return
        
        # Step 2: Download course
        print("\n" + "=" * 80)
        print("📥 STEP 2/2: DOWNLOADING COURSE")
        print("=" * 80)
        
        try:
            downloader = OReillyCourseDownloader(
                email=args.email,
                password=args.password,
                transcript_only=args.transcript_only,
                headless=args.headless
            )
            downloader.download_course(
                course_structure_file=structure_file,
                course_name=course_name
            )
            
            # Cleanup structure file (optional, keep for debugging)
            # Path(structure_file).unlink(missing_ok=True)
            
        except Exception as e:
            print(f"\n❌ Download failed: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
