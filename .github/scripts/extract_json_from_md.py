#!/usr/bin/env python3
"""
Extract JSON feature data from copilot-feature-matrix.md tables.
Simple extraction script that parses markdown tables into JSON following the schema.
"""

import re
import json
from datetime import datetime
from pathlib import Path


def parse_status_emoji(status_cell):
    """Convert emoji status to text."""
    status_map = {
        "🟢": "Stable",
        "🟡": "Preview", 
        "🟠": "Experimental",
        "🔵": "Rolling Out",
        "🔴": "Deprecated"
    }
    
    for emoji, text in status_map.items():
        if emoji in status_cell:
            return text
    
    # If no emoji found, try to extract text
    text = re.sub(r'[^\w\s]', '', status_cell).strip()
    return text if text else "Unknown"


def clean_cell_content(cell):
    """Clean markdown formatting from table cell."""
    # Remove **bold** formattinggit 
    cell = re.sub(r'\*\*(.*?)\*\*', r'\1', cell)
    # Remove *italic* formatting  
    cell = re.sub(r'\*(.*?)\*', r'\1', cell)
    # Remove links but keep text
    cell = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cell)
    return cell.strip()


def parse_markdown_table(table_text, platform):
    """Parse a markdown table into JSON feature objects."""
    features = []
    
    # Split into lines and remove header/separator
    lines = [line.strip() for line in table_text.split('\n') if line.strip()]
    if len(lines) < 3:  # Header + separator + at least one data row
        return features
    
    # Skip header and separator
    data_lines = lines[2:]
    
    for line in data_lines:
        if not line or not line.startswith('|'):
            continue
            
        # Parse table cells
        cells = [cell.strip() for cell in line.split('|')]
        # Remove empty first/last cells from split
        cells = [cell for cell in cells if cell]
        
        if len(cells) < 6:
            continue
            
        feature_capability = clean_cell_content(cells[0])
        category = clean_cell_content(cells[1])
        first_introduced = clean_cell_content(cells[2]) or "Unknown"
        current_status = parse_status_emoji(cells[3])
        latest_update = clean_cell_content(cells[4]) or "Unknown"
        key_milestones = clean_cell_content(cells[5]) or "No specific milestones available"
        
        # Skip empty/header rows
        if not feature_capability or feature_capability.lower() in ['feature', 'capability', 'feature / capability']:
            continue
        
        # Create feature object
        feature = {
            "featureCapability": feature_capability,
            "category": category,
            "firstIntroduced": first_introduced,
            "currentStatus": current_status,
            "latestUpdate": latest_update,
            "keyMilestones": key_milestones,
            "sourceLinks": [
                {
                    "url": "https://github.com/SwEngin51/copilot-octoverse-vault/blob/main/copilot-feature-matrix.md",
                    "title": f"Copilot Feature Matrix - {platform} Features",
                    "feedSource": "feature-matrix"
                }
            ],
            "detectionDate": datetime.now().isoformat(),
            "lastModified": datetime.now().isoformat()
        }
        
        features.append(feature)
    
    return features


def extract_table_section(content, section_patterns):
    """Extract a table section from markdown content using multiple possible patterns."""
    for pattern in section_patterns:
        # Try different approaches to find the section
        patterns_to_try = [
            rf"### {pattern}.*?\n(.*?)(?=\n## |\Z)",  # Level 3 header to level 2 header or end
            rf"## {pattern}.*?\n(.*?)(?=\n## |\n# |\Z)",  # Level 2 header
            rf"# {pattern}.*?\n(.*?)(?=\n# |\Z)",  # Level 1 header
        ]
        
        for regex_pattern in patterns_to_try:
            section_match = re.search(regex_pattern, content, re.DOTALL | re.IGNORECASE)
            
            if section_match:
                section_content = section_match.group(1)
                
                # Find the table within the section
                table_lines = []
                in_table = False
                
                for line in section_content.split('\n'):
                    line = line.strip()
                    if line.startswith('|') and line.count('|') >= 3:  # At least 3 pipes for a valid table row
                        in_table = True
                        table_lines.append(line)
                    elif in_table and line and not line.startswith('|'):
                        # End of table
                        break
                
                if len(table_lines) >= 3:  # Header + separator + at least one data row
                    return '\n'.join(table_lines)
    
    return ""


def main():
    # Read the feature matrix
    matrix_file = Path("copilot-feature-matrix.md")
    if not matrix_file.exists():
        print("❌ copilot-feature-matrix.md not found")
        return
    
    with open(matrix_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract IDE features table
    ide_patterns = [
        "IDE Feature Evolution Timeline",
        "🖥️ IDE Integration Features",
        "IDE Integration Features"
    ]
    ide_table = extract_table_section(content, ide_patterns)
    ide_features = parse_markdown_table(ide_table, "IDE")
    
    # Extract Agent features table  
    agent_patterns = [
        "Platform and Agent Evolution Timeline",
        "🌐 Platform and Agent Evolution Timeline",
        "Agent Feature Evolution Timeline",
        "🤖 Copilot Coding Agent Features",
        "Copilot Coding Agent Features"
    ]
    agent_table = extract_table_section(content, agent_patterns)
    agent_features = parse_markdown_table(agent_table, "Platform")
    
    # Create IDE JSON
    ide_json = {
        "metadata": {
            "platform": "IDE",
            "lastUpdated": datetime.now().isoformat(),
            "generatedBy": "automated-extraction",
            "feedSources": ["copilot-feature-matrix.md"]
        },
        "features": sorted(ide_features, key=lambda x: x.get('latestUpdate', ''), reverse=True)
    }
    
    # Create Agent JSON
    agent_json = {
        "metadata": {
            "platform": "Platform",
            "lastUpdated": datetime.now().isoformat(), 
            "generatedBy": "automated-extraction",
            "feedSources": ["copilot-feature-matrix.md"]
        },
        "features": sorted(agent_features, key=lambda x: x.get('latestUpdate', ''), reverse=True)
    }
    
    # Write JSON files
    with open("copilot-ide-features.json", 'w', encoding='utf-8') as f:
        json.dump(ide_json, f, indent=2, ensure_ascii=False)
    
    with open("copilot-platform-features.json", 'w', encoding='utf-8') as f:
        json.dump(agent_json, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Extracted {len(ide_features)} IDE features and {len(agent_features)} Platform features")
    print("📁 Generated: copilot-ide-features.json, copilot-platform-features.json")


if __name__ == "__main__":
    main()
