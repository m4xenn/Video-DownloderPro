# ============================================================
#  src/state/app_state.py
#  Uygulama global durumu (State)
# ============================================================

state = {
    "current_download_path": "",
    "current_lang": "tr",
    "download_status": {
        "status": "idle", 
        "error": "", 
        "total_items": 0,
        "items": []
    },
    "cancel_flags": {}
}

class state_actions:
    @staticmethod
    def set_download_path(path):
        state["current_download_path"] = path

    @staticmethod
    def set_language(lang):
        state["current_lang"] = lang

    @staticmethod
    def update_download_status(status_dict):
        state["download_status"].update(status_dict)

    @staticmethod
    def update_item_progress(url, percent=None, speed=None, status=None):
        for item in state["download_status"].get("items", []):
            if item["url"] == url:
                if percent is not None:
                    item["percent"] = percent
                if speed is not None:
                    item["speed"] = speed
                if status is not None:
                    item["status"] = status
                break

    @staticmethod
    def set_cancel_flag(url, value):
        state["cancel_flags"][url] = value
