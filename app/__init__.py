
import os
from datetime import datetime, date, timedelta

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash
)

from .services.database import get_db, close_db, init_db
from .services.notice_parser import extract_document_text, parse_notice_text


def save_deadlines(db, notice_id, old_status=None):
    """保存一条通知的多个截止事项"""

    old_status = old_status or {}

    labels = request.form.getlist("deadline_label[]")
    dates = request.form.getlist("deadline_date[]")
    notes = request.form.getlist("deadline_note[]")

    for label, deadline_date, note in zip(labels, dates, notes):

        label = label.strip()
        note = note.strip()

        if not deadline_date:
            continue

        if not label:
            label = "截止事项"

        try:
            datetime.strptime(deadline_date, "%Y-%m-%d")
        except ValueError:
            continue

        status = old_status.get((label, deadline_date), 0)

        db.execute("""
            INSERT INTO notice_deadlines
            (notice_id, label, deadline_date, status, note)
            VALUES (?, ?, ?, ?, ?)
        """, (notice_id, label, deadline_date, status, note))


def create_app():

    app = Flask(__name__)

    app.config["SECRET_KEY"] = "campusnotice-local-demo-key"
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 单个上传文件最大 10 MB

    os.makedirs(app.instance_path, exist_ok=True)

    app.config["DATABASE"] = os.path.join(
        app.instance_path, "campusnotice.db"
    )

    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    # 首页
    @app.route("/")
    def index():

        db = get_db()

        today = date.today()
        seven_days = (today + timedelta(days=7)).isoformat()

        total_notices = db.execute(
            "SELECT COUNT(*) FROM notices"
        ).fetchone()[0]

        pending_deadlines = db.execute("""
            SELECT COUNT(*) FROM notice_deadlines
            WHERE status = 0
        """).fetchone()[0]

        upcoming_count = db.execute("""
            SELECT COUNT(*) FROM notice_deadlines
            WHERE status = 0
            AND deadline_date BETWEEN ? AND ?
        """, (today.isoformat(), seven_days)).fetchone()[0]

        recent_notices = db.execute("""
            SELECT * FROM notices
            ORDER BY created_at DESC
            LIMIT 5
        """).fetchall()

        upcoming_items = db.execute("""
            SELECT d.*, n.title
            FROM notice_deadlines d
            JOIN notices n ON d.notice_id = n.id
            WHERE d.status = 0
            AND d.deadline_date >= ?
            ORDER BY d.deadline_date ASC
            LIMIT 5
        """, (today.isoformat(),)).fetchall()

        return render_template(
            "index.html",
            active_page="dashboard",
            total_notices=total_notices,
            pending_deadlines=pending_deadlines,
            upcoming_count=upcoming_count,
            recent_notices=recent_notices,
            upcoming_items=upcoming_items
        )

    # 通知列表与搜索
    @app.route("/notices")
    def notices_page():

        db = get_db()
        keyword = request.args.get("q", "").strip()

        sql = """
            SELECT n.*,
                (SELECT COUNT(*) FROM notice_deadlines d
                 WHERE d.notice_id = n.id) AS deadline_count,
                (SELECT COUNT(*) FROM notice_deadlines d
                 WHERE d.notice_id = n.id AND d.status = 0)
                 AS pending_count
            FROM notices n
        """

        params = []

        if keyword:
            sql += """
                WHERE n.title LIKE ?
                OR n.category LIKE ?
                OR n.publisher LIKE ?
                OR n.content LIKE ?
            """
            value = f"%{keyword}%"
            params = [value, value, value, value]

        sql += " ORDER BY n.created_at DESC"

        rows = db.execute(sql, params).fetchall()

        notices = []

        for row in rows:

            item = dict(row)

            item["deadlines"] = db.execute("""
                SELECT * FROM notice_deadlines
                WHERE notice_id = ?
                ORDER BY deadline_date ASC
            """, (row["id"],)).fetchall()

            notices.append(item)

        return render_template(
            "notices.html",
            active_page="notices",
            notices=notices,
            keyword=keyword
        )

    # 新增通知
    @app.route("/notices/new", methods=["GET", "POST"])
    def create_notice():

        if request.method == "POST":

            title = request.form.get("title", "").strip()
            category = request.form.get("category", "其他")
            publisher = request.form.get("publisher", "").strip()
            content = request.form.get("content", "").strip()

            if not title or not content:
                flash("通知标题和内容不能为空。", "error")
                return redirect(url_for("create_notice"))

            db = get_db()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor = db.execute("""
                INSERT INTO notices
                (title, category, publisher, content,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, category, publisher, content, now, now))

            save_deadlines(db, cursor.lastrowid)

            db.commit()

            flash("通知添加成功！", "success")

            return redirect(url_for("notices_page"))

        return render_template(
            "notice_form.html",
            active_page="notices",
            notice=None,
            deadlines=[]
        )

    # 编辑通知
    @app.route("/notices/<int:notice_id>/edit",
               methods=["GET", "POST"])
    def edit_notice(notice_id):

        db = get_db()

        notice = db.execute(
            "SELECT * FROM notices WHERE id = ?",
            (notice_id,)
        ).fetchone()

        if notice is None:
            flash("没有找到这条通知。", "error")
            return redirect(url_for("notices_page"))

        if request.method == "POST":

            title = request.form.get("title", "").strip()
            category = request.form.get("category", "其他")
            publisher = request.form.get("publisher", "").strip()
            content = request.form.get("content", "").strip()

            if not title or not content:
                flash("通知标题和内容不能为空。", "error")
                return redirect(url_for(
                    "edit_notice", notice_id=notice_id
                ))

            old_rows = db.execute("""
                SELECT label, deadline_date, status
                FROM notice_deadlines
                WHERE notice_id = ?
            """, (notice_id,)).fetchall()

            old_status = {
                (row["label"], row["deadline_date"]): row["status"]
                for row in old_rows
            }

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            db.execute("""
                UPDATE notices
                SET title = ?, category = ?, publisher = ?,
                    content = ?, updated_at = ?
                WHERE id = ?
            """, (
                title, category, publisher,
                content, now, notice_id
            ))

            db.execute("""
                DELETE FROM notice_deadlines
                WHERE notice_id = ?
            """, (notice_id,))

            save_deadlines(db, notice_id, old_status)

            db.commit()

            flash("通知修改成功！", "success")

            return redirect(url_for("notices_page"))

        deadlines = db.execute("""
            SELECT * FROM notice_deadlines
            WHERE notice_id = ?
            ORDER BY deadline_date ASC
        """, (notice_id,)).fetchall()

        return render_template(
            "notice_form.html",
            active_page="notices",
            notice=notice,
            deadlines=deadlines
        )

    # 删除通知
    @app.route("/notices/<int:notice_id>/delete",
               methods=["POST"])
    def delete_notice(notice_id):

        db = get_db()

        db.execute(
            "DELETE FROM notices WHERE id = ?",
            (notice_id,)
        )

        db.commit()

        flash("通知已删除。", "success")

        return redirect(url_for("notices_page"))

    # 切换截止事项完成状态
    @app.route("/deadlines/<int:deadline_id>/toggle",
               methods=["POST"])
    def toggle_deadline(deadline_id):

        db = get_db()

        db.execute("""
            UPDATE notice_deadlines
            SET status = CASE WHEN status = 0 THEN 1 ELSE 0 END
            WHERE id = ?
        """, (deadline_id,))

        db.commit()

        flash("事项状态已更新。", "success")

        return redirect(url_for("notices_page"))

    # 智能通知导入：上传文件并提取候选信息
    @app.route("/import", methods=["GET", "POST"])
    def import_page():
        if request.method == "GET":
            return render_template("import.html", active_page="import")

        uploaded_file = request.files.get("notice_file")
        if uploaded_file is None or not uploaded_file.filename:
            flash("请先选择一个 PDF、DOCX 或 TXT 文件。", "error")
            return redirect(url_for("import_page"))

        try:
            text = extract_document_text(uploaded_file)
            notice_data = parse_notice_text(text)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("import_page"))

        return render_template(
            "import_preview.html",
            active_page="import",
            notice=notice_data,
            source_filename=uploaded_file.filename
        )

    # 确认识别结果并保存到现有 SQLite 数据库
    @app.route("/import/confirm", methods=["POST"])
    def confirm_import():
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "其他").strip()
        publisher = request.form.get("publisher", "").strip()
        content = request.form.get("content", "").strip()

        allowed_categories = {"活动", "竞赛", "学习", "奖助", "就业", "其他"}
        if category not in allowed_categories:
            category = "其他"

        labels = request.form.getlist("deadline_label[]")
        dates = request.form.getlist("deadline_date[]")
        notes = request.form.getlist("deadline_note[]")

        deadline_rows = []
        invalid_date = False

        for label, deadline_date, note in zip(labels, dates, notes):
            label = label.strip() or "截止事项"
            deadline_date = deadline_date.strip()
            note = note.strip()

            if not deadline_date:
                continue

            try:
                datetime.strptime(deadline_date, "%Y-%m-%d")
            except ValueError:
                invalid_date = True

            deadline_rows.append({
                "label": label,
                "deadline_date": deadline_date,
                "note": note
            })

        notice_data = {
            "title": title,
            "category": category,
            "publisher": publisher,
            "content": content,
            "deadlines": deadline_rows
        }

        if not title or not content:
            flash("通知标题和正文不能为空，请检查后再保存。", "error")
            return render_template(
                "import_preview.html",
                active_page="import",
                notice=notice_data,
                source_filename="当前编辑内容"
            )

        if invalid_date:
            flash("日期格式不正确，请使用 YYYY-MM-DD 格式。", "error")
            return render_template(
                "import_preview.html",
                active_page="import",
                notice=notice_data,
                source_filename="当前编辑内容"
            )

        db = get_db()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            cursor = db.execute("""
                INSERT INTO notices
                (title, category, publisher, content, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, category, publisher, content, now, now))

            notice_id = cursor.lastrowid

            for item in deadline_rows:
                db.execute("""
                    INSERT INTO notice_deadlines
                    (notice_id, label, deadline_date, status, note)
                    VALUES (?, ?, ?, 0, ?)
                """, (
                    notice_id,
                    item["label"],
                    item["deadline_date"],
                    item["note"]
                ))

            db.commit()
        except Exception:
            db.rollback()
            raise

        flash("通知文件导入成功，已保存到通知管理。", "success")
        return redirect(url_for("notices_page"))

    @app.errorhandler(413)
    def file_too_large(error):
        flash("文件超过 10 MB，请压缩文件或选择较小的文件。", "error")
        return redirect(url_for("import_page"))

    # 截止日历页面（下一阶段开发）
    @app.route("/calendar")
    def calendar_page():
        return render_template(
            "placeholder.html",
            active_page="calendar",
            page_title="截止日历",
            page_description="集中查看报名、材料提交和活动截止时间。"
        )

    # 数据统计页面（下一阶段开发）
    @app.route("/statistics")
    def statistics_page():
        return render_template(
            "placeholder.html",
            active_page="statistics",
            page_title="数据统计",
            page_description="通过统计图表了解通知类别和事项处理情况。"
        )

    return app
