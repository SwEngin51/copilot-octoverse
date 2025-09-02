# copilot-octoverse-vault

A GitHub Actions pipeline that monitors repository content and RSS feeds monthly, creating issues assigned to Copilot for review.

## 🚨 Required Setup

**Important**: You MUST configure the following before the pipeline will work:

### 1. Template Configuration (Required)
Configure either:
- **Option A**: Set `COPILOT_ACTION_ITEMS_TEMPLATE` repository variable with your template content
- **Option B**: Create `.github/templates/copilot_action_items.md` with your template

**The pipeline will fail if neither is configured** - this is intentional to ensure no hardcoded text in the source code.

### 2. Personal Access Token
For enhanced Copilot assignment features, create a `PERSONAL_ACCESS_TOKEN` repository secret.
