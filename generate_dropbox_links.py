import json
import os
from pathlib import Path
import dropbox
from dropbox.exceptions import ApiError
import time
import argparse
import shutil

class DropboxLinkGenerator:
    def __init__(self, access_token):
        self.dbx = dropbox.Dropbox(access_token)
        self.dbx.users_get_current_account()
        print("Successfully connected to Dropbox")

    def list_folder_recursive(self, path=""):
        print(f"Listing folder: {path}")
        files = []
        result = self.dbx.files_list_folder(path, recursive=True)
        while True:
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    files.append(entry)
                    
            if not result.has_more:
                break

            result = self.dbx.files_list_folder_continue(result.cursor)
        return files
    
    def get_shared_link(self, file_path):
        links = self.dbx.sharing_list_shared_links(path=file_path).links
        if links:
            return self.convert_to_direct_link(links[0].url)

        time.sleep(0.05)
        shared_link_metadata = self.dbx.sharing_create_shared_link_with_settings(
            file_path,
            settings=dropbox.sharing.SharedLinkSettings(
                requested_visibility=dropbox.sharing.RequestedVisibility.public
            )
        )
        return self.convert_to_direct_link(shared_link_metadata.url)

    def convert_to_direct_link(self, url):
        if "?dl=0" in url:
            return url.replace("?dl=0", "?raw=1")
        elif "dl=0" in url:
            return url.replace("dl=0", "raw=1")
        else:
            separator = "&" if "?" in url else "?"
            return f"{url}{separator}raw=1"

def load_all_answer_keys():
    answer_keys = {}
    parsed_exams_dir = Path("parsed_exams")
    if not parsed_exams_dir.exists():
        print("Error: parsed_exams directory not found")
        return answer_keys

    for year_dir in sorted(parsed_exams_dir.iterdir()):
        if not year_dir.is_dir():
            continue
        year = year_dir.name
        
        for exam_type in ["local", "national"]:
            answer_key_file = year_dir / f"{exam_type}_answer_key.json"
            if answer_key_file.exists():
                with open(answer_key_file, 'r') as f:
                    questions = json.load(f)
                    for q in questions:
                        if q["image_path"]:
                            answer_keys[q["image_path"]] = q

    print(f"loaded{len(answer_keys)} answer key entries")
    return answer_keys

def generate_question_database(access_token):
    print("Dropbox Link Generator for Chem Oly Q")
    print("\n[1/4] Connecting to Dropbox...")
    generator = DropboxLinkGenerator(access_token)
    print("\n[2/4] Getting answer keys")
    answer_keys = load_all_answer_keys()
    print("\n[3/4] Fetching files from Dropbox...")
    files = generator.list_folder_recursive("/question_images")
    print(f"\n[4/4] Generating links for {len(files)} files...")
    question_database = []
    for i, file_entry in enumerate(files):
        file_path = file_entry.path_display
        file_name = file_entry.name

        if not file_name.endswith(".png"):
            continue
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(files)} files processed...")

        direct_link = generator.get_shared_link(file_path)
        local_path = file_path.lstrip("/")
        answer_data = answer_keys.get(local_path, {})
        question_entry = {
            "dropbox_path": file_path,
            "local_path": local_path,
            "direct_link": direct_link,
            "exam_year": answer_data.get("exam_year", None),
            "exam_type": answer_data.get("exam_type", None),
            "question_number": answer_data.get("question_number", None),
            "answer": answer_data.get("answer", None)
        }
        question_database.append(question_entry)

    def sort_key(x):
        year = x["exam_year"] if isinstance(x["exam_year"], int) else 9999
        exam_type = x["exam_type"] or ""
        question_num = x["question_number"] if isinstance(x["question_number"], int) else 9999
        return (year, exam_type, question_num)

    question_database.sort(key=sort_key)
    with open("dropbox_question_links.json", 'w') as f:
        json.dump(question_database, f, indent=2)
    print(f"Generated {len(question_database)} question entries")
    print(f"Output saved to: dropbox_question_links.json")


def fix_dropbox_links(access_token):
# previously, was "fo" instead of "fi"
    generator = DropboxLinkGenerator(access_token)

    print("\n[1/3] Loading existing question links...")
    with open('dropbox_question_links.json', 'r') as f:
        questions = json.load(f)
    print(f"Loaded {len(questions)} questions\n")
    print("[2/3] Identifying folder shared links...")
    files_needing_links = [q for q in questions if '/scl/fo/' in q['direct_link']]
    print(f"{len(files_needing_links)} files with folder links\n")
    print(f"[3/3] individual file links for {len(files_needing_links)} files...")

    for i, q in enumerate(files_needing_links):
        file_path = q['dropbox_path']
        if (i + 1) % 100 == 0:
            print(f"  Progress: {i+1}/{len(files_needing_links)} files processed...")
        links = generator.dbx.sharing_list_shared_links(path=file_path).links
        for link in links:
            generator.dbx.sharing_revoke_shared_link(link.url)
        time.sleep(0.05)
        shared_link = generator.dbx.sharing_create_shared_link_with_settings(
            file_path,
            settings=dropbox.sharing.SharedLinkSettings(
                requested_visibility=dropbox.sharing.RequestedVisibility.public
            )
        )
        direct_url = generator.convert_to_direct_link(shared_link.url)
        for question in questions:
            if question['dropbox_path'] == file_path:
                question['direct_link'] = direct_url
    print(f"Fixed {len(files_needing_links)} links")
    shutil.copy('dropbox_question_links.json', 'dropbox_question_links.json.backup')
    with open('dropbox_question_links.json', 'w') as f:
        json.dump(questions, f, indent=2)
    print(f"Saved updated links")
    folder_count = sum(1 for q in questions if '/scl/fo/' in q.get('direct_link', ''))
    file_count = sum(1 for q in questions if '/scl/fi/' in q.get('direct_link', ''))
    if folder_count > 0:
        print(f"\n{folder_count} folder links still remain")
    else:
        print(f"\nAll links fixed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dropbox Chemistry Olympiad Question Link Generator")
    parser.add_argument('--fix-links', action='store_true',
                       help='Fix existing folder links in dropbox_question_links.json')
    parser.add_argument('--token', type=str,
                       help='Dropbox access token (will prompt if not provided)')
    args = parser.parse_args()
    if args.fix_links:
        print("Dropbox Link Fixer Mode")
        print("\nThis will:")
        print("1. Find all folder shared links (/scl/fo/)")
        print("2. Delete them")
        print("3. Create individual file links (/scl/fi/) for each image")
        print("\nThis process may take 10-15 minutes for ~3000 files.\n")
    else:
        print("Dropbox Chemistry Olympiad Question Link Generator")
        print("\nIMPORTANT: Make sure your Dropbox access token has these permissions:")
        print("  - files.metadata.read")
        print("  - files.content.read")
        print("  - sharing.write\n")
    access_token = args.token if args.token else input("Dropbox access token: ").strip()
    if args.fix_links:
        confirm = input("\nProceed with fixing links? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Cancelled.")
            exit(0)

    if args.fix_links:
        fix_dropbox_links(access_token)
    else:
        generate_question_database(access_token)
