#!/usr/bin/env python3
"""
Monitor an RSS feed for new entries.
Compares current feed entries with previously stored entries and detects new content.
"""

import os
import sys
import json
import hashlib
import requests
import feedparser
from datetime import datetime
from pathlib import Path
import re


def safe_github_output(key, value):
    """Safely write to GitHub Actions output, escaping special characters."""
    if not value:
        value = ""
    
    # Replace problematic characters
    safe_value = str(value).replace('\n', ' ').replace('\r', ' ')
    # Replace bullet points with dashes for better compatibility
    safe_value = safe_value.replace('•', '-').replace('…', '...')
    # Remove any other non-ASCII characters that might cause issues
    safe_value = ''.join(char if ord(char) < 128 else '?' for char in safe_value)
    
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write(f"{key}={safe_value}\n")


def fetch_rss_feed(url):
    """Fetch and parse RSS feed."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Try to parse as RSS/Atom feed
        feed = feedparser.parse(response.content)
        
        if feed.bozo and feed.bozo_exception:
            print(f"Warning: Feed parsing issues: {feed.bozo_exception}")
        
        return feed
    except requests.RequestException as e:
        print(f"Error fetching RSS feed: {e}")
        return None
    except Exception as e:
        print(f"Error parsing RSS feed: {e}")
        return None


def strip_html_and_markdown(text):
    """Strip HTML tags and basic markdown formatting from text."""
    if not text:
        return ""
    
    # First, try to parse HTML and extract text
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()
    except ImportError:
        # Fallback: manual HTML tag removal
        text = re.sub(r'<[^>]+>', '', text)
    
    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
    text = re.sub(r'__(.*?)__', r'\1', text)      # Bold
    text = re.sub(r'_(.*?)_', r'\1', text)        # Italic
    text = re.sub(r'`(.*?)`', r'\1', text)        # Code
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
    text = re.sub(r'#{1,6}\s*', '', text)         # Headers
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # List items
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # Numbered lists
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def extract_feed_entries(feed, feed_index=0):
    """Extract relevant data from feed entries."""
    entries = []
    
    for entry in feed.entries:
        # Create a unique identifier for the entry
        entry_id = getattr(entry, 'id', getattr(entry, 'link', ''))
        title = getattr(entry, 'title', 'No title')
        link = getattr(entry, 'link', '')
        published = getattr(entry, 'published', getattr(entry, 'updated', ''))
        
        # Extract full content - try multiple content fields including content:encoded
        raw_content = ""
        content_candidates = [
            getattr(entry, 'content_encoded', ''),  # content:encoded field
            getattr(entry, 'content', []),  # Full content (usually a list)
            getattr(entry, 'description', ''),  # Description field
            getattr(entry, 'summary', '')  # Summary fallback
        ]
        
        # Try to get the fullest content available
        for candidate in content_candidates:
            if isinstance(candidate, list) and candidate:
                # Content is often a list of dictionaries with 'value' key
                raw_content = candidate[0].get('value', '') if candidate[0] else ''
                if raw_content:
                    break
            elif isinstance(candidate, str) and candidate:
                raw_content = candidate
                if len(raw_content) > 200:  # Prefer longer content
                    break
        
        # Clean the content by stripping HTML and markdown
        clean_content = strip_html_and_markdown(raw_content)
        
        # Create content hash for change detection
        content_to_hash = f"{title}{link}{clean_content}"
        content_hash = hashlib.sha256(content_to_hash.encode()).hexdigest()
        
        entry_data = {
            "id": entry_id,
            "title": title,
            "link": link,
            "published": published,
            "content": clean_content,  # Full cleaned content instead of summary
            "content_hash": content_hash,
            "feed_index": feed_index  # Track which feed this entry came from
        }
        
        entries.append(entry_data)
    
    return entries


def compare_feed_entries(old_entries, new_entries):
    """Compare old and new feed entries to find new entries only.
    Since RSS entries are only added (never modified), we only track new entries.
    """
    changes = {
        "new_entries": [],
        "total_new": 0,
        "cleanup_analysis": analyze_entries_for_cleanup(old_entries, new_entries)
    }
    
    # Create lookup dictionary for old entries
    old_entries_dict = {entry["id"]: entry for entry in old_entries if "id" in entry}
    
    for new_entry in new_entries:
        entry_id = new_entry.get("id", "")
        
        if not entry_id:
            continue
        
        if entry_id not in old_entries_dict:
            # New entry - add timestamp
            new_entry["detected_date"] = datetime.now().isoformat()
            changes["new_entries"].append(new_entry)
            changes["total_new"] += 1
    
    return changes


def analyze_entries_for_cleanup(old_entries, new_entries):
    """Analyze RSS entries for cleanup opportunities."""
    cleanup_info = {
        "total_entries": len(new_entries),
        "total_stored": len(old_entries),
        "entry_growth": len(new_entries) - len(old_entries),
        "oldest_entries": [],
        "entry_age_distribution": {
            "last_week": 0,
            "last_month": 0,
            "last_quarter": 0,
            "older": 0
        }
    }
    
    # Analyze entry ages
    now = datetime.now()
    entry_info = []
    
    for entry in new_entries:
        # Try to get published date
        published = entry.get("published", "")
        days_old = 0
        
        if published:
            try:
                # Try different date formats
                for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%a, %d %b %Y %H:%M:%S %Z"]:
                    try:
                        entry_date = datetime.strptime(published, fmt)
                        days_old = (now - entry_date).days
                        break
                    except ValueError:
                        continue
            except (ValueError, TypeError):
                days_old = 0
        
        entry_info.append({
            "id": entry.get("id", ""),
            "title": entry.get("title", "")[:50],
            "days_old": days_old
        })
        
        # Categorize by age
        if days_old <= 7:
            cleanup_info["entry_age_distribution"]["last_week"] += 1
        elif days_old <= 30:
            cleanup_info["entry_age_distribution"]["last_month"] += 1
        elif days_old <= 90:
            cleanup_info["entry_age_distribution"]["last_quarter"] += 1
        else:
            cleanup_info["entry_age_distribution"]["older"] += 1
    
    # Find oldest entries (candidates for cleanup)
    entry_info.sort(key=lambda x: x["days_old"], reverse=True)
    cleanup_info["oldest_entries"] = entry_info[:10]  # Top 10 oldest
    
    return cleanup_info


def create_changes_summary(changes):
    """Create a human-readable summary of changes."""
    summary_parts = []
    
    if changes["total_new"] > 0:
        summary_parts.append(f"📰 New RSS entries ({changes['total_new']})")
        
        # List first few new entries
        for i, entry in enumerate(changes["new_entries"][:3]):
            summary_parts.append(f"  • {entry.get('title', 'No title')}")
        
        if len(changes["new_entries"]) > 3:
            summary_parts.append(f"  • ... and {len(changes['new_entries']) - 3} more")
    
    # Add cleanup analysis to summary
    cleanup = changes.get("cleanup_analysis", {})
    if cleanup:
        summary_parts.append(f"🧹 Storage: {cleanup['total_entries']} entries total, " +
                           f"{cleanup['entry_growth']} new this run")
    
    return "\n".join(summary_parts)


def main():
    rss_feeds_json = os.getenv('RSS_FEEDS')
    local_content_dir = os.getenv('LOCAL_CONTENT_DIR')
    
    if not all([rss_feeds_json, local_content_dir]):
        print("Error: Missing required environment variables")
        sys.exit(1)
    
    # Parse RSS feeds array
    try:
        rss_feeds = json.loads(rss_feeds_json)
        if not isinstance(rss_feeds, list):
            raise ValueError("RSS_FEEDS must be a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error: Invalid RSS_FEEDS format: {e}")
        sys.exit(1)
    
    print(f"Monitoring {len(rss_feeds)} RSS feeds")
    
    all_changes_detected = False
    all_summaries = []
    
    # Process each RSS feed separately
    for feed_index, rss_feed_url in enumerate(rss_feeds):
        print(f"\n--- Processing Feed {feed_index + 1}/{len(rss_feeds)}: {rss_feed_url} ---")
        
        # Fetch current RSS feed
        feed = fetch_rss_feed(rss_feed_url)
        
        if not feed:
            print(f"Error: Could not fetch RSS feed {feed_index + 1}")
            continue
        
        # Extract entries with feed index
        current_entries = extract_feed_entries(feed, feed_index)
        
        if not current_entries:
            print(f"Warning: No entries found in RSS feed {feed_index + 1}")
            continue
        
        # Create separate directory for each feed
        feed_dir = Path(local_content_dir) / "rss-content" / f"feed-{feed_index}"
        feed_dir.mkdir(parents=True, exist_ok=True)
        
        # Load previous entries for this specific feed
        feed_entries_file = feed_dir / "feed_entries.json"
        previous_entries = []
        
        if feed_entries_file.exists():
            try:
                with open(feed_entries_file, 'r') as f:
                    previous_entries = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load previous entries for feed {feed_index + 1}: {e}")
        
        # Compare entries
        changes = compare_feed_entries(previous_entries, current_entries)
        
        # Determine if there are significant changes for this feed
        has_changes = changes["total_new"] > 0
        
        if has_changes:
            all_changes_detected = True
        
        # Create summary for this feed
        changes_summary = create_changes_summary(changes) if has_changes else ""
        if changes_summary:
            feed_summary = f"Feed {feed_index + 1} ({rss_feed_url}):\n{changes_summary}"
            all_summaries.append(feed_summary)
        
        # Save current entries for this feed
        with open(feed_entries_file, 'w') as f:
            json.dump(current_entries, f, indent=2)
        
        # Save detailed changes for this feed
        changes_file = feed_dir / "latest_changes.json"
        with open(changes_file, 'w') as f:
            json.dump(changes, f, indent=2)
        
        # Save feed metadata
        metadata = {
            "feed_title": getattr(feed.feed, 'title', 'Unknown'),
            "feed_link": getattr(feed.feed, 'link', ''),
            "feed_description": getattr(feed.feed, 'description', ''),
            "feed_url": rss_feed_url,
            "feed_index": feed_index,
            "last_updated": datetime.now().isoformat(),
            "total_entries": len(current_entries)
        }
        
        metadata_file = feed_dir / "feed_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        if has_changes:
            print(f"✅ RSS feed {feed_index + 1} changes detected!")
            print(changes_summary)
        else:
            print(f"✅ No significant changes in RSS feed {feed_index + 1}")
    
    # Create combined summary
    combined_summary = "\n\n".join(all_summaries) if all_summaries else ""
    
    # Set outputs for GitHub Actions
    safe_github_output("changes_detected", str(all_changes_detected).lower())
    safe_github_output("changes_summary", combined_summary)
    
    if all_changes_detected:
        print(f"\n🎉 Changes detected in {len(all_summaries)} of {len(rss_feeds)} RSS feeds!")
    else:
        print(f"\n✅ No significant changes detected in any of the {len(rss_feeds)} RSS feeds")


if __name__ == "__main__":
    main()
