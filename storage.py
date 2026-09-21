from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY

_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TABLE = "subscribers"


def init_db():
    # الجدول تم إنشاؤه مسبقًا على Supabase عبر SQL Editor.
    # هذا الاستدعاء فقط للتأكد إن الاتصال والجدول شغالين.
    _client.table(TABLE).select("chat_id").limit(1).execute()


def add_subscriber(chat_id: int, username: str | None, first_name: str | None) -> bool:
    """يرجع True إذا كان مشترك جديد، False إذا كان مسجل مسبقًا."""
    existing = _client.table(TABLE).select("chat_id").eq("chat_id", chat_id).execute()
    is_new = len(existing.data) == 0

    _client.table(TABLE).upsert(
        {"chat_id": chat_id, "username": username, "first_name": first_name}
    ).execute()

    return is_new


def get_subscriber(chat_id: int) -> dict | None:
    result = _client.table(TABLE).select("*").eq("chat_id", chat_id).execute()
    return result.data[0] if result.data else None


def is_profile_complete(chat_id: int) -> bool:
    sub = get_subscriber(chat_id)
    if not sub:
        return False
    return bool(sub.get("national_id") and sub.get("full_name") and sub.get("phone_number"))


def update_profile(chat_id: int, national_id: str, full_name: str, phone_number: str):
    _client.table(TABLE).update(
        {
            "national_id": national_id,
            "full_name": full_name,
            "phone_number": phone_number,
        }
    ).eq("chat_id", chat_id).execute()


def get_all_subscribers() -> list[dict]:
    result = _client.table(TABLE).select("*").execute()
    return result.data


def remove_subscriber(chat_id: int):
    _client.table(TABLE).delete().eq("chat_id", chat_id).execute()


def get_all_subscriber_ids() -> list[int]:
    result = _client.table(TABLE).select("chat_id").execute()
    return [row["chat_id"] for row in result.data]


def count_subscribers() -> int:
    result = _client.table(TABLE).select("chat_id", count="exact").execute()
    return result.count
