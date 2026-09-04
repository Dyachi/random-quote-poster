import json
import random
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


# ============================================================
# 文件
# ============================================================

BASE_DIR = Path(__file__).parent

QUOTES_FILE = BASE_DIR / "quotes.json"
SETTINGS_FILE = BASE_DIR / "settings.json"
STATE_FILE = BASE_DIR / "quote_schedule_state.json"


# ============================================================
# 读取设置
# ============================================================

def load_settings():

    if not SETTINGS_FILE.exists():
        raise RuntimeError(
            f"找不到 settings.json：\n{SETTINGS_FILE}"
        )

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 读取语录
# ============================================================

def load_quotes():

    with open(QUOTES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    quotes = data["origin"]

    if not quotes:
        raise RuntimeError(
            "quotes.json 里的 origin 没有语录。"
        )

    return quotes


# ============================================================
# 状态
# ============================================================

def load_state():

    if not STATE_FILE.exists():
        return {
            "scheduled_slots": [],
            "scheduled_posts": {}
        }

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    state.setdefault("scheduled_slots", [])
    state.setdefault("scheduled_posts", {})

    return state


def save_state(state):

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# 清理已经过去的排程记录
# ============================================================

def cleanup_old_state(state, now):

    scheduled_posts = state.get(
        "scheduled_posts",
        {}
    )

    remaining = {}

    for slot_id, info in scheduled_posts.items():

        try:
            slot_dt = datetime.fromisoformat(slot_id)

            if slot_dt > now:
                remaining[slot_id] = info

        except Exception:
            # 无法解析的旧数据直接保留
            remaining[slot_id] = info

    state["scheduled_posts"] = remaining

    state["scheduled_slots"] = sorted(
        remaining.keys()
    )


# ============================================================
# tweetkit 排程
# ============================================================

def schedule_tweet(text, dt):

    timestamp = int(dt.timestamp())

    result = subprocess.run(
        [
            "tweetkit",
            "schedule",
            text,
            str(timestamp)
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:

        print("❌ 排程失败")

        if result.stderr.strip():
            print(result.stderr.strip())

        return None

    if not result.stdout.strip():

        print("⚠️ tweetkit 没有返回结果。")

        return None

    try:
        data = json.loads(
            result.stdout
        )

    except json.JSONDecodeError:

        print("⚠️ 无法解析 tweetkit 返回的数据：")
        print(result.stdout)

        return None

    scheduled_id = data.get(
        "scheduled_id"
    )

    if not scheduled_id:

        print("⚠️ 没有获得 scheduled_id：")
        print(result.stdout)

        return None

    print("✅ 排程成功")
    print(
        f"   时间：{dt.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print(
        f"   内容：{text}"
    )
    print(
        f"   ID：{scheduled_id}"
    )

    return scheduled_id


# ============================================================
# 时间解析
# ============================================================

def make_datetime(date_obj, time_string, timezone):

    hour, minute = map(
        int,
        time_string.split(":")
    )

    return datetime(
        date_obj.year,
        date_obj.month,
        date_obj.day,
        hour,
        minute,
        0,
        tzinfo=timezone
    )


# ============================================================
# 每日模式
# ============================================================

def generate_daily(settings, now, end_time):

    timezone = ZoneInfo(
        settings["timezone"]
    )

    times = settings.get(
        "times",
        []
    )

    result = []

    current_date = now.date()

    while current_date <= end_time.date():

        for time_string in times:

            dt = make_datetime(
                current_date,
                time_string,
                timezone
            )

            if now < dt <= end_time:
                result.append(dt)

        current_date += timedelta(days=1)

    return result


# ============================================================
# 每周模式
# ============================================================

def generate_weekly(settings, now, end_time):

    timezone = ZoneInfo(
        settings["timezone"]
    )

    days = settings.get(
        "weekly_days",
        []
    )

    times = settings.get(
        "times",
        []
    )

    result = []

    current_date = now.date()

    while current_date <= end_time.date():

        day_name = current_date.strftime(
            "%A"
        )

        if day_name in days:

            for time_string in times:

                dt = make_datetime(
                    current_date,
                    time_string,
                    timezone
                )

                if now < dt <= end_time:
                    result.append(dt)

        current_date += timedelta(days=1)

    return result


# ============================================================
# 每月模式
# ============================================================

def generate_monthly(settings, now, end_time):

    timezone = ZoneInfo(
        settings["timezone"]
    )

    days = settings.get(
        "monthly_days",
        []
    )

    times = settings.get(
        "times",
        []
    )

    result = []

    current_date = now.date()

    while current_date <= end_time.date():

        if current_date.day in days:

            for time_string in times:

                dt = make_datetime(
                    current_date,
                    time_string,
                    timezone
                )

                if now < dt <= end_time:
                    result.append(dt)

        current_date += timedelta(days=1)

    return result


# ============================================================
# 每年模式
# ============================================================

def generate_yearly(settings, now, end_time):

    timezone = ZoneInfo(
        settings["timezone"]
    )

    dates = settings.get(
        "yearly_dates",
        []
    )

    times = settings.get(
        "times",
        []
    )

    result = []

    current_date = now.date()

    while current_date <= end_time.date():

        month_day = current_date.strftime(
            "%m-%d"
        )

        if month_day in dates:

            for time_string in times:

                dt = make_datetime(
                    current_date,
                    time_string,
                    timezone
                )

                if now < dt <= end_time:
                    result.append(dt)

        current_date += timedelta(days=1)

    return result


# ============================================================
# 固定间隔模式
# ============================================================

def generate_interval(settings, now, end_time):

    interval_minutes = int(
        settings.get(
            "interval_minutes",
            360
        )
    )

    if interval_minutes <= 0:
        raise RuntimeError(
            "interval_minutes 必须大于 0。"
        )

    result = []

    current = now.replace(
        second=0,
        microsecond=0
    )

    current += timedelta(
        minutes=interval_minutes
    )

    while current <= end_time:

        result.append(current)

        current += timedelta(
            minutes=interval_minutes
        )

    return result


# ============================================================
# 随机间隔模式
# ============================================================

def generate_random_interval(
    settings,
    now,
    end_time
):

    minimum = int(
        settings.get(
            "random_interval_min_minutes",
            240
        )
    )

    maximum = int(
        settings.get(
            "random_interval_max_minutes",
            480
        )
    )

    if minimum <= 0:
        raise RuntimeError(
            "random_interval_min_minutes 必须大于 0。"
        )

    if maximum < minimum:
        raise RuntimeError(
            "random_interval_max_minutes 不能小于最小值。"
        )

    result = []

    current = now

    while True:

        delay = random.randint(
            minimum,
            maximum
        )

        current += timedelta(
            minutes=delay
        )

        current = current.replace(
            second=0,
            microsecond=0
        )

        if current > end_time:
            break

        result.append(current)

    return result


# ============================================================
# 根据设置生成所有时间
# ============================================================

def generate_schedule_times(
    settings,
    now,
    ahead_days=None
):

    if ahead_days is None:
        ahead_days = int(
            settings.get(
                "schedule_ahead_days",
                7
            )
        )
    else:
        ahead_days = int(ahead_days)

    if ahead_days <= 0:
        raise RuntimeError(
            "排程天数必须大于 0。"
        )

    end_time = now + timedelta(
        days=ahead_days
    )

    mode = settings.get(
        "mode",
        "daily"
    )

    if mode == "daily":

        return generate_daily(
            settings,
            now,
            end_time
        )

    if mode == "weekly":

        return generate_weekly(
            settings,
            now,
            end_time
        )

    if mode == "monthly":

        return generate_monthly(
            settings,
            now,
            end_time
        )

    if mode == "yearly":

        return generate_yearly(
            settings,
            now,
            end_time
        )

    if mode == "interval":

        return generate_interval(
            settings,
            now,
            end_time
        )

    if mode == "random_interval":

        return generate_random_interval(
            settings,
            now,
            end_time
        )

    raise RuntimeError(
        f"未知的 mode：{mode}"
    )

    if ahead_days is None:
        ahead_days = int(
            settings.get(
                "schedule_ahead_days",
                7
            )
        )
    else:
        ahead_days = int(ahead_days)

    if ahead_days <= 0:
        raise RuntimeError(
            "排程天数必须大于 0。"
        )

    end_time = now + timedelta(
        days=ahead_days
    )

    mode = settings.get(
        "mode",
        "daily"
    )

    if mode == "daily":

        return generate_daily(
            settings,
            now,
            end_time
        )

    if mode == "weekly":

        return generate_weekly(
            settings,
            now,
            end_time
        )

    if mode == "monthly":

        return generate_monthly(
            settings,
            now,
            end_time
        )

    if mode == "yearly":

        return generate_yearly(
            settings,
            now,
            end_time
        )

    if mode == "interval":

        return generate_interval(
            settings,
            now,
            end_time
        )

    if mode == "random_interval":

        return generate_random_interval(
            settings,
            now,
            end_time
        )

    raise RuntimeError(
        f"未知的 mode：{mode}"
    )


# ============================================================
# 开始排程
# ============================================================

def schedule_future_quotes(ahead_days=None):

    settings = load_settings()
    quotes = load_quotes()
    state = load_state()

    timezone = ZoneInfo(
        settings["timezone"]
    )

    now = datetime.now(
        timezone
    )

    # 清理已经过去的记录
    cleanup_old_state(
        state,
        now
    )

    save_state(state)

    scheduled_slots = set(
        state.get(
            "scheduled_slots",
            []
        )
    )

    schedule_times = generate_schedule_times(
        settings,
        now,
        ahead_days
    )

    schedule_times.sort()

    print()
    print(
        f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print(
        f"模式：{settings.get('mode')}"
    )

    print(
        f"未来排程数量：{len(schedule_times)}"
    )

    for post_dt in schedule_times:

        slot_id = post_dt.isoformat()

        if slot_id in scheduled_slots:
            continue

        quote = random.choice(
            quotes
        )

        print()
        print("-----------------------------------")
        print(
            f"准备排程：{post_dt.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(
            f"随机语录：{quote}"
        )

        scheduled_id = schedule_tweet(
            quote,
            post_dt
        )

        if scheduled_id:

            scheduled_slots.add(
                slot_id
            )

            state["scheduled_slots"] = sorted(
                scheduled_slots
            )

            state["scheduled_posts"][slot_id] = {
                "scheduled_id": scheduled_id,
                "quote": quote
            }

            save_state(state)


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":

    print()
    print("===================================")
    print("       RANDOM QUOTE POSTER")
    print("===================================")
    print()

    try:

        schedule_future_quotes()

        print()
        print("===================================")
        print("全部排程处理完成。")
        print("===================================")

    except Exception as e:

        print()
        print("❌ 程序发生错误：")
        print(e)

    print()
    input("按 Enter 键退出...")