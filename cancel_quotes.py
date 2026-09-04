import json
import subprocess
from pathlib import Path


# ============================================================
# 配置
# ============================================================

STATE_FILE = Path(__file__).parent / "quote_schedule_state.json"


# ============================================================
# 读取排程
# ============================================================

def load_state():
    if not STATE_FILE.exists():
        raise RuntimeError(
            f"找不到排程状态文件：\n{STATE_FILE}"
        )

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 保存排程状态
# ============================================================

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# 取消单个排程
# ============================================================

def unschedule_tweet(scheduled_id):
    result = subprocess.run(
        [
            "tweetkit",
            "unschedule",
            str(scheduled_id)
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        print("❌ 取消失败")
        if result.stderr.strip():
            print(result.stderr.strip())
        return False

    print("✅ 取消成功")

    if result.stdout.strip():
        print(f"   {result.stdout.strip()}")

    return True


# ============================================================
# 取消全部随机发帖排程
# ============================================================

def cancel_all_quotes():

    state = load_state()

    scheduled_posts = state.get(
        "scheduled_posts",
        {}
    )

    if not scheduled_posts:
        print("目前没有可以取消的随机发帖排程。")
        return

    print()
    print(f"目前共有 {len(scheduled_posts)} 个排程。")
    print()

    confirm = input(
        "确定要取消全部这些排程吗？输入 YES 确认："
    )

    if confirm != "YES":
        print()
        print("已取消操作，没有修改任何排程。")
        return

    print()
    print("开始取消排程...")
    print()

    remaining_posts = {}

    success_count = 0
    failed_count = 0

    for slot_id, info in scheduled_posts.items():

        scheduled_id = info.get("scheduled_id")
        quote = info.get("quote", "")

        print("-----------------------------------")
        print(f"时间：{slot_id}")
        print(f"语录：{quote}")
        print(f"ID：{scheduled_id}")

        if not scheduled_id:
            print("⚠️ 没有 scheduled_id，跳过。")
            remaining_posts[slot_id] = info
            failed_count += 1
            continue

        success = unschedule_tweet(
            scheduled_id
        )

        if success:
            success_count += 1
        else:
            failed_count += 1
            remaining_posts[slot_id] = info

    # ========================================================
    # 更新状态文件
    # ========================================================

    state["scheduled_posts"] = remaining_posts

    state["scheduled_slots"] = sorted(
        remaining_posts.keys()
    )

    save_state(state)

    print()
    print("===================================")
    print("取消操作完成")
    print("===================================")
    print(f"成功取消：{success_count}")
    print(f"取消失败：{failed_count}")
    print(f"剩余排程：{len(remaining_posts)}")
    print()


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":

    print()
    print("===================================")
    print("       CANCEL RANDOM QUOTES")
    print("===================================")
    print()

    try:
        cancel_all_quotes()

    except Exception as e:
        print()
        print("❌ 程序发生错误：")
        print(e)

    print()
    input("按 Enter 键退出...")