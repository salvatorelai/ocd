import json
import sys

# Constants
COOKIES_FILE = "cookies.json"

try:
    import browser_cookie3
except ImportError:
    print("❌ browser_cookie3 not found!")
    print("Please install it with: pip install browser-cookie3")
    sys.exit(1)

def get_oreilly_cookies():
    """Extract cookies from Chrome/Firefox (avoiding Safari due to SIP issues)"""
    print("🔍 Scanning browsers for cookies...")
    
    # Try Chrome first
    try:
        print("   Checking Chrome...")
        cj = browser_cookie3.chrome(domain_name="oreilly.com")
        cookies = []
        for c in cj:
            cookie_data = {
                'name': c.name,
                'value': c.value,
                'domain': c.domain,
                'path': c.path
            }
            if c.secure:
                cookie_data['secure'] = True
            if c.expires:
                cookie_data['expiry'] = int(c.expires)
            cookies.append(cookie_data)
            
        if cookies:
            print("   ✓ Found cookies in Chrome")
            return cookies
    except Exception as e:
        print(f"   ⚠️  Chrome error: {e}")

    # Try Firefox next
    try:
        print("   Checking Firefox...")
        cj = browser_cookie3.firefox(domain_name="oreilly.com")
        cookies = []
        for c in cj:
            cookie_data = {
                'name': c.name,
                'value': c.value,
                'domain': c.domain,
                'path': c.path
            }
            if c.secure:
                cookie_data['secure'] = True
            if c.expires:
                cookie_data['expiry'] = int(c.expires)
            cookies.append(cookie_data)
            
        if cookies:
            print("   ✓ Found cookies in Firefox")
            return cookies
    except Exception as e:
        print(f"   ⚠️  Firefox error: {e}")

    return []

def main():
    print("🍪 O'Reilly Cookie Generator")
    print("===========================")
    
    cookies = get_oreilly_cookies()
    
    if not cookies:
        print("❌ No O'Reilly cookies found in any browser.")
        print("   Please login to learning.oreilly.com in Chrome/Firefox first.")
        sys.exit(1)
        
    print(f"✓ Found {len(cookies)} cookies")
    
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f, indent=2)
        
    print(f"✅ Cookies saved to: {COOKIES_FILE}")
    print("\nUsage with downloader:")
    print(f'  python oreilly_course_downloader.py --url "..." --cookie-file "{COOKIES_FILE}"')

if __name__ == "__main__":
    main()
