# AI Sonar Issue Fixer

An enterprise-level application that automatically detects, fixes, and creates pull requests for SonarQube issues in large-scale codebases using a multi-agent architecture with LangGraph.

## Overview

The AI Sonar Issue Fixer automates the process of:
1. Fetching new issues from SonarQube that were introduced since the last Jenkins build
2. Retrieving relevant code context from the repository
3. Using Gemini 2.0 (via LangChain and LangGraph) to intelligently fix the code
4. Committing the fixed code to a new branch
5. Pushing the branch to the Git repository
6. Creating a pull request to merge the fix into the `master` branch

## Features

- **Multi-Agent Architecture**: Uses LangGraph to coordinate specialized agents for different tasks
- **Parallel Processing**: Processes multiple issues simultaneously for faster execution
- **Agent Memory**: Agents learn from previous fixes to improve future performance
- **Feedback Loop**: Automated feedback mechanism to improve fixes over time
- **Visualization Dashboard**: Interactive dashboard to monitor and analyze performance
- **Automated Issue Fixing**: Automatically fixes SonarQube issues using AI
- **Enterprise Scale**: Designed to handle large codebases (667k+ lines of code)
- **CI/CD Integration**: Integrates with Jenkins for daily builds
- **Intelligent Fixes**: Uses Gemini 2.0 to understand and fix code issues
- **Detailed Reporting**: Logs and metrics for tracking progress and success rate

## Multi-Agent Architecture

The application uses a LangGraph-based multi-agent architecture with specialized agents:

1. **Issue Analyzer Agent**: Analyzes SonarQube issues and extracts relevant context
2. **Code Fixer Agent**: Fixes code based on the analysis
3. **PR Creator Agent**: Creates pull requests with detailed descriptions
4. **Orchestrator Agent**: Coordinates the workflow between agents

This architecture provides several benefits:
- **Specialization**: Each agent is optimized for a specific task
- **Robustness**: Failures in one agent don't necessarily cause the entire process to fail
- **Scalability**: Agents can work in parallel on different issues
- **Maintainability**: Each agent can be updated independently

## Requirements

- Python 3.8+
- Access to SonarQube API
- Git repository access
- Azure DevOps API access
- Gemini 2.0 API key

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Edit the `config.py` file to set up your:
- SonarQube API credentials
- Git repository details
- Azure DevOps API credentials
- Gemini 2.0 API key

## Usage

```bash
# Run with default settings
./run.py

# Specify maximum number of issues to process
./run.py --max-issues 10

# Specify number of days to look back for issues
./run.py --days-lookback 3

# Specify number of parallel workers
./run.py --parallel-workers 8

# Disable parallel processing
./run.py --no-parallel
```

## Dashboard

The AI Sonar Issue Fixer includes an interactive dashboard for monitoring and analyzing performance:

```bash
# Run the dashboard
./run_dashboard.py
```

The dashboard provides:
- System overview with key metrics
- Memory analysis with success rates and trends
- Feedback analysis with statistics and recent feedback
- Agent interaction visualization
- Performance metrics for each agent

## Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  SonarQube API  │────▶│  Issue Analyzer │────▶│   Code Fixer    │
│                 │     │      Agent      │     │     Agent       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Azure DevOps   │◀────│   PR Creator   │◀────│  Git Operations │
│       API       │     │     Agent       │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## License

[MIT](LICENSE)
