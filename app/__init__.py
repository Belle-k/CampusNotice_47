
from flask import Flask, render_template


def create_app():
    app = Flask(__name__)

    # 首页
    @app.route("/")
    def index():
        return render_template(
            "index.html",
            active_page="dashboard"
        )

    # 通知导入页面
    @app.route("/import")
    def import_page():
        return render_template(
            "placeholder.html",
            active_page="import",
            page_title="通知导入",
            page_description="上传校园通知文件，提取重要信息和截止日期。"
        )

    # 通知管理页面
    @app.route("/notices")
    def notices_page():
        return render_template(
            "placeholder.html",
            active_page="notices",
            page_title="通知管理",
            page_description="集中查看、搜索和管理已保存的校园通知。"
        )

    # 截止日历页面
    @app.route("/calendar")
    def calendar_page():
        return render_template(
            "placeholder.html",
            active_page="calendar",
            page_title="截止日历",
            page_description="集中查看报名、材料提交和活动截止时间。"
        )

    # 数据统计页面
    @app.route("/statistics")
    def statistics_page():
        return render_template(
            "placeholder.html",
            active_page="statistics",
            page_title="数据统计",
            page_description="通过统计图表了解通知类别和事项处理情况。"
        )

    return app
