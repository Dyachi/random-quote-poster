import json
import random
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


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

    with open(
        SETTINGS_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


# ============================================================
# 读取语录
# ============================================================

def load_quotes():

    if not QUOTES_FILE.exists():
        raise RuntimeError(
            f"找不到 quotes.json：\n{QUOTES_FILE}"
        )

    with open(
        QUOTES_FILE,
        "r",
        encoding="utf-8"
    ) as f:
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

    with open(
        STATE_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        state = json.load(f)

    state.setdefault(
        "scheduled_slots",
        []
    )

    state.setdefault(
        "scheduled_posts",
        {}
    )

    return state


def save_state(state):

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# 清理已经过去的排程
# ============================================================

def cleanup_old_state(state, now):

    scheduled_posts = state.get(
        "scheduled_posts",
        {}
    )

    remaining = {}

    for slot_id, info in scheduled_posts.items():

        try:

            slot_dt = datetime.fromisoformat(
                slot_id
            )

            if slot_dt > now:
                remaining[slot_id] = info

        except Exception:

            remaining[slot_id] = info

    state["scheduled_posts"] = remaining

    state["scheduled_slots"] = sorted(
        remaining.keys()
    )


# ============================================================
# X 登录 Cookie
# ============================================================

def parse_cookie_string(cookie_string):

    cookies = []

    for item in cookie_string.split(";"):

        item = item.strip()

        if "=" not in item:
            continue

        name, value = item.split(
            "=",
            1
        )

        name = name.strip()
        value = value.strip()

        if not name:
            continue

        cookies.append({
            "name": name,
            "value": value,
            "domain": ".x.com",
            "path": "/",
            "secure": True
        })

    return cookies


# ============================================================
# 检查登录状态
# ============================================================

def check_login(page):

    print()
    print("-----------------------------------")
    print("检查 X 登录状态")
    print("-----------------------------------")

    page.goto(
        "https://x.com/home",
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(5000)

    current_url = page.url

    print(
        f"X 当前页面：{current_url}"
    )

    # Cloudflare / 验证页面
    title = page.title()

    print(
        f"页面标题：{title}"
    )

    if "Just a moment" in title:

        raise RuntimeError(
            "X 返回了 Cloudflare 验证页面。"
        )

    # 如果仍然在登录页面
    if "/i/flow/login" in current_url:

        raise RuntimeError(
            "X 登录状态无效，Cookie 已失效。"
        )

    print("✅ X 登录状态看起来正常。")


# ============================================================
# Playwright 创建 X 排程
# ============================================================

def schedule_tweet(
    page,
    text,
    dt
):

    print()
    print("-----------------------------------")
    print("开始通过 X 网页创建排程")
    print("-----------------------------------")

    print(
        f"目标时间：{dt.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print(
        f"内容：{text}"
    )

    # --------------------------------------------------------
    # 打开 X 首页
    # --------------------------------------------------------

    page.goto(
        "https://x.com/home",
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(3000)

    # --------------------------------------------------------
    # 打开发帖窗口
    # --------------------------------------------------------

    compose_button = page.locator(
        '[data-testid="SideNav_NewTweet_Button"]'
    )

    try:

        compose_button.wait_for(
            state="visible",
            timeout=30000
        )

        compose_button.click()

    except PlaywrightTimeoutError:

        raise RuntimeError(
            "找不到 X 的发帖按钮。"
        )

    page.wait_for_timeout(1500)

    # --------------------------------------------------------
    # 输入语录
    # --------------------------------------------------------

    tweet_input = page.locator(
        '[data-testid="tweetTextarea_0"]'
    )

    try:

        tweet_input.wait_for(
            state="visible",
            timeout=30000
        )

        tweet_input.fill(text)

    except PlaywrightTimeoutError:

        raise RuntimeError(
            "找不到 X 的发帖输入框。"
        )

    page.wait_for_timeout(500)

    # --------------------------------------------------------
    # 点击排程按钮
    # --------------------------------------------------------

    schedule_button = page.locator(
        '[data-testid="scheduleOption"]'
    )

    try:

        schedule_button.wait_for(
            state="visible",
            timeout=15000
        )

        schedule_button.click()

    except PlaywrightTimeoutError:

        raise RuntimeError(
            "找不到 X 的排程按钮。"
        )

    page.wait_for_timeout(1000)

    # --------------------------------------------------------
    # 设置日期
    # --------------------------------------------------------

    date_string = dt.strftime(
        "%Y-%m-%d"
    )

    time_string = dt.strftime(
        "%H:%M"
    )

    date_input = page.locator(
        '[data-testid="scheduledDateField"]'
    )

    time_input = page.locator(
        '[data-testid="scheduledTimeField"]'
    )

    try:

        date_input.wait_for(
            state="visible",
            timeout=15000
        )

    except PlaywrightTimeoutError:

        raise RuntimeError(
            "找不到 X 的日期输入框。"
        )

    # 日期
    try:

        date_input.fill(
            date_string
        )

    except Exception:

        # 某些版本的 X 使用原生 input
        page.evaluate(
            """([selector, value]) => {
                const el = document.querySelector(selector);
                if (!el) return false;

                const setter =
                    Object.getOwnPropertyDescriptor(
                        HTMLInputElement.prototype,
                        "value"
                    ).set;

                setter.call(el, value);

                el.dispatchEvent(
                    new Event("input", {bubbles: true})
                );

                el.dispatchEvent(
                    new Event("change", {bubbles: true})
                );

                return true;
            }""",
            [
                '[data-testid="scheduledDateField"]',
                date_string
            ]
        )

    # 时间
    try:

        time_input.fill(
            time_string
        )

    except Exception:

        page.evaluate(
            """([selector, value]) => {
                const el = document.querySelector(selector);
                if (!el) return false;

                const setter =
                    Object.getOwnPropertyDescriptor(
                        HTMLInputElement.prototype,
                        "value"
                    ).set;

                setter.call(el, value);

                el.dispatchEvent(
                    new Event("input", {bubbles: true})
                );

                el.dispatchEvent(
                    new Event("change", {bubbles: true})
                );

                return true;
            }""",
            [
                '[data-testid="scheduledTimeField"]',
                time_string
            ]
        )

    page.wait_for_timeout(500)

    # --------------------------------------------------------
    # 点击确认排程
    # --------------------------------------------------------

    confirm_button = page.locator(
        '[data-testid="scheduledConfirmationPrimaryAction"]'
    )

    try:

        confirm_button.wait_for(
            state="visible",
            timeout=15000
        )

        confirm_button.click()

    except PlaywrightTimeoutError:

        raise RuntimeError(
            "找不到 X 的最终排程确认按钮。"
        )

    # 等待 X 完成请求
    page.wait_for_timeout(3000)

    print()
    print("✅ X 网页排程操作已完成")

    print(
        f"   时间：{dt.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print(
        f"   内容：{text}"
    )

    # --------------------------------------------------------
    # 返回一个本地标识
    #
    # 网页 UI 不一定直接把 scheduled_id 暴露给我们，
    # 所以这里使用时间作为 state 标识。
    # --------------------------------------------------------

    return f"web-{dt.strftime('%Y%m%d%H%M%S')}"


# ============================================================
# 时间解析
# ============================================================

def make_datetime(
    date_obj,
    time_string,
    timezone
):

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
# 每日
# ============================================================

def generate_daily(
    settings,
    now,
    end_time
):

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

        current_date += timedelta(
            days=1
        )

    return result


# ============================================================
# 每周
# ============================================================

def generate_weekly(
    settings,
    now,
    end_time
):

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

        current_date += timedelta(
            days=1
        )

    return result


# ============================================================
# 每月
# ============================================================

def generate_monthly(
    settings,
    now,
    end_time
):

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

        current_date += timedelta(
            days=1
        )

    return result


# ============================================================
# 每年
# ============================================================

def generate_yearly(
    settings,
    now,
    end_time
):

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

        current_date += timedelta(
            days=1
        )

    return result


# ============================================================
# 固定间隔
# ============================================================

def generate_interval(
    settings,
    now,
    end_time
):

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
# 随机间隔
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
# 生成排程
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
                1
            )
        )

    else:

        ahead_days = int(
            ahead_days
        )

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
# 主排程
# ============================================================

def schedule_future_quotes(
    ahead_days=None
):

    settings = load_settings()

    quotes = load_quotes()

    state = load_state()

    timezone = ZoneInfo(
        settings["timezone"]
    )

    now = datetime.now(
        timezone
    )

    cleanup_old_state(
        state,
        now
    )

    save_state(
        state
    )

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

    created_count = 0
    skipped_count = 0
    failed_count = 0

    # --------------------------------------------------------
    # Cookie
    # --------------------------------------------------------

    cookie_string = os.environ.get(
        "X_COOKIE",
        ""
    ).strip()

    if not cookie_string:

        raise RuntimeError(
            "没有找到 X_COOKIE。"
        )

    cookies = parse_cookie_string(
        cookie_string
    )

    if not any(
        c["name"] == "auth_token"
        for c in cookies
    ):

        raise RuntimeError(
            "X_COOKIE 中没有 auth_token。"
        )

    if not any(
        c["name"] == "ct0"
        for c in cookies
    ):

        raise RuntimeError(
            "X_COOKIE 中没有 ct0。"
        )

    # --------------------------------------------------------
    # 启动 Chromium
    # --------------------------------------------------------

    with sync_playwright() as playwright:

        print()
        print("-----------------------------------")
        print("启动 Chromium")
        print("-----------------------------------")

        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        context = browser.new_context(
            locale="en-US",
            timezone_id="Asia/Taipei",
            viewport={
                "width": 1440,
                "height": 900
            },
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        )

        context.add_cookies(
            cookies
        )

        page = context.new_page()

        # ----------------------------------------------------
        # 检查登录
        # ----------------------------------------------------

        check_login(
            page
        )

        # ----------------------------------------------------
        # 创建排程
        # ----------------------------------------------------

        for post_dt in schedule_times:

            slot_id = post_dt.isoformat()

            if slot_id in scheduled_slots:

                skipped_count += 1

                continue

            quote = random.choice(
                quotes
            )

            print()
            print(
                "-----------------------------------"
            )

            print(
                f"准备排程：{post_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            print(
                f"随机语录：{quote}"
            )

            try:

                scheduled_id = schedule_tweet(
                    page,
                    quote,
                    post_dt
                )

            except Exception as error:

                print()
                print(
                    "❌ 排程失败："
                )

                print(
                    str(error)
                )

                failed_count += 1

                continue

            if scheduled_id:

                created_count += 1

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

                save_state(
                    state
                )

        browser.close()

    # --------------------------------------------------------
    # 最终保存
    # --------------------------------------------------------

    state["scheduled_slots"] = sorted(
        scheduled_slots
    )

    save_state(
        state
    )

    print()
    print(
        "==================================="
    )

    print(
        "排程处理完成"
    )

    print(
        "==================================="
    )

    print(
        f"候选时间：{len(schedule_times)}"
    )

    print(
        f"新建排程：{created_count}"
    )

    print(
        f"已有排程：{skipped_count}"
    )

    print(
        f"失败排程：{failed_count}"
    )

    print()


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "==================================="
    )

    print(
        "       RANDOM QUOTE POSTER"
    )

    print(
        "==================================="
    )

    print()

    try:

        schedule_future_quotes()

        print(
            "==================================="
        )

        print(
            "全部排程处理完成。"
        )

        print(
            "==================================="
        )

    except Exception as e:

        print()

        print(
            "❌ 程序发生错误："
        )

        print(
            e
        )

        raise
