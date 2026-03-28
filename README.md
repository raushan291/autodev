# AutoDev

A multi-agent AI software engineering team that autonomously designs, builds, reviews, tests, and deploys code end-to-end.


## Overview

This project implements a sophisticated multi-agent system for automated software engineering tasks. The system uses a team of specialized agents that collaborate to understand requirements, generate code, review quality, run tests, and deploy solutions.

---


## Installation

Clone the repository and install dependencies:

```bash
git clone --recurse-submodules https://github.com/raushan291/autodev.git
cd autodev
pip install -r requirements.txt
```

---


## Environment Setup

```bash
# Set up environment variables in .env
GEMINI_API_KEY=your_api_key_here
```

---


## Configuration

The application uses a central configuration file:

```bash
app/config.py
```

Edit this file to customize system behavior, such as model settings, agent behavior, execution settings, and project paths.

---


## Usage

### Run the UI

```bash
streamlit run ui/streamlit_app.py
```

---


## Logging

The project uses Python's logging module. Set `DEBUG=1` environment variable for debug-level logging:

```bash
DEBUG=1 streamlit run ui/streamlit_app.py
```

---
