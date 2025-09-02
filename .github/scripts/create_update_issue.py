#!/usr/bin/env python3
"""
GitHub Issue Creator for Copilot Feature Matrix Updates

This script creates GitHub issues to notify about changes that may require
updates to the copilot-feature-matrix.md file. It processes monitoring data
and generates structured issue content for the Copilot agent to review.

This script is a pure template processor - all content comes from external
template files, with no hardcoded text in the code.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from github import Github


def load_template(template_name):
    """
    Load a template file from the templates directory.
    
    Args:
        template_name: Name of the template file (without path)
        
    Returns:
        Template content as string
    """
    templates_dir = Path(__file__).parent.parent / "templates"
    template_path = templates_dir / template_name
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: Template file {template_path} not found")
        return ""


def format_detection_data(data):
    """
    Format the detection data into a readable string for the issue body.
    
    Args:
        data: Dictionary containing the detection information
        
    Returns:
        Formatted string representation of the data
    """
    formatted_lines = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list) and value:
                formatted_lines.append(f"**{key.replace('_', ' ').title()}:**")
                for item in value:
                    if isinstance(item, dict):
                        formatted_lines.append(f"- {format_detection_data(item)}")
                    else:
                        formatted_lines.append(f"- {item}")
                formatted_lines.append("")
            elif value and not isinstance(value, list):
                formatted_lines.append(f"**{key.replace('_', ' ').title()}:** {value}")
    else:
        return str(data)
    
    return "\n".join(formatted_lines)


def format_file_list(files, limit=5):
    """Format a list of files with truncation."""
    if not files:
        return []
    
    lines = []
    display_files = files[:limit] if len(files) > limit else files
    for file_path in display_files:
        lines.append(f"- {file_path}")
    
    if len(files) > limit:
        lines.append(f"... and {len(files) - limit} more files")
    
    return lines


def create_repo_changes_section(repo_changes):
    """Create the repository changes section using template."""
    if not repo_changes:
        return ""
    
    template = load_template("repo_section.md")
    
    lines = []
    
    # Source information from environment variables
    monitored_repo = os.getenv('MONITORED_REPO', 'Repository')
    monitored_dir = os.getenv('MONITORED_DIRECTORY', 'Directory')
    lines.append(f"**Source:** `{monitored_repo}/{monitored_dir}`")
    lines.append("")
    
    # Extract data from structure (supports both old and new formats)
    summary = repo_changes.get('summary', {})
    file_count_analysis = repo_changes.get('file_count_analysis', {})
    monitored_files = repo_changes.get('monitored_files', {})
    
    # New files - show detailed list
    new_files = repo_changes.get('new_files', [])
    if new_files:
        lines.append("### New Files:")
        lines.append("")
        lines.extend(format_file_list(new_files, limit=10))
        lines.append("")
    
    # Updated files - show detailed list
    updated_files = repo_changes.get('updated_files', [])
    if updated_files:
        lines.append("### Updated Files:")
        lines.append("")
        lines.extend(format_file_list(updated_files, limit=10))
        lines.append("")
    
    # Storage analysis
    lines.append("### Storage Analysis:")
    total_files = file_count_analysis.get('total_files', 0)
    new_files_count = len(new_files)
    updated_files_count = len(updated_files)
    average_size = file_count_analysis.get('average_size', 0)
    
    lines.append(f"- **Total files tracked:** {total_files}")
    lines.append(f"- **Files added this run:** {new_files_count}")
    lines.append(f"- **Files updated this run:** {updated_files_count}")
    if average_size > 0:
        lines.append(f"- **Average file size:** {average_size:,} bytes")
    
    if 'commit_hash' in repo_changes:
        lines.append(f"- **Latest commit:** {repo_changes['commit_hash']}")
    if 'detection_timestamp' in repo_changes:
        lines.append(f"- **Detection time:** {repo_changes['detection_timestamp']}")
    
    repo_data = "\n".join(lines)
    return template.format(repo_data=repo_data)


def create_rss_changes_section(rss_updates):
    """Create the RSS feed updates section using template."""
    if not rss_updates:
        print("📊 Debug: No RSS updates available")
        return ""
    
    print(f"📊 Debug: Processing {len(rss_updates)} RSS updates")
    template = load_template("rss_section.md")
    
    lines = []
    
    for feed_name, feed_data in rss_updates.items():
        print(f"📊 Debug: Processing RSS feed '{feed_name}' with type: {type(feed_data)}")
        
        # Feed name - use feed_title from metadata if available, otherwise fallback to feed_name
        if isinstance(feed_data, dict) and 'feed_title' in feed_data:
            feed_display_name = feed_data['feed_title']
            print(f"📊 Debug: Using feed_title from metadata: {feed_display_name}")
        else:
            # Fallback to processed feed_name
            feed_display_name = feed_name.replace('_', ' ').title()
            print(f"📊 Debug: Using processed feed_name: {feed_display_name}")
        
        lines.append(f"### Feed: {feed_display_name}")
        
        # Source URL
        if isinstance(feed_data, dict) and 'feed_url' in feed_data:
            lines.append(f"**Source:** {feed_data['feed_url']}")
        lines.append("")
        
        # Entries - prioritize new_items over latest_items
        lines.append("**New Entries:**")
        lines.append("")
        
        # Check for new_items first (priority)
        if isinstance(feed_data, dict) and 'new_items' in feed_data and feed_data['new_items']:
            lines.extend(format_rss_entries(feed_data['new_items'], limit=5))
            print(f"📊 Debug: Added {len(feed_data['new_items'])} new entries for {feed_name}")
        
        # Fall back to latest_items
        elif isinstance(feed_data, dict) and 'latest_items' in feed_data and feed_data['latest_items']:
            lines.extend(format_rss_entries(feed_data['latest_items'], limit=5))
            print(f"📊 Debug: Added {len(feed_data['latest_items'])} latest entries for {feed_name}")
        
        # Handle direct list format (legacy)
        elif isinstance(feed_data, list):
            lines.extend(format_rss_entries(feed_data, limit=5))
            print(f"📊 Debug: Added {len(feed_data)} entries from list for {feed_name}")
        
        # Last resort - show raw data snippet
        else:
            lines.append(f"- Raw data: {str(feed_data)[:100]}...")
            print(f"📊 Debug: Added raw data for {feed_name}")
        
        lines.append("")
        
        # Storage analysis for this feed
        total_entries = 0
        new_count = 0
        
        if isinstance(feed_data, dict):
            if 'new_items' in feed_data:
                new_count = len(feed_data['new_items'])
                total_entries = len(feed_data.get('latest_items', []))
            elif 'latest_items' in feed_data:
                total_entries = len(feed_data['latest_items'])
                new_count = total_entries  # All are considered new if no new_items distinction
        elif isinstance(feed_data, list):
            total_entries = len(feed_data)
            new_count = total_entries
        
        if total_entries > 0:
            lines.append("### Storage Analysis:")
            lines.append(f"- **Total entries tracked:** {total_entries}")
            lines.append(f"- **Entries added this run:** {new_count}")
            lines.append("")
    
    rss_data = "\n".join(lines)
    result = template.format(rss_data=rss_data)
    print(f"📊 Debug: Generated RSS section with template, length: {len(result)} characters")
    return result


def format_rss_entries(items, limit=3):
    """Format RSS feed entries with truncation."""
    if not items:
        return []
    
    lines = []
    display_items = items[:limit] if len(items) > limit else items
    
    for item in display_items:
        if isinstance(item, dict):
            title = item.get('title', 'No title')
            link = item.get('link', '')
            published = item.get('published', '')
            
            lines.append(f"- **{title}**")
            if link:
                lines.append(f"  Link: {link}")
            if published:
                lines.append(f"  Published: {published}")
        else:
            lines.append(f"- {item}")
    
    if len(items) > limit:
        lines.append(f"... and {len(items) - limit} more entries")
    
    return lines





def create_issue_body(detection_date, repo_changes=None, rss_updates=None):
    """
    Create the issue body content using templates with data substitution only.
    
    Args:
        detection_date: ISO format date string
        repo_changes: Repository changes data
        rss_updates: RSS feed updates data
        
    Returns:
        Formatted issue body string
    """
    template = load_template("copilot_action_items.md")
    
    # Process data into formatted sections
    repo_section = create_repo_changes_section(repo_changes)
    rss_section = create_rss_changes_section(rss_updates)
    
    # Determine status indicators
    repo_status = "✅ Active" if repo_changes else "⏸️ No changes"
    rss_status = "✅ Active" if rss_updates else "⏸️ No changes"
    
    # Template substitution with all possible placeholders
    return template.format(
        detection_date=detection_date,
        repo_changes=repo_section,
        rss_changes=rss_section,
        repo_status=repo_status,
        rss_status=rss_status
    )


def load_changes_data(local_content_dir):
    """Load change data from repository monitoring and multiple RSS feeds."""
    repo_changes = {}
    rss_feeds_data = []

    # Load repository changes
    repo_changes_file = Path(local_content_dir) / "repo-content" / "latest_changes.json"
    if repo_changes_file.exists():
        try:
            with open(repo_changes_file, 'r') as f:
                repo_changes = json.load(f)
                print(f"📊 Debug: Loaded repo changes with {len(repo_changes.get('new_files', []))} new files")
        except Exception as e:
            print(f"Error loading repository changes: {e}")

    # Load RSS feeds data from feed directories
    rss_content_dir = Path(local_content_dir) / "rss-content"
    if rss_content_dir.exists():
        print(f"📊 Debug: RSS content directory exists, checking for feeds...")
        for feed_dir in rss_content_dir.iterdir():
            if feed_dir.is_dir() and feed_dir.name.startswith('feed-'):
                feed_index = feed_dir.name.replace('feed-', '')
                print(f"📊 Debug: Found feed directory: {feed_dir.name}")
                
                # Try to load latest changes for this feed
                changes_file = feed_dir / "latest_changes.json"
                entries_file = feed_dir / "feed_entries.json"
                metadata_file = feed_dir / "feed_metadata.json"
                
                feed_data = {}
                
                # Load feed metadata first
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            feed_data.update(metadata)
                            print(f"📊 Debug: Loaded metadata for feed {feed_index}")
                    except Exception as e:
                        print(f"Warning loading feed metadata {feed_index}: {e}")
                
                # Load changes if they exist
                if changes_file.exists():
                    try:
                        with open(changes_file, 'r') as f:
                            changes = json.load(f)
                            feed_data.update(changes)
                            print(f"📊 Debug: Loaded changes for feed {feed_index}")
                    except Exception as e:
                        print(f"Warning loading feed changes {feed_index}: {e}")
                
                # Load all entries as fallback
                if entries_file.exists():
                    try:
                        with open(entries_file, 'r') as f:
                            entries = json.load(f)
                            if 'latest_items' not in feed_data:
                                feed_data['latest_items'] = entries
                            print(f"📊 Debug: Loaded {len(entries)} entries for feed {feed_index}")
                    except Exception as e:
                        print(f"Warning loading feed entries {feed_index}: {e}")
                
                if feed_data:
                    # Use feed metadata for name or default to index
                    feed_name = feed_data.get('feed_name', f'feed_{feed_index}')
                    rss_feeds_data.append({
                        'feed_name': feed_name,
                        'data': feed_data
                    })
                    print(f"📊 Debug: Added feed {feed_name} with data keys: {list(feed_data.keys())}")

    print(f"📊 Debug: Total RSS feeds loaded: {len(rss_feeds_data)}")
    return repo_changes, rss_feeds_data


def assign_issue_to_copilot(issue_number, assignee_username, personal_token, repo_name):
    """
    Assign the issue to Copilot using GitHub CLI.
    Waits 2 minutes after issue creation to handle concurrency issues.
    
    Args:
        issue_number: GitHub issue number
        assignee_username: Username to assign the issue to (e.g., 'copilot')
        personal_token: Personal access token with permission to assign issues
        repo_name: Repository name in format 'owner/repo'
    """
    try:
        if not personal_token:
            print(f"⚠️  Warning: No PERSONAL_ACCESS_TOKEN provided, skipping assignment to {assignee_username}")
            return
            
        print(f"⏳ Waiting 2 minutes before assigning to {assignee_username} (concurrency handling)...")
        time.sleep(120)  # Wait 2 minutes
        
        # Set up environment for gh CLI
        env = os.environ.copy()
        env['GITHUB_TOKEN'] = personal_token
        print("🔑 Using personal access token for assignment (will appear as user action)")
        
        # Run gh CLI command to assign issue to copilot
        cmd = ['gh', 'issue', 'edit', str(issue_number), '--add-assignee', assignee_username, '--repo', repo_name]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
        print(f"✅ Successfully assigned issue to '{assignee_username}' using GitHub CLI")
        
    except subprocess.CalledProcessError as e:
        print(f"⚠️ GitHub CLI assignment failed: {e}")
        print(f"   stdout: {e.stdout}")
        print(f"   stderr: {e.stderr}")
        print("   Issue was created successfully but assignment failed")
    except FileNotFoundError:
        print("⚠️ GitHub CLI (gh) not found - assignment failed")
        print("   Issue was created successfully but assignment failed")
    except Exception as e:
        print(f"⚠️ Unexpected error with GitHub CLI: {e}")
        print("   Issue was created successfully but assignment failed")


def create_github_issue(title, body, repo_name, token, assignee=None, personal_token=None):
    """Create a GitHub issue with the provided content and optionally assign it."""
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        # Create the issue
        issue = repo.create_issue(
            title=title,
            body=body,
            labels=['copilot-agent', 'feature-matrix', 'automated']
        )
        
        print(f"✅ Issue created successfully: {issue.html_url}")
        
        # Assign to Copilot if requested
        if assignee:
            assign_issue_to_copilot(issue.number, assignee, personal_token, repo_name)
        
        return issue
        
    except Exception as e:
        print(f"❌ Error creating GitHub issue: {e}")
        sys.exit(1)


def main():
    """Main function to orchestrate the issue creation process."""
    # Get environment variables
    github_token = os.getenv('GITHUB_TOKEN')
    personal_token = os.getenv('PERSONAL_ACCESS_TOKEN')  # For assigning to copilot
    repo_name = os.getenv('GITHUB_REPOSITORY')
    local_content_dir = os.getenv('LOCAL_CONTENT_DIR', 'content')
    copilot_assignee = os.getenv('COPILOT_ASSIGNEE')  # Get assignee from environment
    
    # Make sure MONITORED_REPO and MONITORED_DIRECTORY are available globally
    os.environ.setdefault('MONITORED_REPO', 'microsoft/vscode')
    os.environ.setdefault('MONITORED_DIRECTORY', 'release-notes')
    
    if not github_token:
        print("❌ GITHUB_TOKEN environment variable is required")
        sys.exit(1)
    
    if not repo_name:
        print("❌ GITHUB_REPOSITORY environment variable is required")
        sys.exit(1)
    
    # Load change data
    repo_changes, rss_feeds_data = load_changes_data(local_content_dir)
    
    # Debug RSS data
    print(f"📊 Debug: RSS feeds data loaded: {len(rss_feeds_data)} feeds")
    for i, feed in enumerate(rss_feeds_data):
        print(f"   Feed {i+1}: {feed['feed_name']} - Data type: {type(feed['data'])}")
    
    # Combine RSS feeds data into a single structure
    combined_rss_updates = {}
    for feed in rss_feeds_data:
        combined_rss_updates[feed['feed_name']] = feed['data']
    
    print(f"📊 Debug: Combined RSS updates: {len(combined_rss_updates)} feeds")
    print(f"📊 Debug: RSS updates bool: {bool(combined_rss_updates)}")
    
    # Check if there are any changes to report
    if not repo_changes and not rss_feeds_data:
        print("ℹ️  No changes detected, skipping issue creation")
        return
    
    # Create issue content
    detection_date = datetime.now().isoformat()
    
    # Generate issue body
    issue_body = create_issue_body(
        detection_date=detection_date,
        repo_changes=repo_changes if repo_changes else None,
        rss_updates=combined_rss_updates if combined_rss_updates else None
    )
    
    # Extract title from the issue body (first line should be the title)
    lines = issue_body.split('\n')
    issue_title = lines[0].lstrip('# ') if lines and lines[0].startswith('# ') else "Copilot Feature Matrix Update Required"
    
    create_github_issue(
        title=issue_title,
        body=issue_body,
        repo_name=repo_name,
        token=github_token,
        assignee=copilot_assignee,  # Pass assignee to the function
        personal_token=personal_token  # Pass personal token for assignment
    )


if __name__ == "__main__":
    main()
