# PDF Chemical Analysis Tool with Gemini AI

This tool analyzes PDFs containing chemical information. It extracts text and/or takes screenshots of PDF pages, then uses Google's Gemini AI to identify chemical substances, their concentrations, and their uses.

## Features

- Extract text from PDFs using PyMuPDF
- Take high-quality screenshots of PDF pages
- Analyze content using Google's Gemini AI (multimodal)
- Generate a structured Markdown table of chemical substances
- Flexible modes: analyze text only, images only, or both
- Optional cleanup of temporary files

## Prerequisites

- Python 3.7 or higher
- Google AI API key

## Installation

1. Clone the repository or download the scripts
2. Install required packages:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your Google API key:
   ```
   cp .env.example .env
   ```
   Then edit the `.env` file and replace `your_google_api_key_here` with your actual API key from [Google AI Studio](https://aistudio.google.com/).

## Usage

```bash
python pdf_analyzer.py [pdf_file] --mode [text|screenshots|both] [options]
```

### Required Arguments:

- `pdf_file`: Path to the PDF file you want to analyze
- `--mode`: Source data for analysis
  - `text`: Extract and analyze only text
  - `screenshots`: Generate and analyze only page images
  - `both`: Use both text and images

### Optional Arguments:

- `--output_dir`: Custom directory for saving screenshots (default: `[pdf_name]_screenshots`)
- `--dpi`: Resolution for screenshots (default: 150)
- `--skip_gemini`: Only extract text/images without sending to Gemini
- `--cleanup`: Delete screenshot files after analysis

### Examples:

```bash
# Analyze using only text extraction
python pdf_analyzer.py document.pdf --mode text

# Analyze using only page screenshots
python pdf_analyzer.py document.pdf --mode screenshots

# Analyze using both text and screenshots
python pdf_analyzer.py document.pdf --mode both

# Specify custom screenshot directory and higher resolution
python pdf_analyzer.py document.pdf --mode both --output_dir ./images --dpi 200

# Extract data without Gemini analysis
python pdf_analyzer.py document.pdf --mode both --skip_gemini

# Analyze and clean up temporary files afterward
python pdf_analyzer.py document.pdf --mode screenshots --cleanup
```

## Output

The script outputs a Markdown table with the following columns:
- Substance Name
- Concentration Range
- Use Case

The table is sorted by the apparent importance of each chemical substance in the document. 