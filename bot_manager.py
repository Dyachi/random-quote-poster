import json
import subprocess
from pathlib import Path


# ============================================================
# 文件
# ============================================================

BASE_DIR = Path(__file__).parent

SETTINGS_FILE = BASE_DIR / "settings.json"


# ============================================================
# 设置
# ============================================================

def load_settings():

    with open(
        SETTINGS_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def save_settings(settings):

    with open(
        SETTINGS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            settings,
            f,
            ensure_ascii=False,
            indent=4
        )


# ============================================================
# 查看设置
# ============================================================

def show_settings():

    settings = load_settings()

    print()
    print("===================================")
    print("当前 Bot 设置")
    print("===================================")

    print(
        f"模式：{settings.get('mode')}"
    )

    print(
        f"固定时间：{', '.join(settings.get('times', []))}"
    )

    print(
        f"每周：{', '.join(settings.get('weekly_days', []))}"
    )

    print(
        f"每月：{settings.get('monthly_days', [])}"
    )

    print(
        f"每年：{settings.get('yearly_dates', [])}"
    )

    print(
        f"固定间隔：{settings.get('interval_minutes')} 分钟"
    )

    print(
        f"随机间隔："
        f"{settings.get('random_interval_min_minutes')}"
        f" ～ "
        f"{settings.get('random_interval_max_minutes')}"
        f" 分钟"
    )

    print(
        f"时区：{settings.get('timezone')}"
    )

    print(
        f"提前排程：{settings.get('schedule_ahead_days')} 天"
    )

    print()


# ============================================================
# 修改每日时间
# ============================================================

def edit_daily():

    settings = load_settings()

    print()
    print("请输入每天发帖时间。")
    print("多个时间使用逗号分隔。")
    print()
    print("例如：")
    print("09:00,15:00,21:00")
    print()

    value = input("时间：").strip()

    if not value:
        print("❌ 不能为空。")
        return

    times = [
        x.strip()
        for x in value.split(",")
    ]

    settings["mode"] = "daily"
    settings["times"] = times

    save_settings(settings)

    print()
    print("✅ 已保存。")
    print(
        f"每天：{', '.join(times)}"
    )


# ============================================================
# 修改每周设置
# ============================================================

def edit_weekly():

    settings = load_settings()

    print()
    print("星期名称：")
    print("Monday Tuesday Wednesday Thursday")
    print("Friday Saturday Sunday")
    print()

    days = input(
        "星期："
    ).strip()

    times = input(
        "时间，例如 12:00,20:00："
    ).strip()

    settings["mode"] = "weekly"

    settings["weekly_days"] = [
        x.strip()
        for x in days.split(",")
    ]

    settings["times"] = [
        x.strip()
        for x in times.split(",")
    ]

    save_settings(settings)

    print()
    print("✅ 每周设置已保存。")


# ============================================================
# 修改每月设置
# ============================================================

def edit_monthly():

    settings = load_settings()

    print()
    print("请输入日期，例如：")
    print("1,15,30")
    print()

    days = input(
        "每月哪几天："
    ).strip()

    times = input(
        "时间，例如 12:00,21:00："
    ).strip()

    try:

        monthly_days = [
            int(x.strip())
            for x in days.split(",")
        ]

    except ValueError:

        print("❌ 日期格式错误。")
        return

    settings["mode"] = "monthly"

    settings["monthly_days"] = monthly_days

    settings["times"] = [
        x.strip()
        for x in times.split(",")
    ]

    save_settings(settings)

    print()
    print("✅ 每月设置已保存。")


# ============================================================
# 修改每年设置
# ============================================================

def edit_yearly():

    settings = load_settings()

    print()
    print("请输入日期，例如：")
    print("01-01,06-01,12-25")
    print()

    dates = input(
        "每年哪几天："
    ).strip()

    times = input(
        "时间，例如 12:00："
    ).strip()

    settings["mode"] = "yearly"

    settings["yearly_dates"] = [
        x.strip()
        for x in dates.split(",")
    ]

    settings["times"] = [
        x.strip()
        for x in times.split(",")
    ]

    save_settings(settings)

    print()
    print("✅ 每年设置已保存。")


# ============================================================
# 固定间隔
# ============================================================

def edit_interval():

    settings = load_settings()

    print()
    print("例如：")
    print("60   = 每小时")
    print("180  = 每3小时")
    print("360  = 每6小时")
    print("1440 = 每天")
    print()

    value = input(
        "每隔多少分钟："
    ).strip()

    try:
        minutes = int(value)

        if minutes <= 0:
            raise ValueError

    except ValueError:

        print("❌ 请输入大于 0 的整数。")
        return

    settings["mode"] = "interval"
    settings["interval_minutes"] = minutes

    save_settings(settings)

    print()
    print(
        f"✅ 已设置为每 {minutes} 分钟发一次。"
    )


# ============================================================
# 随机间隔
# ============================================================

def edit_random_interval():

    settings = load_settings()

    print()
    print("例如：")
    print("最短 4 小时 = 240 分钟")
    print("最长 8 小时 = 480 分钟")
    print()

    minimum = input(
        "最短间隔（分钟）："
    ).strip()

    maximum = input(
        "最长间隔（分钟）："
    ).strip()

    try:

        minimum = int(minimum)
        maximum = int(maximum)

        if minimum <= 0 or maximum < minimum:
            raise ValueError

    except ValueError:

        print("❌ 间隔设置错误。")
        return

    settings["mode"] = "random_interval"

    settings[
        "random_interval_min_minutes"
    ] = minimum

    settings[
        "random_interval_max_minutes"
    ] = maximum

    save_settings(settings)

    print()
    print(
        f"✅ 已设置为每 "
        f"{minimum}～{maximum} 分钟随机发一次。"
    )


# ============================================================
# 运行排程
# ============================================================

def run_poster():

    print()
    print("开始生成排程")
    print()
    print("请输入本次要生成未来几天的排程。")
    print("例如：")
    print("3  = 未来 3 天")
    print("7  = 未来 7 天")
    print("14 = 未来 14 天")
    print("30 = 未来 30 天")
    print()

    value = input(
        "排程天数："
    ).strip()

    try:
        ahead_days = int(value)

        if ahead_days <= 0:
            raise ValueError

    except ValueError:
        print()
        print("❌ 请输入大于 0 的整数。")
        return

    print()
    print(
        f"本次将生成未来 {ahead_days} 天的排程。"
    )
    print()

    try:
        import quote_poster

        quote_poster.schedule_future_quotes(
            ahead_days
        )

    except Exception as e:

        print()
        print("❌ 生成排程时发生错误：")
        print(e)

    print()

# ============================================================
# 取消全部排程
# ============================================================

def run_cancel():

    print()
    print("启动取消程序...")
    print()

    subprocess.run(
        [
            "python",
            str(
                BASE_DIR / "cancel_quotes.py"
            )
        ]
    )


# ============================================================
# 主菜单
# ============================================================

def main():

    while True:

        print()
        print("===================================")
        print("       RANDOM QUOTE BOT")
        print("===================================")
        print()

        print("[1] 查看当前设置")
        print("[2] 每天固定时间")
        print("[3] 每周固定时间")
        print("[4] 每月固定时间")
        print("[5] 每年固定时间")
        print("[6] 每隔固定时间")
        print("[7] 随机间隔发帖")
        print("[8] 立即生成排程（自定义天数）")
        print("[9] 取消全部排程")
        print("[0] 退出")
        print()

        choice = input(
            "请选择："
        ).strip()

        if choice == "1":

            show_settings()

        elif choice == "2":

            edit_daily()

        elif choice == "3":

            edit_weekly()

        elif choice == "4":

            edit_monthly()

        elif choice == "5":

            edit_yearly()

        elif choice == "6":

            edit_interval()

        elif choice == "7":

            edit_random_interval()

        elif choice == "8":

            run_poster()

        elif choice == "9":

            run_cancel()

        elif choice == "0":

            print()
            print("再见喵！")
            break

        else:

            print()
            print("❌ 无效选项。")


if __name__ == "__main__":
    main()