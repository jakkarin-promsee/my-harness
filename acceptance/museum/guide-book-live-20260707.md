# Researcher Harness Guidebook

Welcome to the Researcher Harness! This project is a from-scratch implementation designed for learning and experimentation with AI agents.

## Project Overview

The Researcher Harness provides a framework for building and testing AI agents. It's a learning project, so feel free to explore and understand its inner workings.

## Key Components

*   **Source Code:** The core agent and harness logic resides in the `src/harness/` directory.
*   **Documentation:** Project documentation, including this guide, is located in the `docs/` directory.
*   **Archives:** The `archive/` directory contains older or experimental code. **Do not modify** the `archive/mvp/` directory as it is a frozen artifact.

## Core Operations

### Running Tests

To ensure the integrity of the system, two main test suites are available:

1.  **Offline Tests (Recommended):**
    *   Command: `uv run pytest -q`
    *   Details: This suite runs quickly and does not consume any external resources or tokens. It's ideal for verifying changes locally. Pass/fail results are shown as dots (`.`) or errors (`F`). Refer to `tests/README.md` for troubleshooting.

2.  **Acceptance Tests (Full Stack):**
    *   Command: `uv run python acceptance/run.py ollama`
    *   Details: This suite tests the complete system against a live model. It consumes tokens, so use it judiciously. The `ollama` provider is preferred for cost-efficiency. **Never** use the `gemini` provider unless specifically instructed, as it incurs charges.
    *   Read `acceptance/README.md` for more details and budget considerations.

### Running the Harness

You can run the main harness program with the following command:

*   Command: `uv run harness [ollama|gemini|anthropic] [-y]`
    *   Or: `uv run python -m harness [ollama|gemini|anthropic] [-y]`
*   Replace `[ollama|gemini|anthropic]` with your desired LLM provider. The `-y` flag can be used for automatic yes to prompts.

## Agent Usage Guidelines

*   **Environment Variables:** Sensitive information, such as API keys, should be stored in a `.env` file. **Never commit `.env` files** to version control.
*   **General Agent Facts:** For overarching information and facts about how agents operate within this harness, consult the `AGENTS.md` file.
*   **Known Issues:** Be aware that `archive/mvp/fixtures/stats.py` contains a bug deliberately, as part of an acceptance task. Do not "fix" it unless the task specifically requires it.

## Efficient Use

*   **Prioritize Offline Tests:** For rapid feedback on your code changes, always run the offline tests (`uv run pytest -q`) first.
*   **Strategic Acceptance Tests:** Use the acceptance tests only when necessary to verify end-to-end functionality or when specifically required by a task. Be mindful of token costs.
*   **Consult Documentation:** Refer to `AGENTS.md` and `skills/README.md` files for detailed information on agent behavior and specific procedures.

This guide provides a foundational understanding of the Researcher Harness. Happy Hacking!
