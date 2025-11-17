import pdfplumber
import re
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path

@dataclass
class Question:
    number: int
    text: str
    choices: dict[str, str]
    correct_answer: str
    page_number: int
    has_images: bool = False
    parsing_confidence: str = 'high'

@dataclass
class ParsingIssue:
    question_number: Optional[int]
    issue: str
    needs_manual_review: bool = False

class USNCOParser:
    def __init__(self, pdf_path: str, exam_year: int = 2018):
        self.pdf_path = pdf_path
        self.exam_year = exam_year
        self.questions: List[Question] = []
        self.parsing_issues: List[ParsingIssue] = []
        self.answer_key: Dict[int, str] = {}

    def parse(self) -> Dict:
        print(f"Opening PDF: {self.pdf_path}")
        with pdfplumber.open(self.pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print("\nExtracting answer key from last page...")
            self._extract_answer_key(pdf.pages[-1])
            print(f"Found {len(self.answer_key)} answers in key")

            for page_num in range(2, min(total_pages - 1, total_pages)):
                page = pdf.pages[page_num]
                print(f"  Processing page {page_num + 1}...")
                self._parse_question_page(page, page_num + 1)

            self.questions.sort(key=lambda q: q.number)
            self._match_answers()
            return {
                "exam_year": self.exam_year,
                "total_questions": len(self.questions),
                "questions": [asdict(q) for q in self.questions],
                "parsing_issues": [asdict(issue) for issue in self.parsing_issues],
            }

    def _extract_answer_key(self, page):
        text = page.extract_text()
        pattern = r'(\d+)\.\s+([A-D])'

        for line in text.split('\n'):
            matches = re.findall(pattern, line)
            for match in matches:
                q_num = int(match[0])
                answer = match[1]
                self.answer_key[q_num] = answer

    def _remove_footer_text(self, text: str, page_number: int) -> str:
        footer_patterns = [
            r'Property of ACS USNCO[^\n]*Local Sectio[^\n]*',
            r'ot for use as USNCO Local Section[^\n]*',
            r'Page \d+ Property of ACS USNCO[^\n]*',
            f'Exam after March 31, {self.exam_year}[^\n]*',
            r'END OF TEST[^\n]*'
        ]

        for pattern in footer_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text

    def _clean_scientific_notation(self, text: str) -> str:
        text = text.replace('\uf0b4', '×')
        pattern = r'(\d+\.?\d*)\s*×\s*10(\d{2,})'

        def replace_scientific(match):
            coefficient = match.group(1)
            exponent_str = match.group(2)

            if len(exponent_str) >= 3 and exponent_str.startswith('10'):
                exp = exponent_str[2:]
            else:
                exp = exponent_str[-2:]

            superscript_map = {
                '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
                '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
                '-': '⁻'
            }
            exp_super = ''.join(superscript_map.get(c, c) for c in exp)
            return f"{coefficient} × 10{exp_super}"

        text = re.sub(pattern, replace_scientific, text)
        pattern_neg = r'(\d+\.?\d*)\s*×\s*10[–\-](\d+)'

        def replace_scientific_neg(match):
            coefficient = match.group(1)
            exponent = match.group(2)

            superscript_map = {
                '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
                '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
            }

            exp_super = '⁻' + ''.join(superscript_map.get(c, c) for c in exponent)
            return f"{coefficient} × 10{exp_super}"

        text = re.sub(pattern_neg, replace_scientific_neg, text)
        return text

    def _parse_question_page(self, page, page_number: int):
        width = page.width
        height = page.height
        mid_x = width / 2
        left_bbox = (0, 0, mid_x, height)
        right_bbox = (mid_x, 0, width, height)

        left_text = page.within_bbox(left_bbox).extract_text()
        right_text = page.within_bbox(right_bbox).extract_text()
        left_text = self._remove_footer_text(left_text, page_number)
        right_text = self._remove_footer_text(right_text, page_number)

        left_images = page.within_bbox(left_bbox).images
        right_images = page.within_bbox(right_bbox).images

        if left_text:
            self._parse_column_text(left_text, page_number, has_images=len(left_images) > 0)
        if right_text:
            self._parse_column_text(right_text, page_number, has_images=len(right_images) > 0)

    def _parse_column_text(self, text: str, page_number: int, has_images: bool = False):
        text = self._clean_scientific_notation(text)
        text = self._merge_subscript_lines(text)

        question_pattern = r'^\s*(\d+)\.\s+'
        lines = text.split('\n')
        current_question = None
        current_text = []

        for line in lines:
            match = re.match(question_pattern, line)
            if match:
                if current_question is not None:
                    self._process_question_block('\n'.join(current_text), current_question, page_number, has_images)

                current_question = int(match.group(1))
                current_text = [line]
            elif current_question is not None:
                current_text.append(line)

        if current_question is not None:
            self._process_question_block('\n'.join(current_text), current_question, page_number, has_images)

    def _merge_subscript_lines(self, text: str) -> str:
        lines = text.split('\n')
        merged_lines = []
        i = 0
        while i < len(lines):
            current_line = lines[i].rstrip()

            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()

                if self._is_subscript_line(next_line, current_line):
                    merged = self._merge_with_subscripts_advanced(current_line, next_line)
                    merged_lines.append(merged)
                    i += 2
                    continue

            merged_lines.append(current_line)
            i += 1
        return '\n'.join(merged_lines)

    def _is_subscript_line(self, line: str, prev_line: str) -> bool:
        if not line:
            return False

        if re.match(r'^[\d\s]+$', line):
            if prev_line and re.search(r'[A-Za-z\)\]]$', prev_line):
                if len(line) < 30:
                    return True
        return False

    def _merge_with_subscripts_advanced(self, line: str, subscript_line: str) -> str:
        subscript_map = {
            '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
            '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'
        }
        tokens = subscript_line.split()

        if not tokens:
            return line

        insertion_points = self._find_subscript_insertion_points(line)

        if len(tokens) == len(insertion_points):
            result = line
            offset = 0
            for pos, token in zip(insertion_points, tokens):
                subscript = ''.join(subscript_map.get(c, c) for c in token)
                insert_pos = pos + offset

                if insert_pos < len(result) and result[insert_pos] == ' ':
                    result = result[:insert_pos] + subscript + result[insert_pos+1:]
                    offset += len(subscript) - 1
                else:
                    result = result[:insert_pos] + subscript + result[insert_pos:]
                    offset += len(subscript)
            return result
        
        subscripts = ''.join(subscript_map.get(c, c) for c in subscript_line if c.isdigit())
        return line + subscripts

    def _find_subscript_insertion_points(self, line: str) -> List[int]:
        insertion_points = []
        all_matches = []
        for match in re.finditer(r'([A-Z][a-z]?)\s', line):
            pos_before = match.start()
            element = match.group(1)
            if pos_before > 0 and line[pos_before - 1] == '(':
                if len(element) == 1:
                    continue
            all_matches.append((match.start(), match.end() - 1, element))

        filtered_matches = []
        for i, (start, end, element) in enumerate(all_matches):
            if i + 1 < len(all_matches):
                next_start, _, _ = all_matches[i + 1]
                if next_start - end <= 3:
                    filtered_matches.append(end)
                    continue
            if i > 0:
                prev_start, prev_end, _ = all_matches[i - 1]
                if start - prev_end <= 3:
                    continue
            filtered_matches.append(end)

        insertion_points.extend(filtered_matches)

        for match in re.finditer(r'\[([A-Z][a-z]?)\s*\]', line):
            insertion_points.append(match.end(1))

        for match in re.finditer(r'\([^)]*[A-Z][a-z]?\s*\)', line):
            paren_content = match.group()
            if re.match(r'^\([A-Z]\)$', paren_content):
                continue
            if match.end() < len(line) and not line[match.end()].isalpha():
                insertion_points.append(match.end())
        insertion_points = sorted(set(insertion_points))

        return insertion_points

    def _process_question_block(self, block: str, q_number: int, page_number: int, has_images: bool):
        block = re.sub(r'^\s*\d+\.\s+', '', block, count=1)

        choices = {}
        question_lines = []
        choice_lines = []
        found_first_choice = False
        lines = block.split('\n')
        for line in lines:
            if re.search(r'\([A-D]\)', line):
                choice_lines.append(line)
                found_first_choice = True
            elif not found_first_choice:
                question_lines.append(line)
            else:
                if line.strip():
                    choice_lines.append(line)

        question_text = '\n'.join(question_lines).strip()
        choice_text = '\n'.join(choice_lines)
        choice_text = self._convert_rate_law_exponents(choice_text)
        choice_pattern = r'\(([A-D])\)\s*([^\(]*?)(?=\s*\([A-D]\)|$)'
        matches = list(re.finditer(choice_pattern, choice_text, re.DOTALL))
        for match in matches:
            letter = match.group(1)
            choice_content = match.group(2).strip()
            choice_content = ' '.join(choice_content.split())
            choices[letter] = choice_content

        if not choices:
            for line in choice_lines:
                match = re.match(r'\(([A-D])\)\s*(.+)', line)
                if match:
                    letter = match.group(1)
                    content = match.group(2).strip()
                    choices[letter] = content
        confidence = self._calculate_confidence(question_text, choices, has_images)

        question = Question(
            number=q_number,
            text=question_text,
            choices=choices,
            correct_answer="",
            page_number=page_number,
            has_images=has_images,
            parsing_confidence=confidence
        )
        self.questions.append(question)

        if len(choices) != 4:
            self.parsing_issues.append(ParsingIssue(
                question_number=q_number,
                issue=f"Found {len(choices)} choices instead of 4",
                needs_manual_review=True
            ))

    def _convert_rate_law_exponents(self, text: str) -> str:
        superscript_map = {
            '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
            '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
        }
        pattern = r'\]([1-9])'
        def replace_exponent(match):
            digit = match.group(1)
            superscript = superscript_map[digit]
            return f']{superscript}'
        text = re.sub(pattern, replace_exponent, text)
        return text
    def _calculate_confidence(self, text: str, choices: dict, has_images: bool) -> str:
        if has_images:
            return 'medium'
        if len(choices) != 4:
            return 'low'
        if len(text) < 5:
            return 'low'
        if len(text) > 500:
            return 'medium'
        for choice_text in choices.values():
            if len(choice_text) < 1:
                return 'low'
        return 'high'

    def _match_answers(self):
        for question in self.questions:
            if question.number in self.answer_key:
                question.correct_answer = self.answer_key[question.number]
            else:
                question.correct_answer = ""
                self.parsing_issues.append(ParsingIssue(
                    question_number=question.number,
                    issue="No answer found in answer key",
                    needs_manual_review=True
                ))
        question_numbers = {q.number for q in self.questions}
        for answer_num in self.answer_key.keys():
            if answer_num not in question_numbers:
                self.parsing_issues.append(ParsingIssue(
                    question_number=answer_num,
                    issue=f"Answer key has entry for Q{answer_num} but question not parsed",
                    needs_manual_review=True
                ))

    def save_json(self, output_path: str, data: Dict):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nJSON saved to: {output_path}")

def main():
    exam_type = "national" # local/national
    for exam_year in range(2000,2026):
        pdf_path = f"usnco-exams/{exam_year}-usnco-{exam_type}-exam-part-i.pdf"

        output_dir = Path("parsed_exams") / str(exam_year)
        output_dir.mkdir(parents=True, exist_ok=True)

        json_output = output_dir / f"{exam_type}_parsed.json"
        report_output = output_dir / f"{exam_type}_parsing_report.md"

        if not Path(pdf_path).exists():
            print(f"Error: PDF file not found at {pdf_path}")
            return

        parser = USNCOParser(pdf_path, exam_year=exam_year)
        data = parser.parse()
        data['exam_type'] = exam_type
        parser.save_json(str(json_output), data)
        print(f"\nIssues:")
        issues = data['parsing_issues']
        
        if issues:
            for i, issue in enumerate(issues[:5], 1):
                q_num = issue['question_number'] or 'N/A'
                print(f"  {i}. Q{q_num}: {issue['issue']}")
        else:
            print("No issues detected")
        print(f"\nOutput files generated")
        print(f"  - {json_output}")
        print(f"  - {report_output}")
if __name__ == "__main__":
    main()
