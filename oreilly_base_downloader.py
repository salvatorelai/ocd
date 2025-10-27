"""
O'Reilly Course Downloader - Base Class
Provides core functionality for downloading videos and transcripts
Designed for complete course downloads only - Use oreilly_course_downloader.py
"""

import os
import sys
import json
import time
import subprocess
import threading
import traceback
import re
from pathlib import Path
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
except ImportError:
    print("❌ Selenium not installed!")
    print("Install with: pip install selenium")
    sys.exit(1)


class OReillyDownloader:
    """
    Base O'Reilly downloader with Selenium automation.
    Provides core functionality for course downloads:
    - Chrome setup and login management
    - Video URL capture from m3u8 streams
    - Transcript extraction
    - Video downloads via FFmpeg
    
    NOTE: This class is designed for course downloads only.
    Use OReillyCourseDownloader for full course downloads.
    """
    
    # Class constants
    BASE_URL = "https://learning.oreilly.com"
    LOGIN_URL = f"{BASE_URL}/accounts/login/"
    SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    def __init__(self, email, password, download_dir="downloads", transcript_only=False, headless=True):
        self.email = email
        self.password = password
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.progress_file = Path("download_progress.json")
        self.profile_dir = Path("chrome_profile")
        self.profile_dir.mkdir(exist_ok=True)
        self.driver = None
        self.transcript_only = transcript_only
        self.headless = headless
        
    def _configure_chrome_options(self):
        """Configure Chrome options for headless automation"""
        options = Options()
        
        # Persistent profile for saved login
        profile_path = str(self.profile_dir.absolute())
        options.add_argument(f'--user-data-dir={profile_path}')
        options.add_argument('--profile-directory=Default')
        
        # Headless mode configuration (conditional)
        if self.headless:
            options.add_argument('--headless=new')
            options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Suppress logs and warnings
        log_suppression_flags = [
            '--log-level=3',
            '--silent',
            '--disable-logging',
            '--disable-gpu',
            '--disable-webgl',
            '--disable-software-rasterizer',
            '--disable-dev-shm-usage',
            '--no-sandbox'
        ]
        for flag in log_suppression_flags:
            options.add_argument(flag)
        
        # Experimental options
        options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Performance logging for network requests
        options.set_capability('goog:loggingPrefs', {
            'performance': 'ALL',
            'browser': 'OFF',
            'driver': 'OFF'
        })
        
        return options
    
    def setup_driver(self):
        """Setup Chrome driver with required options"""
        print("🚀 Setting up Chrome driver...")
        print(f"   📁 Using profile: {self.profile_dir.absolute()}")
        print(f"   🌐 Mode: {'Headless' if self.headless else 'Visible Browser'}")
        
        # Suppress webdriver-manager logs
        os.environ['WDM_LOG'] = '0'
        
        options = self._configure_chrome_options()
        self.driver = webdriver.Chrome(options=options)
        
        # Hide webdriver detection
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        
        print("✓ Driver setup complete")
        print("✓ Chrome profile will save login permanently!")
        
    def _is_logged_in(self):
        """Check if already logged in"""
        current_url = self.driver.current_url
        return "login" not in current_url.lower() and "signin" not in current_url.lower()
    
    def _perform_login_steps(self):
        """Perform the two-step login process"""
        # Step 1: Enter email
        email_field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        email_field.clear()
        email_field.send_keys(self.email)
        print(f"  ✓ Entered email: {self.email}")
        
        # Click Continue button
        continue_btn = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='EmailSubmit']"))
        )
        continue_btn.click()
        print("  ✓ Clicked Continue button")
        time.sleep(3)
        
        # Step 2: Enter password
        password_field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        password_field.clear()
        password_field.send_keys(self.password)
        print("  ✓ Entered password")
        
        # Click sign in button
        sign_in_btn = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='SignInBtn']"))
        )
        sign_in_btn.click()
        print("  ✓ Clicked sign in button")
        time.sleep(5)
    
    def login(self):
        """Login to O'Reilly"""
        print("\n🔐 Checking O'Reilly login status...")
        
        # Navigate to O'Reilly homepage
        self.driver.get(self.BASE_URL)
        time.sleep(3)
        
        # Check if already logged in
        if self._is_logged_in():
            print("✓ Already logged in! (Using saved profile)")
            print("✓ No need to enter credentials again!")
            return True
        
        # Need to login
        print("  Need to perform login...")
        self.driver.get(self.LOGIN_URL)
        time.sleep(3)
        
        try:
            self._perform_login_steps()
            
            # Verify login success
            if self._is_logged_in():
                print("✓ Login successful!")
                print("✓ Login saved to Chrome profile - won't need to login again!")
                return True
            else:
                print("❌ Login failed! Check credentials")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            traceback.print_exc()
            return False
    
    def _inject_url_capturer(self):
        """Inject JavaScript to intercept m3u8 URLs"""
        script = """
        (function() {
            if (window._urlCapturerInjected) return;
            window._urlCapturerInjected = true;
            window._capturedUrls = [];
            
            // Intercept fetch requests
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
                const url = typeof args[0] === 'string' ? args[0] : args[0].url;
                if (url && url.includes('.m3u8')) {
                    window._capturedUrls.push(url);
                }
                return originalFetch.apply(this, args);
            };
            
            // Intercept XHR requests
            const originalXHROpen = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(method, url) {
                if (url && url.includes('.m3u8')) {
                    window._capturedUrls.push(url);
                }
                return originalXHROpen.apply(this, arguments);
            };
        })();
        """
        self.driver.execute_script(script)
    
    def _get_captured_urls(self):
        """Get URLs captured by injected JavaScript"""
        try:
            urls = self.driver.execute_script("return window._capturedUrls || [];")
            return list(set(urls))  # Remove duplicates
        except:
            return []
    
    def _get_urls_from_performance_logs(self):
        """Extract m3u8 URLs from Chrome performance logs"""
        try:
            logs = self.driver.get_log('performance')
            urls = set()
            
            for log in logs:
                try:
                    message = json.loads(log['message'])
                    method = message['message']['method']
                    
                    if method in ('Network.requestWillBeSent', 'Network.responseReceived'):
                        params = message['message'].get('params', {})
                        url = (params.get('request', {}).get('url') or 
                               params.get('response', {}).get('url'))
                        
                        if url and '.m3u8' in url:
                            urls.add(url)
                except:
                    continue
            
            return list(urls)
        except:
            return []
    
    def capture_video_url(self, video_url, timeout=45):
        """Navigate to video page and capture m3u8 URL"""
        print(f"\n📹 Processing: {video_url}")
        
        try:
            # Navigate to video page
            self.driver.get(video_url)
            print("  ✓ Page loaded")
            time.sleep(5)
            
            # Inject URL capturer before video plays
            self._inject_url_capturer()
            print("  ✓ URL capturer injected")
            
            # Wait for video player
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "video"))
                )
                print("  ✓ Video player found")
            except:
                print("  ⚠️  Video player not found yet...")
            
            # Wait for m3u8 URL to be captured
            print("  ⏳ Waiting for m3u8 URL...")
            start_time = time.time()
            check_count = 0
            
            while time.time() - start_time < timeout:
                check_count += 1
                
                # Try both capture methods
                urls = self._get_captured_urls() or self._get_urls_from_performance_logs()
                
                if urls:
                    print(f"  ✅ Captured URL after {check_count} checks!")
                    print(f"     {urls[0][:100]}...")
                    return urls[0]
                
                # Progress update every 5 seconds
                if check_count % 5 == 0:
                    elapsed = int(time.time() - start_time)
                    print(f"     Still waiting... ({elapsed}s elapsed)")
                
                time.sleep(1)
            
            print(f"  ❌ Failed to capture video URL (timeout after {timeout}s)")
            return None
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            traceback.print_exc()
            return None
    
    def _find_transcript_container(self):
        """Locate transcript container using multiple selectors"""
        # Scroll to load transcript section
        print("    ⏬ Scrolling to transcript section...")
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(2)
        
        # Try primary selector
        try:
            container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='transcript']"))
            )
            print("    ✓ Transcript section found")
            return container
        except:
            # Try alternative selector
            try:
                container = self.driver.find_element(By.CSS_SELECTOR, "div.css-k72e9c")
                print("    ✓ Found transcript with alternative selector")
                return container
            except:
                print("    ❌ Transcript not available on this page")
                return None
    
    def _extract_transcript_entries(self, transcript_body):
        """Extract timestamp and text from transcript buttons"""
        buttons = transcript_body.find_elements(By.CSS_SELECTOR, "button")
        print(f"    ✓ Found {len(buttons)} transcript entries")
        
        if not buttons:
            return None
        
        transcript_lines = []
        for button in buttons:
            try:
                # Extract timestamp and text
                timestamp = button.find_element(
                    By.CSS_SELECTOR, "p.MuiTypography-uiBodySmall"
                ).text.strip()
                text = button.find_element(
                    By.CSS_SELECTOR, "p.MuiTypography-uiBody"
                ).text.strip()
                
                if timestamp and text:
                    transcript_lines.append(f"[{timestamp}] {text}")
            except:
                continue
        
        if transcript_lines:
            return '\n\n'.join(transcript_lines)
        return None
    
    def extract_transcript(self):
        """Extract transcript from current video page"""
        print("  📝 Extracting transcript...")
        
        try:
            # Find transcript container
            transcript_container = self._find_transcript_container()
            if not transcript_container:
                return None
            
            # Find transcript body
            try:
                transcript_body = transcript_container.find_element(
                    By.CSS_SELECTOR, "div[data-testid='transcript-body']"
                )
                print("    ✓ Transcript body found")
            except:
                print("    ⚠️  Transcript body not found")
                return None
            
            # Extract entries
            transcript = self._extract_transcript_entries(transcript_body)
            
            if transcript:
                print(f"    ✅ Transcript extracted! ({len(transcript)} chars)")
                return transcript
            else:
                print("    ⚠️  No transcript text found")
                return None
                    
        except Exception as e:
            print(f"    ⚠️  Transcript extraction failed: {e}")
            traceback.print_exc()
            return None
    
    def get_video_title(self):
        """Extract video title from current page"""
        # Title selectors in priority order
        selectors = [
            ("ID", "videoTitle"),
            ("CSS", "h2.MuiTypography-h2"),
            ("CSS", "h1"),
            ("CSS", "[data-testid='title']"),
            ("CSS", ".chapter-title"),
            ("TAG", "title")
        ]
        
        for selector_type, selector in selectors:
            try:
                if selector_type == "ID":
                    element = self.driver.find_element(By.ID, selector)
                elif selector_type == "TAG":
                    element = self.driver.find_element(By.TAG_NAME, selector)
                else:  # CSS
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                
                title = element.text or element.get_attribute("textContent")
                if title:
                    title = self.sanitize_filename(title)
                    print(f"    ✓ Got title: {title}")
                    return title
            except:
                continue
        
        return "video"
    
    def sanitize_filename(self, filename):
        """Remove invalid characters and limit filename length"""
        # Remove invalid filesystem characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Limit length
        return filename[:200].strip() if len(filename) > 200 else filename.strip()
    
    def _run_ffmpeg_with_spinner(self, cmd, output_path):
        """Run ffmpeg command with animated spinner"""
        idx = [0]
        stop_spinner = [False]
        
        def show_spinner():
            while not stop_spinner[0]:
                frame = self.SPINNER_FRAMES[idx[0] % len(self.SPINNER_FRAMES)]
                print(f"\r  ⬇️  Downloading video... {frame}", end="", flush=True)
                idx[0] += 1
                time.sleep(0.1)
        
        # Start spinner thread
        spinner_thread = threading.Thread(target=show_spinner, daemon=True)
        spinner_thread.start()
        
        # Run ffmpeg
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Stop spinner
        stop_spinner[0] = True
        time.sleep(0.15)
        
        return result
    
    def download_video(self, m3u8_url, output_name):
        """Download video using ffmpeg with progress indicator"""
        print(f"  ⬇️  Downloading video...", end="", flush=True)
        
        output_path = self.download_dir / f"{output_name}.mp4"
        
        # Check if already exists
        if output_path.exists():
            print(f"\r    ⚠️  File already exists: {output_path.name}")
            return str(output_path)
        
        try:
            cmd = [
                'ffmpeg',
                '-i', m3u8_url,
                '-c', 'copy',
                '-bsf:a', 'aac_adtstoasc',
                '-loglevel', 'error',
                '-stats',
                '-y',
                str(output_path)
            ]
            
            result = self._run_ffmpeg_with_spinner(cmd, output_path)
            
            if result.returncode == 0 and output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"\r    ✅ Downloaded: {output_path.name} ({size_mb:.1f} MB)")
                return str(output_path)
            else:
                print(f"\r    ❌ Download failed")
                if result.stderr:
                    print(f"    Error: {result.stderr[:200]}")
                return None
                
        except Exception as e:
            print(f"\r    ❌ Download error: {e}")
            return None
    
    def save_transcript(self, transcript, output_name):
        """Save transcript to text file"""
        if not transcript:
            return None
        
        output_path = self.download_dir / f"{output_name}.txt"
        
        try:
            output_path.write_text(transcript, encoding='utf-8')
            print(f"    ✓ Transcript saved: {output_path.name}")
            return str(output_path)
        except Exception as e:
            print(f"    ❌ Failed to save transcript: {e}")
            return None
    
    def save_progress(self, data):
        """Save download progress to JSON file"""
        try:
            self.progress_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except:
            pass
    
    def load_progress(self):
        """Load download progress from JSON file"""
        try:
            if self.progress_file.exists():
                return json.loads(self.progress_file.read_text(encoding='utf-8'))
        except:
            pass
        return {}
    
    def process_single_video(self, video_url):
        """
        Process a single video: capture URL, extract transcript, download.
        Used internally by OReillyCourseDownloader for course downloads.
        """
        print("\n" + "=" * 80)
        
        # Navigate to video page
        self.driver.get(video_url)
        print(f"\n📹 Processing: {video_url}")
        time.sleep(5)
        
        # Get video title while on video page
        title = self.get_video_title()
        print(f"  ✓ Video title: {title}")
        
        # Extract transcript
        transcript = self.extract_transcript()
        
        # Initialize result
        result = {
            'success': False,
            'url': video_url,
            'title': title,
            'm3u8_url': None,
            'video_path': None,
            'transcript_path': None,
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
        }
        
        # If transcript-only mode, skip video download
        if self.transcript_only:
            print(f"  📝 Transcript-only mode enabled")
            
            # Save transcript
            transcript_path = self.save_transcript(transcript, title) if transcript else None
            
            if transcript:
                print(f"  ✅ Transcript saved!")
                result['success'] = True
                result['transcript_path'] = transcript_path
            else:
                print(f"  ⚠️  No transcript available")
                result['error'] = 'No transcript found'
        else:
            # Full download mode: capture video URL and download
            m3u8_url = self.capture_video_url(video_url)
            
            if not m3u8_url:
                result['error'] = 'Failed to capture m3u8 URL'
            else:
                result['m3u8_url'] = m3u8_url
                
                # Download video
                video_path = self.download_video(m3u8_url, title)
                result['video_path'] = video_path
                
                # Save transcript
                transcript_path = self.save_transcript(transcript, title) if transcript else None
                result['transcript_path'] = transcript_path
                
                if video_path:
                    result['success'] = True
                    if transcript:
                        print(f"  ✅ Video and transcript saved!")
                    else:
                        print(f"  ✅ Video saved (no transcript available)")
                else:
                    result['error'] = 'Video download failed'
        
        # Save progress
        progress = self.load_progress()
        progress[video_url] = result
        self.save_progress(progress)
        
        return result
    
    def cleanup(self):
        """Cleanup and close browser"""
        if self.driver:
            self.driver.quit()
            print("\n✓ Browser closed")


# This module provides the base class for course downloads
# Use oreilly_course_downloader.py for complete course downloads
if __name__ == "__main__":
    print("=" * 80)
    print("🎓 O'REILLY COURSE DOWNLOADER - BASE CLASS")
    print("=" * 80)
    print("\n⚠️  This is the base class module.")
    print("For complete course downloads, use:")
    print("\n  python oreilly_course_downloader.py --help")
    print("\nExamples:")
    print("  # Extract course structure:")
    print('  python oreilly_course_downloader.py --extract "COURSE_URL"')
    print("\n  # Download course:")
    print('  python oreilly_course_downloader.py --structure course.json --name "Course Name"')
    print("\n  # Download transcripts only:")
    print('  python oreilly_course_downloader.py --structure course.json --name "Course Name" --transcript-only')
    print("\n" + "=" * 80)
