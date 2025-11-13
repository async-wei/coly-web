
import fitz  # PyMuPDF
import pdfplumber
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple


class QuestionImageExtractor:
    def __init__(self, pdf_path: str, parsed_json_path: str, exam_type: str = "local", output_dir: str = "question_images"):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.exam_type = exam_type  # "local" or "national"
        # Load parsed questions
        with open(parsed_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.questions = data['questions']
            self.exam_year = data['exam_year']
        # Open PDF with both libraries
        self.pdf_plumber = pdfplumber.open(pdf_path)
        self.pdf_fitz = fitz.open(pdf_path)
        # Create output directory: question_images/YEAR/local or national
        self.exam_output_dir = Path(output_dir) / str(self.exam_year) / exam_type
        self.exam_output_dir.mkdir(parents=True, exist_ok=True)
        self.extraction_stats = {
            'total': 0,
            'success': 0,
            'failed': [],
            'file_sizes': []
        }

    def extract_all_questions(self):
        print(f"Extracting images for {len(self.questions)} questions...")
        print(f"Output directory: {self.exam_output_dir}")

        for question in self.questions:
            try:
                self._extract_question_image(question)
                self.extraction_stats['success'] += 1
                print(f"  [OK] Question {question['number']:2d} extracted")
            except Exception as e:
                self.extraction_stats['failed'].append({
                    'number': question['number'],
                    'error': str(e)
                })
                print(f"  [FAIL] Question {question['number']:2d} failed: {e}")

            self.extraction_stats['total'] += 1

        self._update_json_with_paths()
        # Generate simplified answer key JSON
        self._generate_answer_key()
        self._print_summary()

    def _extract_question_image(self, question: Dict):
        """q as image"""
        q_num = question['number']
        page_num = question['page_number']

        # Get bounding box
        bbox = self._find_question_bbox(question)
        # Extract image using PyMuPDF
        page = self.pdf_fitz[page_num - 1]  # 0-indexed
        # Convert bbox to PyMuPDF rect (x0, y0, x1, y1)
        rect = fitz.Rect(bbox['x0'], bbox['y0'], bbox['x1'], bbox['y1'])
        # Render page region to pixmap at high resolution
        mat = fitz.Matrix(3.0, 3.0)
        pix = page.get_pixmap(matrix=mat, clip=rect)
        output_path = self.exam_output_dir / f"q{q_num:02d}.png"
        pix.save(str(output_path))
        file_size = output_path.stat().st_size / 1024  # KB
        self.extraction_stats['file_sizes'].append(file_size)

        # Store path in question data
        question['image_path'] = f"question_images/{self.exam_year}/{self.exam_type}/q{q_num:02d}.png"

    def _find_question_bbox(self, question: Dict) -> Dict[str, float]:
        """
        Find bbox for a question using text coordinate analysis.
        Returns: {'x0': float, 'y0': float, 'x1': float, 'y1': float}
        """
        q_num = question['number']
        page_num = question['page_number']
        page = self.pdf_plumber.pages[page_num - 1]  # 0-indexed
        # words w coords
        words = page.extract_words()
        # q num start
        q_start_pattern = f"{q_num}."
        start_words = [w for w in words if w['text'] == q_start_pattern]

        if not start_words:
            raise ValueError(f"Cannot find start of question {q_num}")

        start_word = start_words[0]
        page_width = page.width
        page_height = page.height
        mid_x = page_width / 2
        in_left_column = start_word['x0'] < mid_x
        # Set column boundaries with some padding
        if in_left_column:
            x0 = 36  #L margin
            x1 = mid_x - 6  #column div
        else:
            x0 = mid_x + 10  # div 2
            x1 = page_width - 34  # R margin
        y0 = start_word['top'] - 5  # Small padding above

        # Find end
        next_q_num = q_num + 1
        next_q_pattern = f"{next_q_num}."

        # look for next q
        next_words = [w for w in words
                     if w['text'] == next_q_pattern
                     and ((in_left_column and w['x0'] < mid_x) or
                          (not in_left_column and w['x0'] >= mid_x))]
        if next_words:
            # end before question
            y1 = next_words[0]['top'] - 3
        else:
            # This is the last question in the column
            # Find choice D to determine end
            col_words = [w for w in words
                        if (in_left_column and w['x0'] < mid_x) or
                           (not in_left_column and w['x0'] >= mid_x)]
            # filter
            footer_keywords = ['Page', 'Property', 'ACS', 'USNCO', 'Exam', 'END', 'OF', 'TEST']
            non_footer_words = [w for w in col_words
                               if not any(keyword in w['text'] for keyword in footer_keywords)
                               and w['top'] >= y0]  # Only words after question start

            # Look for D
            answer_d_patterns = ['(D)', 'D.', 'D)']
            answer_d_words = [w for w in non_footer_words
                             if any(pattern in w['text'] for pattern in answer_d_patterns)]
            if answer_d_words:
                # latest occurance of D
                last_d = max(answer_d_words, key=lambda w: w['bottom'])
                answer_d_text = [w for w in non_footer_words
                               if w['top'] >= last_d['top'] - 2 and w['bottom'] <= last_d['bottom'] + 30]
                if answer_d_text:
                    # Use the bottom of the lowest text in answer D
                    y1 = max(w['bottom'] for w in answer_d_text) + 10 #10px pad
                else:
                    y1 = last_d['bottom'] + 10
            else:
                if non_footer_words:
                    y1 = max(w['bottom'] for w in non_footer_words) + 5
                else:
                    y1 = page_height - 80

        # Ensure y1 doesn't exceed footer area 70px
        y1 = min(y1, page_height - 70)
        return {
            'x0': x0,
            'y0': y0,
            'x1': x1,
            'y1': y1
        }

    def _update_json_with_paths(self):
        """Update the parsed JSON file with image paths"""
        #path structure: parsed_exams/YEAR/local_parsed.json or national_parsed.json
        parsed_dir = Path("parsed_exams") / str(self.exam_year)
        parsed_dir.mkdir(parents=True, exist_ok=True)
        json_path = parsed_dir / f"{self.exam_type}_parsed.json"
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {
                "exam_year": self.exam_year,
                "exam_type": self.exam_type,
                "total_questions": len(self.questions),
                "questions": []
            }
        # Update q w/ image path
        for i, question in enumerate(self.questions):
            if i < len(data.get('questions', [])):
                data['questions'][i]['image_path'] = question.get('image_path', '')
            else:
                data['questions'].append({
                    'number': question['number'],
                    'image_path': question.get('image_path', '')
                })

        # Save updated JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Updated {json_path} with image paths")

    def _generate_answer_key(self):
        """Generate simplified answer key JSON with just: year, type, number, answer, image_path"""
        parsed_dir = Path("parsed_exams") / str(self.exam_year)
        parsed_dir.mkdir(parents=True, exist_ok=True)
        answer_key_path = parsed_dir / f"{self.exam_type}_answer_key.json"
        answer_key_data = []
        for question in self.questions:
            answer_key_data.append({
                "exam_year": self.exam_year,
                "exam_type": self.exam_type,
                "question_number": question['number'],
                "answer": question.get('correct_answer', ''),
                "image_path": question.get('image_path', '')
            })
        with open(answer_key_path, 'w', encoding='utf-8') as f:
            json.dump(answer_key_data, f, indent=2, ensure_ascii=False)
        print(f"[OK] Generated {answer_key_path}")
    def _print_summary(self):
        stats = self.extraction_stats
        print("\n" + "="*60)
        print("IMAGE EXTRACTION COMPLETE")
        print("="*60)
        print(f"\n[OK] Extracted: {stats['success']}/{stats['total']} questions")
        print(f"[OK] Output: {self.exam_output_dir}")

        if stats['file_sizes']:
            avg = sum(stats['file_sizes']) / len(stats['file_sizes'])
            print(f"[OK] Avg size: {avg:.1f} KB")

        if stats['failed']:
            print(f"\n[WARNING] Failed: {len(stats['failed'])} questions")
            for fail in stats['failed'][:3]:
                print(f"  - Q{fail['number']}: {fail['error']}")
    def close(self):
        """Close PDF resources"""
        self.pdf_plumber.close()
        self.pdf_fitz.close()
def main():
    """Main execution"""
    # Configuration
    exam_type = "local"  # "local" or "national"
    for exam_year in range(2022,2023):
        pdf_path = f"usnco-exams/{exam_year}-usnco-{exam_type}-exam.pdf"
        json_path = Path("parsed_exams") / str(exam_year) / f"{exam_type}_parsed.json"

        # Check files exist
        if not Path(pdf_path).exists():
            print(f"Error: PDF not found at {pdf_path}")
            return

        if not json_path.exists():
            print(f"Error: Parsed JSON not found at {json_path}")
            print(f"Expected: {json_path}")
            print(f"Run usnco_parser.py first to generate the parsed JSON file.")
            return

        # Extract images
        extractor = QuestionImageExtractor(pdf_path, str(json_path), exam_type=exam_type)

        try:
            extractor.extract_all_questions()
        finally:
            extractor.close()


if __name__ == "__main__":
    main()
