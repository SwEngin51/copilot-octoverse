# 🤖 Copilot Feature Matrix Update Required

**Detection Date:** {detection_date}

## Summary

New content has been detected that may require updates to the `copilot-feature-matrix.md` file. Please review the changes below and update the feature matrix accordingly.

{repo_changes}

{rss_changes}


## 🎯 Action Items for @copilot

Please review the detected changes and update the `copilot-feature-matrix.md` file following the **Copilot Matrix Maintenance Guide** principles:

### **1. Content Analysis Priority**
   - **VS Code release notes FIRST** (highest priority for IDE features)
   - **RSS feed content** for platform and secondary IDE features
   - **Cross-reference sources** to avoid duplication

### **2. Feature Classification & Extraction**

#### **IDE Features** (🖥️ IDE Integration Features)
Extract only actual IDE functionality:
- Editor-specific Copilot integrations
- Extension capabilities and UI improvements  
- IDE protocol changes (Language Server, MCP)
- Cross-IDE compatibility features

#### **Platform Features** (🌐 Platform and Agent Evolution Timeline)
Extract service-level capabilities:
- Core Copilot service updates
- AI model changes and new models
- API updates and enterprise features
- Security, performance, GitHub service integration

#### **⚠️ EXCLUDE from Platform Features**
- Event announcements (conferences, webinars)
- Educational content (courses, tutorials)
- Billing/licensing policy changes
- Marketing announcements and company news

### **3. Table Organization Rules**

#### **IDE Features Table Ordering**
1. **VS Code release features** (by version, newest first)
2. **Other IDE features** (by date, newest first)
3. **Never mix** VS Code with external IDE features chronologically

#### **Platform Features Table Ordering**
- **Sort by Latest Update** (newest to oldest)
- **Maintain strict chronological progression**
- **Preserve existing ordering structure**

### **4. RSS Feed Analysis Guidelines**

#### **IDE-Relevant Signals in RSS Feeds**
Look for keywords: `VS Code`, `Visual Studio Code`, `vscode`, `IDE`, `editor`, `extension`
Integration terms: `completion`, `chat`, `debugging`, `workspace`, `LSP`, `MCP`

#### **Source Prioritization**
1. **Tier 1**: Official sources (immediate inclusion)
2. **Tier 2**: Verified sources (validate first)  
3. **Tier 3**: Unverified sources (cross-reference required)

### **5. Feature Updates Protocol**

For each relevant feature:
- **Title**: Clear, specific description of capability
- **Status**: Use emoji scheme (🟢 Stable, 🟡 Preview, 🟠 Experimental, 🔵 Rolling Out, 🔴 Deprecated)
- **Timeline**: Accurate version/date information
- **Lifecycle tracking**: Monitor for deprecation signals (`deprecated`, `sunset`, `EOL`)
- **Source links**: Maintain traceability

### **6. Quality Control Checklist**
- [ ] Feature not already in matrix
- [ ] Source is credible and recent
- [ ] Proper table ordering maintained
- [ ] No duplication across sections
- [ ] Status accurately reflects availability
- [ ] Categories follow established patterns

### **7. Cross-Platform Analysis**
- Identify features spanning IDE and Platform
- Document relationships in key milestones
- Note deprecations affecting multiple platforms

## 📊 Current Status

- Repository monitoring: {repo_status}
- RSS feed monitoring: {rss_status}
- Matrix file: `copilot-feature-matrix.md`

---
