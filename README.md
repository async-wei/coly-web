# USNCO Question Database

A pipeline for parsing USNCO (United States National Chemistry Olympiad) exam PDFs, extracting question images, and hosting them in a web-based question viewer.

## Overview

i used this project to convert USNCO exam PDFs into a searchable database with individual question images. The pipeline handles:
- PDF text parsing
- Individual question image extraction
- Dropbox link generation for cloud hosting
- Website for browsing questions by year, type, and mode

## Requirements

```
pdfplumber
PyMuPDF (fitz)
dropbox
```

Install dependencies:
```bash
pip install pdfplumber PyMuPDF dropbox
```

## Workflow

### 1. Parsed PDF Exams

Extract questions, answer keys, and metadata from USNCO PDF files.

```bash
python usnco_parser.py
```

Configure in `main()`:
- `exam_type`: "local" or "national"
- `exam_year`: Range of years to process

**Output:**
- `parsed_exams/{year}/{exam_type}_parsed.json` - Full question data with text, choices, answers
- Parsing statistics and issue detection
- note that there were inevitable errors (especially in early years) but ultimately the text parsing wasn't necessary
for the website functionality

### 2. Extracted Question Images

Generate individual PNG images for each question from PDFs.

```bash
python question_image_extractor.py
```

Configure in `main()`:
- `exam_type`: "local" or "national"
- `exam_year`: Range of years to process

**Output:**
- `question_images/{year}/{exam_type}/q{number}.png` - Individual question images
- `parsed_exams/{year}/{exam_type}_answer_key.json` - Simplified answer key with image paths

### 3. Generated Dropbox Links

Made Dropbox links for all question images.

```bash
# Generate new database
python generate_dropbox_links.py

# Fix existing folder links (convert /scl/fo/ to /scl/fi/), apparently was an issue
python generate_dropbox_links.py --fix-links

# Provide token via argument
python generate_dropbox_links.py --token YOUR_TOKEN
```

**Output:**
- `dropbox_question_links.json` - Complete database with Dropbox direct links

**Required Dropbox permissions:**
- files.metadata.read
- files.content.read
- sharing.write

**Note:** The `--fix-links` mode converts old folder-shared links to individual file links. This process takes 10-15 minutes for ~3000 files.

## Website

**Question Modes:**
- Random: Shuffled questions from selected year/type
- Filter by category


## File Structure

```
/
├── usnco-exams/                    # Source PDF files, some needed renaming to fit format
│   └── {year}-usnco-{type}-exam-part-i.pdf
├── parsed_exams/                   # Parsed JSON data
│   └── {year}/
│       ├── {type}_parsed.json
│       └── {type}_answer_key.json
├── question_images/                # Extracted PNG images
│   └── {year}/{type}/
│       └── q{number}.png
├── dropbox_question_links.json     # Dropbox link database
├── usnco_parser.py                 # PDF parsing script
├── question_image_extractor.py     # Image extraction script
├── generate_dropbox_links.py       # Dropbox link generator
├── questions.js                    # Question display logic
├── index.html                      # Web interface
```

## Data Schema

### dropbox_question_links.json
```json
{
  "dropbox_path": "/question_images/2023/national/q01.png",
  "local_path": "question_images/2023/national/q01.png",
  "direct_link": "https://www.dropbox.com/...",
  "exam_year": 2023,
  "exam_type": "national",
  "question_number": 1,
  "answer": "B"
}
```

### {type}_parsed.json
```json
{
  "exam_year": 2023,
  "exam_type": "national",
  "total_questions": 60,
  "questions": [
    {
      "number": 1,
      "text": "Question text...",
      "choices": {
        "A": "Choice A",
        "B": "Choice B",
        "C": "Choice C",
        "D": "Choice D"
      },
      "correct_answer": "B",
      "page_number": 3,
      "has_images": false,
      "parsing_confidence": "high",
      "image_path": "question_images/2023/national/q01.png"
    }
  ],
  "parsing_issues": []
}
```

## Notes

- PDF files must be named: `{year}-usnco-{type}-exam-part-i.pdf`
- Dropbox folder structure must match: `/question_images/{year}/{type}/`
- The parser assumes standard USNCO exam formatting (two-column layout, footer patterns)
- Image extraction requires both PDFs and parsed JSON files
- All scripts process multiple years in a loop by default (edit `range(2000,2026)` to modify)
- The older the exam, the more errors come from parsing

