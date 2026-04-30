업로드 기능 설계 요약
1. 목적
업로드 API는 파일을 저장하는 것에서 끝나지 않고, 이후 질문답변과 Edit에 바로 사용할 수 있도록 내부 변환 산출물을 생성한다.
지원 확장자:
.hwpx
.docx
.pptx
.xlsx
.pdf
업로드 완료 후 파일은 반드시 다음 상태 중 하나가 된다.
converted
conversion_failed
2. 업로드 시 생성되는 것
사용자가 보는 파일:
/workspace/files/report.docx
내부 생성물:
/workspace/.converted/file_001/
  source.pdf
  manifest.json
  pages/
    page_001.png
    page_002.png
Registry:
/workspace/.registry/files.json
XLSX는 추가로 생성한다.
/workspace/.converted/file_001/
  workbook_index.json
  xlsx/
    sheets/
      sheet_0001/
        sheet.json
        pages/
          page_001.png
3. 업로드 처리 순서
1. 파일 수신
2. 확장자 검증
3. /workspace/files에 원본 저장
4. file_id 생성
5. registry에 uploaded 상태로 등록
6. /workspace/.converted/{file_id}/ 생성
7. PDF 변환
   - hwpx/docx/pptx/xlsx → source.pdf
   - pdf → source.pdf로 복사 또는 참조
8. PDF를 페이지별 이미지로 변환
9. manifest.json 생성
10. xlsx이면 workbook_index.json, sheet.json 생성
11. registry를 converted 상태로 갱신
12. 응답 반환
4. Registry 역할
Registry는 사용자가 보는 파일과 내부 변환 결과를 연결한다.
{
  "file_id": "file_001",
  "visible_path": "/workspace/files/report.docx",
  "visible_name": "report.docx",
  "file_type": "docx",
  "status": "converted",
  "converted_dir": "/workspace/.converted/file_001",
  "manifest_path": "/workspace/.converted/file_001/manifest.json"
}
workflow는 파일명으로 .converted 경로를 추측하지 않는다.
file_id 또는 visible_path
  → registry lookup
  → manifest_path
  → page images
5. Manifest 역할
Manifest는 변환된 페이지 이미지 목록을 가진다.
{
  "file_id": "file_001",
  "source_filename": "report.docx",
  "source_path": "/workspace/files/report.docx",
  "file_type": "docx",
  "pdf_path": "/workspace/.converted/file_001/source.pdf",
  "pages": [
    {
      "page_number": 1,
      "image_filename": "page_001.png",
      "image_path": "/workspace/.converted/file_001/pages/page_001.png"
    },
    {
      "page_number": 2,
      "image_filename": "page_002.png",
      "image_path": "/workspace/.converted/file_001/pages/page_002.png"
    }
  ],
  "status": "converted"
}
질문답변 workflow는 이 pages 목록을 사용해 VLM 병렬 스캔을 수행한다.
6. XLSX 추가 처리
XLSX는 시트가 많을 수 있으므로 업로드 시 구조 인덱스를 만든다.
workbook_index.json
sheet별 sheet.json
sheet별 page image
workbook_index.json 예:
{
  "file_id": "file_002",
  "source_filename": "budget.xlsx",
  "sheet_count": 500,
  "sheets": [
    {
      "sheet_id": "sheet_0001",
      "sheet_name": "Summary",
      "index": 0,
      "visible": true,
      "used_range": "A1:R120",
      "has_formulas": true,
      "formula_count": 42,
      "sheet_summary_path": "/workspace/.converted/file_002/xlsx/sheets/sheet_0001/sheet.json"
    }
  ]
}
이 구조 덕분에 XLSX 질문답변 시 전체 workbook을 LLM에 넣지 않고, sheet 단위 map-reduce를 수행할 수 있다.
7. 사용자에게 숨기는 것
사용자는 다음만 본다.
/workspace/files
/workspace/outputs
숨김:
/workspace/.converted
/workspace/.registry
/workspace/.jobs
/workspace/.cache
ls, cd에서도 내부 폴더는 보이지 않는다.
8. 업로드 API 응답
성공:
{
  "uploaded_files": [
    {
      "file_id": "file_001",
      "filename": "report.docx",
      "file_type": "docx",
      "status": "converted"
    }
  ]
}
실패:
{
  "uploaded_files": [
    {
      "file_id": "file_003",
      "filename": "broken.docx",
      "file_type": "docx",
      "status": "conversion_failed",
      "error": "LibreOffice conversion failed"
    }
  ]
}
9. 병렬처리
업로드는 파일 단위로 병렬 처리한다.
file_001.docx → PDF → images
file_002.pptx → PDF → images
file_003.xlsx → PDF → images
권장 동시성:
conversion_max_concurrency = 2~4
LibreOffice 변환은 무겁기 때문에 무제한 병렬처리는 피한다.
10. 업로드 완료 후 가능한 작업
업로드가 converted 상태가 되면 다음 기능을 사용할 수 있다.
질문답변:
  manifest의 page images를 VLM으로 스캔
Edit:
  원본 파일을 복사해 수정
  수정본을 다시 upload 처리와 동일하게 converted 처리
XLSX:
  workbook_index와 sheet.json 기반으로 시트별 분석
핵심은 이거다.
업로드 API는 원본 파일을 시스템이 사용할 수 있는 내부 표현으로 준비하는 단계다.
그 내부 표현은 registry + manifest + page images다.