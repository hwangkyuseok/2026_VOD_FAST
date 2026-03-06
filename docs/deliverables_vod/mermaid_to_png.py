"""
mermaid_to_png.py
-  마크다운 파일에서 ```mermaid 블록을 찾아 PNG 이미지로 렌더링한 뒤
   코드 블록 바로 아래에 이미지 링크를 삽입한다.
- 실행: python mermaid_to_png.py
"""
import os
import re
import subprocess
import shutil
import sys

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(DOCS_DIR, "mermaid_images")

os.makedirs(IMG_DIR, exist_ok=True)

MMDC = shutil.which("mmdc") or shutil.which("mmdc.cmd")
if MMDC is None:
    print("ERROR: mmdc not found. Install: npm install -g @mermaid-js/mermaid-cli", file=sys.stderr)
    sys.exit(1)

print(f"mmdc found: {MMDC}")

# 마크다운 ```mermaid ... ``` 블록 패턴
MERMAID_BLOCK = re.compile(r'(```mermaid\r?\n(.*?)\r?\n```)', re.DOTALL)

def render_mermaid(code: str, out_path: str) -> bool:
    """mmdc 로 mermaid 코드를 PNG 이미지로 변환. 성공 시 True."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False,
                                     encoding='utf-8') as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = subprocess.run(
            [MMDC, "-i", tmp_path, "-o", out_path,
             "--backgroundColor", "white",
             "--width", "1200"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"  mmdc error: {result.stderr[:200]}")
            return False
        return os.path.exists(out_path)
    except subprocess.TimeoutExpired:
        print("  mmdc timeout")
        return False
    finally:
        os.unlink(tmp_path)


def process_file(md_path: str):
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    filename_base = os.path.splitext(os.path.basename(md_path))[0]
    matches = list(MERMAID_BLOCK.finditer(content))

    if not matches:
        print(f"  (no mermaid blocks)")
        return False

    print(f"  Found {len(matches)} mermaid block(s)")

    offset = 0
    new_content = content
    inserted = 0

    for idx, m in enumerate(matches):
        # 이미 이미지가 삽입되어 있는지 확인 (중복 방지)
        img_marker = f"<!-- mermaid-img-{filename_base}-{idx+1} -->"
        if img_marker in new_content:
            print(f"  Block {idx+1}: already has image, skipping")
            continue

        block_text = m.group(1)   # 전체 ```mermaid ... ``` 텍스트
        mermaid_code = m.group(2)  # 내부 코드만

        img_name = f"{filename_base}_{idx+1:02d}.png"
        img_path = os.path.join(IMG_DIR, img_name)

        print(f"  Block {idx+1}: rendering → {img_name} ...", end=" ", flush=True)
        ok = render_mermaid(mermaid_code, img_path)

        if ok:
            print("OK")
            # 상대 경로 (마크다운 기준)
            rel_path = os.path.relpath(img_path, DOCS_DIR).replace("\\", "/")
            insert_text = f"\n\n{img_marker}\n![다이어그램 {idx+1}]({rel_path})\n"
        else:
            print("FAILED (skipping image insertion)")
            continue

        # 블록 종료 위치 이후에 삽입 (offset 보정 포함)
        abs_end = m.end() + offset
        new_content = new_content[:abs_end] + insert_text + new_content[abs_end:]
        offset += len(insert_text)
        inserted += 1

    if inserted > 0:
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  → Saved ({inserted} image(s) inserted)")
        return True
    return False


def main():
    md_files = sorted([
        os.path.join(DOCS_DIR, f)
        for f in os.listdir(DOCS_DIR)
        if f.endswith('.md') and f != 'README.md'
        and not f.startswith('.')
    ])

    changed = []
    for md_path in md_files:
        fname = os.path.basename(md_path)
        print(f"\nProcessing: {fname}")
        if process_file(md_path):
            changed.append(fname)

    print(f"\n{'='*50}")
    print(f"Done. {len(changed)} file(s) updated:")
    for f in changed:
        print(f"  - {f}")


if __name__ == "__main__":
    main()
