## 🎯 Action Items for @copilot - JSON Output Format

## 🎯 Action Items for @copilot - JSON Output Format

Please review the detected changes and generate JSON files following the **Copilot Matrix Maintenance Guide** and the schema at `.github/schemas/copilot-feature-schema.json`:

### **1. Content Analysis Priority**
   - **VS Code release notes FIRST** (highest priority for IDE features)
   - **RSS feed content** for platform and secondary IDE features
   - **Cross-reference sources** to avoid duplication

### **2. Feature Classification & Extraction**

#### **IDE Features** → `copilot-ide-features.json`
Extract only actual IDE functionality:
- Editor-specific Copilot integrations and UI improvements
- Extension capabilities and protocol changes (LSP, MCP)
- Cross-IDE compatibility features
- VS Code release features take precedence

#### **Platform Features** → `copilot-platform-features.json`
Extract service-level capabilities:
- Core Copilot service updates and AI model changes
- API updates, enterprise features, security improvements
- Performance enhancements, GitHub service integration

#### **⚠️ EXCLUDE from Platform Features**
- Event announcements, educational content
- Billing/licensing policy changes
- Marketing announcements and company news

### **3. JSON Structure Requirements**

#### **File 1: `copilot-ide-features.json`** (IDE Integration Features)
```json
{
  "metadata": {
    "platform": "IDE",
    "lastUpdated": "ISO_TIMESTAMP",
    "generatedBy": "automated-extraction",
    "feedSources": ["repository sources", "relevant RSS feeds"]
  },
  "features": [
    {
      "featureCapability": "Feature name and brief description",
      "category": "Feature category (e.g., Chat / AI Models)",
      "firstIntroduced": "Version or date (use 'Unknown' if unavailable)",
      "currentStatus": "Stable|Preview|Experimental|Rolling Out|Deprecated|Unknown",
      "latestUpdate": "Most recent version (use 'Unknown' if unavailable)",
      "keyMilestones": "Timeline info (use 'No specific milestones available' if unclear)",
      "sourceLinks": [{"url": "...", "title": "...", "feedSource": "..."}],
      "detectionDate": "ISO_TIMESTAMP",
      "lastModified": "ISO_TIMESTAMP"
    }
  ]
}
```

#### **File 2: `copilot-platform-features.json`** (Platform Features)
- Same JSON structure as above
- Set `metadata.platform` to "Platform"
- Focus on service-level capabilities

### **4. Ordering and Sorting Rules**

#### **IDE Features JSON Ordering**
1. **VS Code release features first** (by version, newest first)
2. **Other IDE features** (by date, newest first)
3. **Maintain separation** between VS Code and external sources

#### **Platform Features JSON Ordering**
- **Sort by `latestUpdate`** (newest to oldest)
- **Preserve chronological flow** matching markdown table

### **5. RSS Feed Analysis Guidelines**

#### **IDE-Relevant Signals**
Keywords: `VS Code`, `Visual Studio Code`, `vscode`, `IDE`, `editor`, `extension`
Integration: `completion`, `chat`, `debugging`, `workspace`, `LSP`, `MCP`

#### **Quality Requirements**
- **Include ALL relevant features** (use "Unknown" for missing info)
- **Text status values only** (no emojis for JSON compatibility)
- **ISO 8601 timestamps** for all datetime fields
- **Source tracking** with `feedSource` identification

### **6. Cross-Platform Features**
- Include in both files when spanning platforms
- Note relationships in `keyMilestones`
- Document deprecations affecting multiple platforms

7. **File output locations**:
   - Save `copilot-ide-features.json` in the repository root
   - Save `copilot-agent-features.json` in the repository root
   - Ensure both files are valid JSON and conform to the schema

## 📊 Current Status

- Repository monitoring: {repo_status}
- RSS feed monitoring: {rss_status}
- Output format: JSON
- Schema file: `.github/schemas/copilot-feature-schema.json`

---
