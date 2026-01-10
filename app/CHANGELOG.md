v1.0.0 Latest
[1.0.0] - 2025-04-28

Added

🛂 Granular Voice Feature Permissions Per User Group: Admins can now separately manage access to Speech-to-Text (record voice), Text-to-Speech (read aloud), and Tool Calls for each user group—giving teams tighter control over voice features and enhanced governance across roles.

🗣️ Toggle Voice Activity Detection (VAD) for Whisper STT: New environment variable lets you enable/disable VAD filtering with built-in Whisper speech-to-text, giving you flexibility to optimize for different audio quality and response accuracy levels.

📋 Copy Formatted Response Mode: You can now enable “Copy Formatted” in Settings > Interface to copy AI responses exactly as styled (with rich formatting, links, and structure preserved), making it faster and cleaner to paste into documents, emails, or reports.

⚙️ Backend Stability and Performance Enhancements: General backend refactoring improves system resilience, consistency, and overall reliability—offering smoother performance across workflows whether chatting, generating media, or using external tools.

🌎 Translation Refinements Across Multiple Languages: Updated translations deliver smoother language localization, clearer labels, and improved international usability throughout the UI—ensuring a better experience for non-English speakers.
Fixed

🛠️ LDAP Login Reliability Restored: Resolved a critical issue where some LDAP setups failed due to attribute parsing—ensuring consistent, secure, and seamless user authentication across enterprise deployments.

🖼️ Image Generation in Temporary Chats Now Works Properly: Fixed a bug where image outputs weren’t generated during temporary chats—visual content can now be used reliably in all chat modes without interruptions.
