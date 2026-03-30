# layout.py — Parse and serialize the SpringBoard iconState plist format
#
# The raw plist from the device looks like:
#   {
#     "buttonBar": ["com.apple.mobilephone", ...],   # dock
#     "iconLists": [                                  # pages
#       ["com.apple.mobilesafari", {...folder...}, ...],
#       [...],
#     ]
#   }
#
# This module converts it to/from a friendlier JSON shape for the frontend:
#   {
#     "dock": ["com.apple.mobilephone", ...],
#     "pages": [
#       [
#         {"type": "app",    "id": "com.apple.mobilesafari"},
#         {"type": "folder", "name": "Utilities", "pages": [["com.apple.Preferences", ...]]},
#       ],
#       ...
#     ]
#   }


def _parse_item(item):
    if isinstance(item, str):
        return {"type": "app", "id": item}
    if isinstance(item, dict):
        # Folder
        inner_pages = []
        for page in item.get("iconLists", []):
            inner_pages.append([i for i in page if isinstance(i, str)])
        return {
            "type": "folder",
            "name": item.get("displayName", ""),
            "pages": inner_pages,
        }
    return None


def plist_to_json(raw: dict) -> dict:
    """Convert raw SpringBoard plist dict to frontend-friendly JSON."""
    dock = list(raw.get("buttonBar", []))
    pages = []
    for raw_page in raw.get("iconLists", []):
        page = []
        for item in raw_page:
            parsed = _parse_item(item)
            if parsed:
                page.append(parsed)
        pages.append(page)
    return {"dock": dock, "pages": pages}


def json_to_plist(data: dict) -> dict:
    """Convert frontend JSON back to SpringBoard plist dict."""
    button_bar = list(data.get("dock", []))
    icon_lists = []

    for page in data.get("pages", []):
        raw_page = []
        for item in page:
            if item["type"] == "app":
                raw_page.append(item["id"])
            elif item["type"] == "folder":
                folder = {
                    "displayName": item.get("name", ""),
                    "listType": "folder",
                    "iconLists": [list(p) for p in item.get("pages", [])],
                }
                raw_page.append(folder)
        icon_lists.append(raw_page)

    return {"buttonBar": button_bar, "iconLists": icon_lists}
