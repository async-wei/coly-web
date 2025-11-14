# Setting Up Question Images with Dropbox

## Current Structure

Your question images should follow this path structure:
```
question_images/
├── 2023/
│   ├── local/
│   │   ├── q01.png
│   │   ├── q02.png
│   │   └── ...
│   └── national/
│       ├── q01.png
│       └── ...
├── 2024/
│   └── ...
└── ...
```

## Option 1: Using Dropbox (Recommended for Production)

### Step 1: Upload Images to Dropbox

1. Upload your entire `question_images` folder to Dropbox
2. Right-click on the folder → "Share" → "Create link"
3. Copy the shared link

### Step 2: Convert to Direct Download Link

Dropbox shared links look like:
```
https://www.dropbox.com/scl/fo/xxxxx/yyyyy?rlkey=zzzzz&dl=0
```

Convert it to a direct download link:
```
https://dl.dropboxusercontent.com/scl/fo/xxxxx/yyyyy?rlkey=zzzzz&dl=0
```

Or use individual file links for better control.

### Step 3: Update Configuration

Edit `questions.js` and update the CONFIG object:

```javascript
const CONFIG = {
    useDropbox: true,  // Change to true
    dropboxBaseUrl: 'YOUR_DROPBOX_DIRECT_LINK_HERE/question_images',
    localBasePath: 'question_images'
};
```

### Example:
```javascript
const CONFIG = {
    useDropbox: true,
    dropboxBaseUrl: 'https://dl.dropboxusercontent.com/your-folder/question_images',
    localBasePath: 'question_images'
};
```

## Option 2: Using Local Images (Development)

1. Keep images in the `question_images/` folder locally
2. Keep `useDropbox: false` in `questions.js`
3. Run with a local server (see below)

### Running a Local Server

```bash
# Python 3
python -m http.server 8000

# Node.js (with http-server)
npx http-server

# Then visit: http://localhost:8000/website.html
```

## Image Path Format

From the answer key JSON, the script can extract:
- **Year**: `2023` from `question_images/2023/local/q01.png`
- **Exam Type**: `local` or `national`
- **Question Number**: `q01` = Question 1

## Answer Keys

Answer keys are stored locally in the repo at:
```
parsed_exams/
├── 2023/
│   ├── local_answer_key.json
│   └── national_answer_key.json
└── ...
```

These are loaded directly by the JavaScript and don't need to be uploaded to Dropbox.

## Testing

1. Make sure answer key JSON files are in `parsed_exams/`
2. Test with local images first
3. Upload to Dropbox when ready for production
4. Update the config
5. Test the Dropbox links

## URL Parameters

The questions page accepts URL parameters:
- `year` - The exam year (default: 2023)
- `type` - The exam type: `local` or `national` (default: local)

Example:
```
questions.html?year=2024&type=national
```
