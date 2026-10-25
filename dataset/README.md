# IBM Project CodeNet Dataset Integration

This directory contains the curated IBM Project CodeNet dataset problem catalog and dynamic loader scripts for the Adaptive Multi-Agent AI Tutoring Platform.

## Directory Structure

```text
dataset/
├── metadata/
│   └── codenet_catalog.json    # Mapped problem catalog with test cases
├── problems/
│   └── codenet_loader.py       # Python loader script to import & seed DB
└── README.md
```

## Supported Concept Mappings

All problems in the CodeNet dataset catalog are mapped across 7 core programming concepts:
- `If Else`
- `Loops`
- `Functions`
- `Arrays`
- `Strings`
- `Recursion`
- `OOP`

## How to Import & Sync

To seed or refresh the database with CodeNet challenges:

```bash
python3 dataset/problems/codenet_loader.py
```

If the dataset is unavailable, the backend automatically falls back to curated built-in CodeNet problem definitions.
