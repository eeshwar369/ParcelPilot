# AI Tool Usage

AI tools used:

- Codex was used to design the architecture and generate the initial implementation.

How it was used:

- Interpreted the assessment requirements.
- Created the architecture plan.
- Designed the enterprise-scale platform roadmap.
- Generated the backend agent, tools, model router, and UI scaffold.
- Added smoke tests and submission notes.

Human responsibilities:

- Review the final code.
- Add the official ParcelPilot data pack into `data/raw`.
- Run ingestion and validate answers against the supplied files.
- Deploy the app and record the demo video.

The application itself is designed to optionally use OpenAI and Hugging Face models through environment variables, with deterministic fallback behavior when no API keys are configured.
