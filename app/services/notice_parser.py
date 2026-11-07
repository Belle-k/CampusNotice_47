import re
from datetime import datetime
from io import BytesIO
from pathlib import Path


DATE_PATTERN = re.compile(
    r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"
    r"|\d{4}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*\d{1,2}"
)


def extract_document_text(uploaded_file):
    """读取 PDF、DOCX、TXT 文件中的文本，不在服务器保存原文件。"""
    filename = (uploaded_file.filename or "").strip()
    suffix = Path(filename).suffix.lower()

    if not filename:
        raise ValueError("请先选择一个文件。")

    raw_data = uploaded_file.read()
    if not raw_data:
        raise ValueError("上传的文件为空，请重新选择。")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(raw_data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise ValueError("PDF 读取失败，请检查文件是否损坏或受密码保护。") from exc

        if not text.strip():
            raise ValueError(
                "没有提取到 PDF 文字。该文件可能是扫描图片版，当前版本暂不支持 OCR。"
            )

    elif suffix == ".docx":
        try:
            from docx import Document
            document = Document(BytesIO(raw_data))
            parts = [
                paragraph.text.strip()
                for paragraph in document.paragraphs
                if paragraph.text.strip()
            ]
            for table in document.tables:
                for row in table.rows:
                    values = [cell.text.strip() for cell in row.cells]
                    if any(values):
                        parts.append(" | ".join(values))
            text = "\n".join(parts)
        except Exception as exc:
            raise ValueError("Word 文件读取失败，请确认上传的是 .docx 文件。") from exc

    elif suffix == ".txt":
        try:
            text = raw_data.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = raw_data.decode("gb18030")
            except UnicodeDecodeError as exc:
                raise ValueError("TXT 编码无法识别，请另存为 UTF-8 后重试。") from exc

    else:
        raise ValueError("文件格式不支持，请上传 PDF、DOCX 或 TXT 文件。")

    text = text.replace("\x00", "").strip()
    if not text:
        raise ValueError("文件中没有可读取的文字内容。")

    return text


def normalize_date(value):
    """将中文或常见数字日期格式转换为 YYYY-MM-DD。"""
    value = re.sub(r"\s+", "", value)

    if "年" in value:
        value = value.replace("年", "-").replace("月", "-").replace("日", "")
    else:
        value = value.replace("/", "-").replace(".", "-")

    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


def detect_category(text):
    """根据关键词给出通知类别候选，最终由用户确认。"""
    rules = [
        ("竞赛", ["竞赛", "比赛", "大赛", "创新创业"]),
        ("学习", ["课程", "考试", "教学", "学分", "选课"]),
        ("活动", ["活动", "志愿者", "志愿服务", "讲座"]),
        ("奖助", ["奖学金", "助学金", "评优", "资助"]),
        ("就业", ["招聘", "就业", "实习", "求职"]),
    ]
    for category, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return category
    return "其他"


def detect_publisher(text):
    """提取明确标注的发布单位。"""
    patterns = [
        r"(?:发布单位|发布部门|主办单位|承办单位|通知单位)\s*[:：]\s*([^\n；;]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip(" 。；;")
    return ""


def _guess_deadline_label(context):
    """根据日期附近的文字给出事项名称候选。"""
    if "报名" in context:
        return "报名截止"
    if "材料" in context or "提交" in context:
        return "材料提交截止"
    if "作品" in context:
        return "作品提交截止"
    if "申请" in context:
        return "申请截止"
    if "缴费" in context:
        return "缴费截止"
    if "面试" in context:
        return "面试时间"
    if "考试" in context:
        return "考试时间"
    if "活动" in context:
        return "活动时间"
    if "截止" in context:
        return "事项截止"
    return "重要日期"



def detect_deadlines(text):
    """提取有明确事项含义的日期，过滤落款日期。"""

    date_pattern = re.compile(
        r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"
        r"|\d{4}[-/.]\d{1,2}[-/.]\d{1,2}"
    )

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    def classify(line):
        line = re.sub(r"\s+", "", line)

        # 优先识别具体事项，避免相邻关键词干扰
        if any(k in line for k in [
            "材料提交", "提交材料", "材料截止", "材料递交"
        ]):
            return "材料提交截止"

        if any(k in line for k in [
            "报名截止", "报名时间", "报名要求",
            "线上报名", "完成报名", "报名日期"
        ]):
            return "报名截止"

        if any(k in line for k in [
            "作品提交", "作品截止"
        ]):
            return "作品提交截止"

        if any(k in line for k in [
            "申请截止", "申请时间"
        ]):
            return "申请截止"

        if any(k in line for k in [
            "缴费截止", "缴费时间"
        ]):
            return "缴费截止"

        if any(k in line for k in [
            "活动时间", "活动日期", "活动安排"
        ]):
            return "活动时间"

        if any(k in line for k in [
            "考试时间", "考试日期"
        ]):
            return "考试时间"

        if any(k in line for k in [
            "面试时间", "面试日期"
        ]):
            return "面试时间"

        return None

    results = []
    seen = set()

    for i, line in enumerate(lines):

        for match in date_pattern.finditer(line):

            normalized = normalize_date(match.group())

            if not normalized:
                continue

            label = classify(line)

            # 日期单独成行时，只参考相邻明确事项
            if not label:
                candidates = []

                if i > 0:
                    previous = classify(lines[i - 1])
                    if previous:
                        candidates.append(previous)

                if i + 1 < len(lines):
                    following = classify(lines[i + 1])
                    if following:
                        candidates.append(following)

                if len(set(candidates)) == 1:
                    label = candidates[0]

            # 没有明确事项含义的日期不作为待办
            if not label:
                continue

            key = (label, normalized)

            if key in seen:
                continue

            seen.add(key)

            results.append({
                "label": label,
                "deadline_date": normalized,
                "note": line
            })

    return results



def parse_notice_text(text):
    """提取通知标题、类别、发布单位、正文和日期候选。"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("通知正文为空，无法提取信息。")

    title = lines[0]
    if title in {"通知", "公告"} and len(lines) > 1:
        title = lines[1]
    title = title[:100]

    return {
        "title": title,
        "category": detect_category(text),
        "publisher": detect_publisher(text),
        "content": text.strip(),
        "deadlines": detect_deadlines(text)
    }
