import instaloader
import json
import sys
import os
import argparse
from datetime import datetime

# --- CONFIGURATION ---
# The Instagram account you created the session for
SESSION_USER = "portalrecruit" 

def get_player_intel(target_username, max_posts=15):
    """
    Scrapes a specific Instagram profile using a pre-authorized session.
    Outputs a highly structured JSON object optimized for LLM analysis.
    """
    
    # 1. Initialize Instaloader
    # strict_limiting=False speeds it up, but be careful. 
    # For a few profiles, it's fine. For bulk, set to True.
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False, 
        download_video_thumbnails=False,
        compress_json=False
    )

    # 2. Load the Session (Crucial Step)
    try:
        print(f"🔓 Loading session for '{SESSION_USER}'...")
        L.load_session_from_file(SESSION_USER)
    except FileNotFoundError:
        print(f"❌ Error: Session file for '{SESSION_USER}' not found.")
        print("   Make sure you have run your cookie generator script and the session file exists.")
        sys.exit(1)

    # 3. Connect to the Target Profile
    try:
        print(f"🔍 Fetching profile: @{target_username}...")
        profile = instaloader.Profile.from_username(L.context, target_username)
    except instaloader.ProfileNotExistsException:
        return {"error": "Profile not found"}
    except instaloader.ConnectionException as e:
        return {"error": f"Connection failed: {e}"}

    # 4. Extract High-Level Profile Data (The "Bio Check")
    intel_packet = {
        "meta": {
            "scraped_at": datetime.now().isoformat(),
            "target_handle": target_username
        },
        "profile_summary": {
            "full_name": profile.full_name,
            "biography": profile.biography,
            "followers": profile.followers,
            "following": profile.followees,
            "is_verified": profile.is_verified,
            "is_private": profile.is_private,
            "external_url": profile.external_url, # Often links to Highlight tapes or recruiting profiles
        },
        "recent_content": []
    }

    # If private, we can't get posts unless we follow them. 
    # The LLM needs to know this to generate a specific "Private Profile" report.
    if profile.is_private and not profile.followed_by_viewer:
        intel_packet["profile_summary"]["access_status"] = "PRIVATE_LOCKED"
        return intel_packet

    intel_packet["profile_summary"]["access_status"] = "PUBLIC"

    # 5. Extract Post Data (The "Vibe Check")
    # We limit to 'max_posts' to keep it fast and machine-readable.
    print(f"📥 Extracting last {max_posts} posts...")
    
    count = 0
    for post in profile.get_posts():
        if count >= max_posts:
            break
            
        post_data = {
            "date": post.date_local.isoformat(),
            "caption": post.caption if post.caption else "",
            "likes_count": post.likes,
            "comments_count": post.comments,
            "is_video": post.is_video,
            "location": post.location.name if post.location else None,
            "tagged_users": sorted(post.tagged_users) if post.tagged_users else [], # Good for finding teammates
            "hashtags": sorted(post.caption_hashtags) # Good for finding camps/circuits (e.g., #EYBL)
        }
        
        intel_packet["recent_content"].append(post_data)
        count += 1

    return intel_packet

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Instagram Intelligence for ML Ingestion")
    parser.add_argument("username", help="Target Instagram handle (without @)")
    parser.add_argument("--out", help="Output file path (optional)", default=None)
    
    args = parser.parse_args()

    # Run the scraper
    data = get_player_intel(args.username)

    # Handle Output
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"✅ Intel saved to {args.out}")
    else:
        # Print to STDOUT for piping into other scripts
        print(json.dumps(data, indent=4, ensure_ascii=False))
