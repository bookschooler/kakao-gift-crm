"""
Google Slides 호환 v01 생성 스크립트
- 비표준 XML 요소 제거 (custGeom, a14:, a16: 네임스페이스)
- 슬라이드 크기 16:9 명시 확인
- 폰트 맑은 고딕 유지 (Google Slides 지원)
"""

import shutil
import zipfile
import os
import re

BASE   = "C:/Users/user/Desktop/pjt/portfolio/kakao_gift"
SRC    = f"{BASE}/kakao_gift_analysis_selfmade.pptx"
DST    = f"{BASE}/kakao_gift_analysis_selfmade_v01.pptx"
TMP    = f"{BASE}/_pptx_tmp"

# 제거할 비표준 네임스페이스 패턴
REMOVE_NS = [
    r'xmlns:a14="[^"]*"',
    r'xmlns:a16="[^"]*"',
    r'xmlns:mc="[^"]*"',
]

# 제거할 비표준 엘리먼트 패턴 (태그 전체)
REMOVE_TAGS = [
    r'<mc:AlternateContent[^>]*>.*?</mc:AlternateContent>',
    r'<a14:[^/]*/?>',
    r'</a14:[^>]*>',
    r'<a16:[^/]*/?>',
    r'</a16:[^>]*>',
    r'<custGeom[^>]*>.*?</custGeom>',
]

def clean_xml(content: str) -> str:
    for pattern in REMOVE_TAGS:
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    for pattern in REMOVE_NS:
        content = re.sub(pattern, '', content)
    return content

def make_v01():
    # 1. 원본 복사
    shutil.copy2(SRC, DST)

    # 2. zip으로 열어서 XML 정리
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP)

    with zipfile.ZipFile(DST, 'r') as z:
        z.extractall(TMP)

    # 3. 모든 XML 파일 정리
    cleaned = 0
    for root, dirs, files in os.walk(TMP):
        for fname in files:
            if fname.endswith('.xml') or fname.endswith('.rels'):
                fpath = os.path.join(root, fname)
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                new_content = clean_xml(content)
                if new_content != content:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    cleaned += 1

    print(f"XML cleaned: {cleaned} files")

    # 4. 다시 zip으로 압축
    os.remove(DST)
    with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(TMP):
            for fname in files:
                fpath = os.path.join(root, fname)
                arcname = os.path.relpath(fpath, TMP)
                z.write(fpath, arcname)

    # 5. 임시 폴더 정리
    shutil.rmtree(TMP, ignore_errors=True)

    # 6. 검증
    from pptx import Presentation
    prs = Presentation(DST)
    print(f"v01 slides: {len(prs.slides)}")
    print(f"v01 size: {prs.slide_width} x {prs.slide_height} EMU")
    print(f"Saved: {DST}")

if __name__ == "__main__":
    make_v01()
