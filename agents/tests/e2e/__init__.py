"""End-to-end tests for trading agents with real integrations.

These tests exercise real agent behavior:
- Real Brave Search API calls
- Real database access (PostgreSQL via backend API)
- Real LLM calls (OpenAI)

Run with: pytest tests/e2e/ -v -s

WARNING: These tests cost real $ (LLM + API calls). Run sparingly.
"""
