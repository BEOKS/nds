#!/usr/bin/env python3
"""Obsidian Zettelkasten Note Manager"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path
import re

# 노트 타입별 폴더 매핑
TYPE_FOLDERS = {
    "fleeting": "00-Inbox",
    "dev": "01-Development",
    "til": "02-TIL",
    "meeting": "03-Meetings",
    "project": "04-Projects",
    "permanent": "05-Permanent",
}

def get_vault_path():
    """환경변수에서 vault 경로 가져오기"""
    path = os.environ.get("OBSIDIAN_PATH")
    if not path:
        print("Error: OBSIDIAN_PATH 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        print("export OBSIDIAN_PATH=\"/path/to/vault\" 로 설정하세요.", file=sys.stderr)
        sys.exit(1)
    return Path(path)

def generate_id():
    """Zettelkasten ID 생성 (YYYYMMDDHHmmss)"""
    return datetime.now().strftime("%Y%m%d%H%M%S")

def create_frontmatter(note_id, title, note_type, tags=None):
    """YAML frontmatter 생성"""
    now = datetime.now().isoformat()
    tags_list = tags.split(",") if tags else []
    return f"""---
id: "{note_id}"
title: "{title}"
type: {note_type}
tags: {json.dumps(tags_list)}
created: {now}
modified: {now}
links: []
---

"""

def ensure_folders(vault_path):
    """폴더 구조 생성"""
    for folder in TYPE_FOLDERS.values():
        (vault_path / folder).mkdir(parents=True, exist_ok=True)

def create_note(args):
    """새 노트 생성"""
    vault = get_vault_path()
    ensure_folders(vault)

    note_id = generate_id()
    note_type = args.type or "fleeting"
    folder = TYPE_FOLDERS.get(note_type, "00-Inbox")

    filename = f"{note_id} {args.title}.md"
    filepath = vault / folder / filename

    frontmatter = create_frontmatter(note_id, args.title, note_type, args.tags)
    content = frontmatter + f"# {args.title}\n\n" + (args.content or "")

    filepath.write_text(content, encoding="utf-8")
    print(f"Created: {filepath}")
    print(f"ID: {note_id}")

def append_note(args):
    """기존 노트에 내용 추가"""
    vault = get_vault_path()
    note_path = find_note(vault, args.note_id)

    if not note_path:
        print(f"Error: 노트를 찾을 수 없습니다: {args.note_id}", file=sys.stderr)
        sys.exit(1)

    content = note_path.read_text(encoding="utf-8")
    content += "\n\n" + args.content

    # modified 날짜 업데이트
    now = datetime.now().isoformat()
    content = re.sub(r'modified: .+', f'modified: {now}', content)

    note_path.write_text(content, encoding="utf-8")
    print(f"Updated: {note_path}")

def update_note(args):
    """노트 내용 전체 교체"""
    vault = get_vault_path()
    note_path = find_note(vault, args.note_id)

    if not note_path:
        print(f"Error: 노트를 찾을 수 없습니다: {args.note_id}", file=sys.stderr)
        sys.exit(1)

    content = note_path.read_text(encoding="utf-8")

    # frontmatter 추출
    match = re.match(r'(---\n.*?\n---\n)', content, re.DOTALL)
    if match:
        frontmatter = match.group(1)
        # modified 날짜 업데이트
        now = datetime.now().isoformat()
        frontmatter = re.sub(r'modified: .+', f'modified: {now}', frontmatter)

        # title 추출
        title_match = re.search(r'title: "(.+)"', frontmatter)
        title = title_match.group(1) if title_match else "Untitled"

        new_content = frontmatter + f"# {title}\n\n" + args.content
        note_path.write_text(new_content, encoding="utf-8")
        print(f"Updated: {note_path}")
    else:
        print("Error: frontmatter를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

def search_notes(args):
    """노트 검색"""
    vault = get_vault_path()
    results = []

    for md_file in vault.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")

        if args.tag:
            # 태그로 검색
            if f'"{args.tag}"' in content or f"'{args.tag}'" in content:
                results.append(md_file)
        elif args.query:
            # 키워드 검색
            if args.query.lower() in content.lower():
                results.append(md_file)

    if results:
        print(f"Found {len(results)} notes:")
        for r in results:
            print(f"  - {r.relative_to(vault)}")
    else:
        print("No notes found.")

def list_notes(args):
    """타입별 노트 목록"""
    vault = get_vault_path()

    if args.type:
        folder = TYPE_FOLDERS.get(args.type)
        if folder:
            folder_path = vault / folder
            if folder_path.exists():
                notes = list(folder_path.glob("*.md"))
                print(f"{args.type} notes ({len(notes)}):")
                for n in sorted(notes, reverse=True)[:20]:
                    print(f"  - {n.name}")
            else:
                print(f"Folder not found: {folder}")
    else:
        # 모든 타입 표시
        for note_type, folder in TYPE_FOLDERS.items():
            folder_path = vault / folder
            if folder_path.exists():
                count = len(list(folder_path.glob("*.md")))
                print(f"{note_type}: {count} notes")

def link_notes(args):
    """노트 간 링크 추가"""
    vault = get_vault_path()
    source = find_note(vault, args.source)
    target = find_note(vault, args.target)

    if not source:
        print(f"Error: 소스 노트를 찾을 수 없습니다: {args.source}", file=sys.stderr)
        sys.exit(1)
    if not target:
        print(f"Error: 타겟 노트를 찾을 수 없습니다: {args.target}", file=sys.stderr)
        sys.exit(1)

    # 타겟 노트 제목 추출
    target_content = target.read_text(encoding="utf-8")
    title_match = re.search(r'title: "(.+)"', target_content)
    target_title = title_match.group(1) if title_match else target.stem

    # 소스 노트에 링크 추가
    source_content = source.read_text(encoding="utf-8")
    link = f"\n\n[[{target_title}]]"
    source_content += link

    # links 배열 업데이트
    target_id_match = re.search(r'id: "(\d+)"', target_content)
    if target_id_match:
        target_id = target_id_match.group(1)
        source_content = re.sub(
            r'links: \[([^\]]*)\]',
            lambda m: f'links: [{m.group(1)}, "{target_id}"]' if m.group(1) else f'links: ["{target_id}"]',
            source_content
        )

    source.write_text(source_content, encoding="utf-8")
    print(f"Linked: {source.name} -> {target.name}")

def find_note(vault, identifier):
    """ID 또는 제목으로 노트 찾기"""
    for md_file in vault.rglob("*.md"):
        if identifier in md_file.name:
            return md_file
        content = md_file.read_text(encoding="utf-8")
        if f'id: "{identifier}"' in content:
            return md_file
    return None

def main():
    parser = argparse.ArgumentParser(description="Obsidian Zettelkasten Note Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    create_parser = subparsers.add_parser("create", help="새 노트 생성")
    create_parser.add_argument("title", help="노트 제목")
    create_parser.add_argument("--type", "-t", choices=TYPE_FOLDERS.keys(), help="노트 타입")
    create_parser.add_argument("--content", "-c", help="노트 내용")
    create_parser.add_argument("--tags", help="태그 (쉼표 구분)")
    create_parser.set_defaults(func=create_note)

    # append
    append_parser = subparsers.add_parser("append", help="노트에 내용 추가")
    append_parser.add_argument("note_id", help="노트 ID 또는 제목")
    append_parser.add_argument("--content", "-c", required=True, help="추가할 내용")
    append_parser.set_defaults(func=append_note)

    # update
    update_parser = subparsers.add_parser("update", help="노트 내용 교체")
    update_parser.add_argument("note_id", help="노트 ID 또는 제목")
    update_parser.add_argument("--content", "-c", required=True, help="새 내용")
    update_parser.set_defaults(func=update_note)

    # search
    search_parser = subparsers.add_parser("search", help="노트 검색")
    search_parser.add_argument("query", nargs="?", help="검색어")
    search_parser.add_argument("--tag", help="태그로 검색")
    search_parser.set_defaults(func=search_notes)

    # list
    list_parser = subparsers.add_parser("list", help="노트 목록")
    list_parser.add_argument("--type", "-t", choices=TYPE_FOLDERS.keys(), help="노트 타입")
    list_parser.set_defaults(func=list_notes)

    # link
    link_parser = subparsers.add_parser("link", help="노트 간 링크")
    link_parser.add_argument("source", help="소스 노트 ID")
    link_parser.add_argument("target", help="타겟 노트 ID")
    link_parser.set_defaults(func=link_notes)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
