"""
Task 04: AI Speech-to-Speech Voice Transformer - core package
Multimedia Systems Laboratory
Author: Rudranshpardeshi09

Modules:
    config     - Settings loaded from environment / .env
    voices     - Allowlisted target voices (slug -> voice ID from env)
    errors     - AppError and the provider error -> user message mapping
    audio      - Format detection, FFprobe duration probe, validation, trimming
    providers  - ElevenLabs Speech-to-Speech client
    service    - The single conversion pipeline used by the CLI and the server
"""

__all__ = ["config", "voices", "errors", "audio", "providers", "service"]
