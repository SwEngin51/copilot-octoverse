#!/usr/bin/env python3
"""
Monitor a specific directory in a GitHub repository for changes.
Uses metadata-only tracking for efficient change detection while content gets committed to repo.

Key Features:
- Downloads and saves file content locally for committing to repository
- Stores only metadata (hash, size, path) in JSON for change tracking  
- Hash-based comparison for accurate change detection
- Cleanup-safe: content workflows won't interfere with monitoring state
- Protected metadata files ensure monitoring system continuity

File Storage:
- Content: Local files → committed to repo → available in git history
- Metadata: JSON tracking files for processing state only
"""

import os
import sys
import json
import hashlib
import base64
from datetime import datetime
from pathlib import Path
from github import Github


def safe_github_output(key, value):
    """Safely write to GitHub Actions output, escaping special characters."""
    if not value:
        value = ""
    
    # Replace problematic characters - use explicit escape sequences
    safe_value = str(value).replace('\n', ' ').replace('\r', ' ')
    # Replace bullet points with dashes for better compatibility
    safe_value = safe_value.replace('•', '-').replace('…', '...')
    # Remove any other non-ASCII characters that might cause issues
    safe_value = ''.join(char if ord(char) < 128 else '?' for char in safe_value)
    
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write(f"{key}={safe_value}\n")


def download_file_metadata(repo, file_path, ref="main"):
    """Download only metadata of a file from GitHub (content gets committed to repo)."""
    try:
        file_content = repo.get_contents(file_path, ref=ref)
        if file_content.type == "file":
            # Calculate content hash for change detection
            content = file_content.decoded_content.decode('utf-8')
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            # Return only metadata - content will be committed to repo separately
            return {
                "sha": file_content.sha,
                "size": file_content.size,
                "path": file_content.path,
                "content_hash": content_hash,
                "download_url": file_content.download_url,
                "last_processed": datetime.now().isoformat()
            }
    except Exception as e:
        print(f"Warning: Could not download metadata for {file_path}: {e}")
        return None


def download_file_content_for_commit(repo, file_path, ref="main"):
    """Download file content for committing to repo (separate from metadata tracking)."""
    try:
        file_content = repo.get_contents(file_path, ref=ref)
        if file_content.type == "file":
            return file_content.decoded_content.decode('utf-8')
    except Exception as e:
        print(f"Warning: Could not download content for {file_path}: {e}")
        return None


def should_process_file(file_path):
    """Check if we should process this file based on extension."""
    allowed_extensions = {'.md', '.markdown', '.txt', '.json'}
    file_ext = Path(file_path).suffix.lower()
    return file_ext in allowed_extensions

def save_file_locally(local_storage_path, relative_path, content):
    local_file_path = Path(local_storage_path) / "files" / relative_path
    local_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(local_file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  💾 Saved to: {local_file_path}")

def handle_file(repo, item, relative_path, files_metadata, ref, local_storage_path):
    if should_process_file(item.path):
        print(f"📄 Processing: {item.path}")
        
        # Get metadata for tracking
        file_metadata = download_file_metadata(repo, item.path, ref)
        if file_metadata:
            files_metadata[relative_path] = file_metadata
            
            # Get content for committing to repo (if needed)
            if local_storage_path:
                content = download_file_content_for_commit(repo, item.path, ref)
                if content:
                    save_file_locally(local_storage_path, relative_path, content)
    else:
        print(f"⏭️  Skipping non-markdown file: {item.path}")

def handle_directory(repo, item, current_files, relative_path, ref, local_storage_path):
    print(f"📁 Entering directory: {item.path}")
    try:
        subcontents = repo.get_contents(item.path, ref=ref)
        if isinstance(subcontents, list):
            process_contents(repo, subcontents, current_files, relative_path, ref, local_storage_path)
        else:
            process_contents(repo, [subcontents], current_files, relative_path, ref, local_storage_path)
    except Exception as e:
        print(f"Warning: Could not access directory {item.path}: {e}")

def process_contents(repo, items, current_files, current_path, ref, local_storage_path):
    for item in items:
        relative_path = f"{current_path}/{item.name}" if current_path else item.name
        if item.type == "file":
            handle_file(repo, item, relative_path, current_files, ref, local_storage_path)
        elif item.type == "dir":
            handle_directory(repo, item, current_files, relative_path, ref, local_storage_path)

def get_directory_contents(repo, directory_path, ref="main", local_storage_path=None):
    """Get the directory contents and download only markdown files."""
    try:
        contents = repo.get_contents(directory_path, ref=ref)
        files_data = {}

        if isinstance(contents, list):
            process_contents(repo, contents, files_data, "", ref, local_storage_path)
        else:
            # Single file
            if should_process_file(contents.path):
                print(f"📄 Processing single file: {contents.path}")
                
                # Get metadata for tracking
                file_metadata = download_file_metadata(repo, contents.path, ref)
                if file_metadata:
                    files_data[contents.name] = file_metadata
                    
                    # Get content for committing to repo (if needed)
                    if local_storage_path:
                        content = download_file_content_for_commit(repo, contents.path, ref)
                        if content:
                            save_file_locally(local_storage_path, contents.name, content)
            else:
                print(f"⏭️  Skipping non-markdown file: {contents.path}")

        return files_data
    except Exception as e:
        print(f"Error accessing directory {directory_path}: {e}")
        return {}


def compare_file_metadata(old_metadata, new_metadata):
    """Simple comparison: track monitored files with their hashes, basic summary.
    
    Logic:
    - If file name doesn't exist in old metadata → new file
    - If file exists but content hash different → updated file  
    - If file exists and content hash same → do nothing (unchanged)
    
    Returns essential attributes plus file lists for detailed reporting:
    - monitored_files: Current state with content hashes
    - file_count_analysis: Basic file statistics  
    - summary: Simple counts of new/updated/unchanged
    - new_files: List of new file names for detailed reporting
    - updated_files: List of updated file names for detailed reporting
    """
    new_files = []
    updated_files = []
    unchanged_files = []
    total_size = 0
    
    # Compare files: new, updated, or unchanged
    for file_path, metadata in new_metadata.items():
        file_size = metadata.get("size", 0)
        total_size += file_size
        
        if file_path not in old_metadata:
            # New file - file name doesn't exist in the object
            new_files.append(file_path)
        else:
            # File exists, compare content hash
            old_hash = old_metadata[file_path].get("content_hash")
            new_hash = metadata.get("content_hash")
            
            if old_hash != new_hash:
                # Hash different - updated file
                updated_files.append(file_path)
            else:
                # Hash same - unchanged file
                unchanged_files.append(file_path)
    
    # Return essential attributes plus file lists for detailed reporting
    return {
        "monitored_files": new_metadata,  # Current state with content hashes
        "file_count_analysis": {
            "total_files": len(new_metadata),
            "average_size": round(total_size / len(new_metadata)) if new_metadata else 0
        },
        "summary": {
            "new_count": len(new_files),
            "updated_count": len(updated_files),
            "unchanged_count": len(unchanged_files)
        },
        "new_files": new_files,      # List of new file names
        "updated_files": updated_files,  # List of updated file names
        "unchanged_files": unchanged_files  # List of unchanged file names (for completeness)
    }


def is_significant_file_by_path(file_path):
    """Determine if a file is significant based on filename patterns."""
    significant_patterns = [
        "release", "changelog", "version", "copilot", "feature",
        "update", "announcement", "news", "breaking", "migration"
    ]
    
    file_path_lower = file_path.lower()
    return any(pattern in file_path_lower for pattern in significant_patterns)


def is_significant_file(file_path, content):
    """Detect if a file might be significant (version-related, release notes, or has copilot content)."""
    file_path_lower = file_path.lower()
    content_lower = content.lower()
    
    # Check for version/release indicators
    version_indicators = [
        'release', 'changelog', 'changes', 'notes', 'updates', 'news',
        'v1.', 'version', 'whatsnew', 'releases'
    ]
    
    # Check for copilot content
    copilot_keywords = [
        'copilot', 'github copilot', 'ai assistant', 'code completion',
        'chat', 'suggestions', 'autocomplete', 'ai model', 'gpt',
        'claude', 'gemini', 'agent mode', 'inline completion'
    ]
    
    has_version_content = any(indicator in file_path_lower for indicator in version_indicators)
    has_copilot_content = any(keyword in content_lower for keyword in copilot_keywords)
    
    return has_version_content or has_copilot_content


def extract_version_from_filename(file_path):
    """Extract version number from filename if possible."""
    import re
    
    # Look for version patterns like v1.104, 1.104, etc.
    version_patterns = [
        r'v?(\d+\.\d+(?:\.\d+)?)',
        r'version[_-]?(\d+\.\d+(?:\.\d+)?)',
        r'(\d{4}[_-]\d{2}[_-]\d{2})'  # Date patterns
    ]
    
    for pattern in version_patterns:
        match = re.search(pattern, file_path, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return "unknown"


def detect_copilot_content(content):
    """Detect if content contains Copilot-related information."""
    content_lower = content.lower()
    copilot_keywords = [
        'copilot', 'github copilot', 'ai assistant', 'code completion',
        'chat', 'suggestions', 'autocomplete', 'ai model', 'gpt',
        'claude', 'gemini', 'agent mode', 'inline completion'
    ]
    
    detected_keywords = []
    for keyword in copilot_keywords:
        if keyword in content_lower:
            detected_keywords.append(keyword)
    
    return {
        "has_copilot_content": len(detected_keywords) > 0,
        "keywords_found": detected_keywords,
        "keyword_count": len(detected_keywords)
    }


def analyze_content_changes(old_content, new_content):
    """Analyze what changed between old and new content."""
    old_lines = old_content.split('\n')
    new_lines = new_content.split('\n')
    
    changes = {
        "lines_added": len(new_lines) - len(old_lines),
        "estimated_additions": 0,
        "potential_new_features": []
    }
    
    # Simple diff - count new lines that weren't in old content
    old_content_set = set(line.strip() for line in old_lines if line.strip())
    new_content_set = set(line.strip() for line in new_lines if line.strip())
    new_unique_lines = new_content_set - old_content_set
    
    changes["estimated_additions"] = len(new_unique_lines)
    
    # Look for potential new features in added content
    feature_indicators = ['new', 'added', 'introduced', 'feature', 'support', 'improved']
    for line in new_unique_lines:
        line_lower = line.lower()
        if any(indicator in line_lower for indicator in feature_indicators):
            if 'copilot' in line_lower:
                changes["potential_new_features"].append(line[:100])
    
    return changes



def main():
    """Main function to monitor repository directory for changes."""
    github_token = os.getenv('GITHUB_TOKEN')
    monitored_repo = os.getenv('MONITORED_REPO')
    monitored_directory = os.getenv('MONITORED_DIRECTORY')
    local_content_dir = os.getenv('LOCAL_CONTENT_DIR')
    
    if not all([github_token, monitored_repo, monitored_directory, local_content_dir]):
        print("Error: Missing required environment variables")
        sys.exit(1)
    
    # Initialize GitHub client
    g = Github(github_token)
    
    try:
        repo = g.get_repo(monitored_repo)
    except Exception as e:
        print(f"Error accessing repository {monitored_repo}: {e}")
        sys.exit(1)
    
    # Create local storage directory
    repo_content_path = Path(local_content_dir) / "repo-content"
    repo_content_path.mkdir(parents=True, exist_ok=True)
    
    # Get current directory contents with metadata tracking + file downloads
    print(f"📥 Scanning content from {monitored_repo}/{monitored_directory}")
    current_metadata = get_directory_contents(repo, monitored_directory, local_storage_path=repo_content_path)
    
    if not current_metadata:
        print("Warning: No content found in monitored directory")
        safe_github_output("changes_detected", "false")
        safe_github_output("changes_summary", "")
        sys.exit(0)
    
    # Load previous files if exists
    files_data_file = repo_content_path / "files_data.json"
    previous_files = {}
    
    if files_data_file.exists():
        try:
            with open(files_data_file, 'r') as f:
                previous_files = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load previous files data: {e}")
    
    # Compare file contents using simplified structure
    changes_data = compare_file_metadata(previous_files, current_metadata)
    
    # Extract key data from simplified structure
    summary = changes_data["summary"]
    file_count = changes_data["file_count_analysis"]["total_files"]
    
    # Determine if there are changes
    has_changes = summary["new_count"] > 0 or summary["updated_count"] > 0
    
    # Create summary string
    summary_parts = []
    if summary["new_count"] > 0:
        summary_parts.append(f"📁 New files: {summary['new_count']}")
    
    if summary["updated_count"] > 0:
        summary_parts.append(f"� Updated files: {summary['updated_count']}")
    
    if summary["unchanged_count"] > 0:
        summary_parts.append(f"✅ Unchanged files: {summary['unchanged_count']}")
    
    summary_parts.append(f"📊 Total files: {file_count}")
    
    changes_summary = " | ".join(summary_parts)
    
    # Save current files data for next comparison
    with open(files_data_file, 'w') as f:
        json.dump(current_metadata, f, indent=2)
    
    # Save detailed changes data
    changes_file = repo_content_path / "latest_changes.json"
    with open(changes_file, 'w') as f:
        json.dump(changes_data, f, indent=2)
    
    # Set outputs for GitHub Actions
    safe_github_output("changes_detected", str(has_changes).lower())
    safe_github_output("changes_summary", changes_summary)
    
    if has_changes:
        print("✅ Repository changes detected!")
        print(f"📊 Summary: {changes_summary}")
        print(f"\n� Details:")
        print(f"  New files: {summary['new_count']}")
        print(f"  Updated files: {summary['updated_count']}")
        print(f"  Unchanged files: {summary['unchanged_count']}")
        print(f"  Total files tracked: {file_count}")
        print(f"  Average file size: {changes_data['file_count_analysis']['average_size']} bytes")
    else:
        print("✅ No repository changes detected")
        print(f"📊 Status: {changes_summary}")
    
    print(f"\n📁 Monitoring Summary:")
    print(f"   • Repository: {monitored_repo}")
    print(f"   • Directory: {monitored_directory}")
    print(f"   • Content: Saved locally and committed to repository")
    print(f"   • Metadata: Tracked in JSON for change detection")
    print(f"   • Change detection: Hash-based comparison (efficient)")


if __name__ == "__main__":
    main()
