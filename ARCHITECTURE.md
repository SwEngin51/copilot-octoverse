<div align="center">

![Hero](hero.png)

# Copilot Feature Hub — Architecture Diagram

</div>

end-to-end flow: repository + RSS collection, per-feed storage, content cleaning, AI summarization, templated issue creation, and feature matrix update.

<div align="center">

```text
                         [ Scheduler / GitHub Actions ]
                                  (monthly)
                                     |
                                     v
                           +-----------------------------+
                           |  Actions Runner / Workflow  |
                           +-----------------------------+
                                     |
                   ---------------------------------------------
                   |                                           |
                   v                                           v
        +------------------------+                 +---------------------------+
        | Repo Scanner (git)     |                 | RSS Feed Processors       |
        | - microsoft/vscode     |                 | - GitHub blog feed        |
        | - other monitored repos|                 | - Copilot community       |
        |                        |                 |    announcements          |
        +------------------------+                 +---------------------------+
                   |                                           |
                   +----------------------+--------------------+
                     |
                     v
                           +-----------------------------+
                           | Content Cleaner & Extractor |
                           | - strip HTML / Markdown     |
                           | - extract text, links       |
                           | - detect lifecycle signals. |
                           +-----------------------------+
                        |
                        v
                            +-----------------------------+
                            |  Per-feed Storage (artifacts)|
                            | - monitored-content/repo-   |
                            |   content/                  |
                            | - monitored-content/rss-    |
                            |   content/feed-*/           |
                            +-----------------------------+
                           |
                           v
                           +------------------------------+
                           |   AI Summarizer (@copilot)   |
                           | - produce TL;DR & action list|
                           | - assess maturity & status   |
                           | - attach source links & dates|
                           +------------------------------+
                            |
                            v
                           +------------------------------+
                           |   Issue Creator (templated)  |
                           | - uses action items template |
                           | - job-level permissions      |
                           +------------------------------+
         |
         v
                     +----------------------+     +-------------------+
                     | Feature Matrix (MD)  |---->| Notifications     |
                     | - IDE vs Agent split |     | - Slack / email   |
                     | - single source      |     | - dashboard       |
                     +----------------------+     +-------------------+
```

</div>