#!/usr/bin/env python3
"""
Cleanup old content files and RSS entries that are no longer needed.
This script analyzes downloaded content against age criteria and removes outdated files.
"""

import os
import sys
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path


def analyze_repo_files_for_cleanup(repo_content_path, age_threshold_days):
    """Analyze repository files for cleanup candidates."""
    files_data_file = repo_content_path / "files_data.json"
    cleanup_candidates = []
    total_files = 0
    total_size = 0
    
    if not files_data_file.exists():
        print("No repository files data found")
        return [], 0, 0
    
    try:
        with open(files_data_file, 'r') as f:
            files_data = json.load(f)
    except Exception as e:
        print(f"Error loading files data: {e}")
        return [], 0, 0
    
    cutoff_date = datetime.now() - timedelta(days=age_threshold_days)
    
    for file_path, file_info in files_data.items():
        total_files += 1
        file_size = file_info.get("size", 0)
        total_size += file_size
        
        # Check if file has an added_date
        added_date_str = file_info.get("added_date")
        if added_date_str:
            try:
                added_date = datetime.fromisoformat(added_date_str.replace('Z', '+00:00'))
                if added_date < cutoff_date:
                    cleanup_candidates.append({
                        "path": file_path,
                        "size": file_size,
                        "added_date": added_date_str,
                        "days_old": (datetime.now() - added_date).days
                    })
            except (ValueError, TypeError):
                # If date parsing fails, consider it for cleanup if very old
                cleanup_candidates.append({
                    "path": file_path,
                    "size": file_size,
                    "added_date": "unknown",
                    "days_old": "unknown"
                })
    
    return cleanup_candidates, total_files, total_size


def parse_entry_date(published, detected_date):
    """Try to parse the entry date from published or detected_date fields."""
    if published:
        date_formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%a, %d %b %Y %H:%M:%S %Z"
        ]
        for fmt in date_formats:
            try:
                return datetime.strptime(published, fmt)
            except ValueError:
                continue
    if detected_date:
        try:
            return datetime.fromisoformat(detected_date.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            pass
    return None

def analyze_rss_entries_for_cleanup(rss_content_path, age_threshold_days):
    """Analyze RSS entries for cleanup candidates."""
    entries_data_file = rss_content_path / "feed_entries.json"
    cleanup_candidates = []
    total_entries = 0

    if not entries_data_file.exists():
        print("No RSS entries data found")
        return [], 0

    try:
        with open(entries_data_file, 'r') as f:
            entries_data = json.load(f)
    except Exception as e:
        print(f"Error loading RSS entries data: {e}")
        return [], 0

    cutoff_date = datetime.now() - timedelta(days=age_threshold_days)

    for entry in entries_data:
        total_entries += 1
        published = entry.get("published", "")
        detected_date = entry.get("detected_date", "")
        entry_date = parse_entry_date(published, detected_date)

        if entry_date and entry_date < cutoff_date:
            cleanup_candidates.append({
                "id": entry.get("id", ""),
                "title": entry.get("title", "")[:50],
                "published": published,
                "detected_date": detected_date,
                "days_old": (datetime.now() - entry_date).days
            })

    return cleanup_candidates, total_entries


def _delete_file(actual_file_path, file_path, file_size, cleaned_files, total_size_freed):
    try:
        actual_file_path.unlink()
        cleaned_files.append(file_path)
        total_size_freed += file_size
    except Exception as e:
        print(f"    ❌ Error removing file: {e}")
    return total_size_freed

def _update_files_data(files_data_file, files_data):
    try:
        with open(files_data_file, 'w') as f:
            json.dump(files_data, f, indent=2)
    except Exception as e:
        print(f"Error saving updated files data: {e}")

def cleanup_repo_files(repo_content_path, repo_candidates, dry_run):
    """Helper to cleanup repository files."""
    cleaned_files = []
    total_size_freed = 0
    files_data_file = repo_content_path / "files_data.json"
    try:
        with open(files_data_file, 'r') as f:
            files_data = json.load(f)
    except Exception as e:
        print(f"Error loading files data: {e}")
        files_data = {}

    for candidate in repo_candidates:
        file_path = candidate["path"]
        file_size = candidate["size"]
        days_old = candidate["days_old"]

        print(f"  - {file_path} ({file_size:,} bytes, {days_old} days old)")

        if not dry_run:
            actual_file_path = repo_content_path / "files" / file_path
            if actual_file_path.exists():
                total_size_freed = _delete_file(actual_file_path, file_path, file_size, cleaned_files, total_size_freed)
            if file_path in files_data:
                del files_data[file_path]

    if not dry_run and cleaned_files:
        _update_files_data(files_data_file, files_data)

    return cleaned_files, total_size_freed

def cleanup_rss_entries(rss_content_path, rss_candidates, dry_run):
    """Helper to cleanup RSS entries."""
    cleaned_entries = []
    entries_data_file = rss_content_path / "feed_entries.json"
    try:
        with open(entries_data_file, 'r') as f:
            entries_data = json.load(f)
    except Exception as e:
        print(f"Error loading entries data: {e}")
        entries_data = []

    candidate_ids = {candidate["id"] for candidate in rss_candidates}

    for candidate in rss_candidates:
        print(f"  - {candidate['title']} (ID: {candidate['id']}, {candidate['days_old']} days old)")

    if not dry_run:
        updated_entries = [entry for entry in entries_data if entry.get("id", "") not in candidate_ids]
        cleaned_entries = list(candidate_ids)
        try:
            with open(entries_data_file, 'w') as f:
                json.dump(updated_entries, f, indent=2)
        except Exception as e:
            print(f"Error saving updated entries data: {e}")

    return cleaned_entries

def print_cleanup_summary(cleaned_files, cleaned_entries, total_size_freed, dry_run):
    print("\n📊 Cleanup Summary:")
    print(f"  Repository files {'would be ' if dry_run else ''}removed: {len(cleaned_files)}")
    print(f"  RSS entries {'would be ' if dry_run else ''}removed: {len(cleaned_entries)}")
    if total_size_freed > 0:
        print(f"  Disk space {'would be ' if dry_run else ''}freed: {total_size_freed:,} bytes ({total_size_freed/1024/1024:.1f} MB)")

def perform_cleanup(repo_content_path, rss_content_path, repo_candidates, rss_candidates, dry_run=True):
    """Perform the actual cleanup operations."""
    cleaned_files = []
    cleaned_entries = []
    total_size_freed = 0

    print(f"\n{'🔍 DRY RUN - ' if dry_run else '🧹 CLEANUP - '}Processing {len(repo_candidates)} repository files and {len(rss_candidates)} RSS entries")

    # Cleanup repository files
    if repo_candidates:
        print(f"\n📁 Repository files to {'would be ' if dry_run else ''}remove:")
        cleaned_files, total_size_freed = cleanup_repo_files(repo_content_path, repo_candidates, dry_run)

    # Cleanup RSS entries
    if rss_candidates:
        print(f"\n📰 RSS entries to {'would be ' if dry_run else ''}remove:")
        cleaned_entries = cleanup_rss_entries(rss_content_path, rss_candidates, dry_run)

    print_cleanup_summary(cleaned_files, cleaned_entries, total_size_freed, dry_run)

    return cleaned_files, cleaned_entries, total_size_freed


def main():
    """Main cleanup function."""
    age_threshold_days = int(os.getenv('CLEANUP_AGE_DAYS', '90'))
    dry_run = os.getenv('DRY_RUN', 'true').lower() == 'true'
    local_content_dir = os.getenv('LOCAL_CONTENT_DIR', 'monitored-content')
    
    print("🧹 Content Cleanup Analysis")
    print(f"\n   Age threshold: {age_threshold_days} days")
    print(f"\n   Mode: {'DRY RUN' if dry_run else 'ACTUAL CLEANUP'}")
    print(f"\n   Content directory: {local_content_dir}")
    
    # Set up paths
    content_path = Path(local_content_dir)
    repo_content_path = content_path / "repo-content"
    rss_content_path = content_path / "rss-content"
    
    if not content_path.exists():
        print("❌ No content directory found - nothing to cleanup")
        return
    
    # Analyze repository files
    repo_candidates, _, total_repo_size = analyze_repo_files_for_cleanup(
        repo_content_path, age_threshold_days
    )
    # Recompute total repository files for reporting since the intermediate value is intentionally ignored
    total_repo_files = 0
    files_data_file = repo_content_path / "files_data.json"
    if files_data_file.exists():
        try:
            with open(files_data_file, 'r') as f:
                files_data = json.load(f)
                if isinstance(files_data, dict):
                    total_repo_files = len(files_data)
        except Exception as e:
            print(f"Warning: could not read files data for total count: {e}")
    
    # Analyze RSS entries
    rss_candidates, total_rss_entries = analyze_rss_entries_for_cleanup(
        rss_content_path, age_threshold_days
    )
    
    # Print analysis
    print("\n📊 Content Analysis:")
    print(f"\n  Total repository files: {total_repo_files}")
    print(f"\n  Total repository size: {total_repo_size:,} bytes ({total_repo_size/1024/1024:.1f} MB)")
    print(f"\n  Total RSS entries: {total_rss_entries}")
    print(f"\n  Repository files older than {age_threshold_days} days: {len(repo_candidates)}")
    print(f"\n  RSS entries older than {age_threshold_days} days: {len(rss_candidates)}")
    
    if not repo_candidates and not rss_candidates:
        print("✅ No old content found - nothing to cleanup")
        return
    
    # Perform cleanup
    _, _, _ = perform_cleanup(
        repo_content_path, rss_content_path, repo_candidates, rss_candidates, dry_run
    )
    
    if dry_run:
        print("\n💡 To perform actual cleanup, run with DRY_RUN=false")
    else:
        print("\n✅ Cleanup completed successfully!")


if __name__ == "__main__":
    main()
