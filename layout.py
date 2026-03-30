# layout.py — Parse and serialize the SpringBoard iconState format (iOS 26)
#
# get_icon_state(format_version="") returns a flat list:
#   [dock_section, page1, page2, ...]
#
#   dock_section = [[app_dict, ...]]        # one row of dock apps
#   pageN        = [row, row, ...]          # each row = [item, item, item, item]
#
# Each item is either an app dict:
#   {"displayIdentifier": "...", "bundleIdentifier": "...", "displayName": "...", ...}
# or False for an empty slot.
#
# Frontend JSON shape:
#   {
#     "dock": [{"type": "app", "id": "...", "name": "..."}, ...],
#     "pages": [
#       [{"type": "app", "id": "...", "name": "..."}, {"type": "empty"}, ...],
#       ...
#     ]
#   }

ROW_WIDTH = 4


def _parse_app(item):
    if not item or not isinstance(item, dict):
        return None
    bid = item.get("bundleIdentifier") or item.get("displayIdentifier", "")
    name = item.get("displayName", bid)
    return {"type": "app", "id": bid, "name": name}


def plist_to_json(raw: list) -> dict:
    """Convert raw SpringBoard list to frontend-friendly JSON."""
    # Dock: raw[0] is [[app, app, app, app]] — return bare bundle ID strings
    dock = []
    if raw and isinstance(raw[0], list):
        for row in raw[0]:
            if isinstance(row, list):
                for item in row:
                    if isinstance(item, dict):
                        bid = item.get("bundleIdentifier") or item.get("displayIdentifier", "")
                        if bid:
                            dock.append(bid)

    # Pages: raw[1:] — each element is one page (list of rows)
    pages = []
    for page_rows in raw[1:]:
        page = []
        for row in page_rows:
            if isinstance(row, list):
                for item in row:
                    if item is False or item is None:
                        page.append({"type": "empty"})
                    else:
                        parsed = _parse_app(item)
                        page.append(parsed if parsed else {"type": "empty"})
        pages.append(page)

    return {"dock": dock, "pages": pages}


def json_to_plist(data: dict) -> list:
    """Convert frontend JSON back to SpringBoard format."""
    # Dock: pack into a single row of bundle IDs (dock items are bare strings)
    dock_row = [item for item in data.get("dock", []) if isinstance(item, str)]
    result = [[dock_row]]

    # Pages: re-chunk flat page list into rows of ROW_WIDTH, False for empty
    for page_items in data.get("pages", []):
        row = []
        rows = []
        for item in page_items:
            row.append(item["id"] if item.get("type") == "app" else False)
            if len(row) == ROW_WIDTH:
                rows.append(row)
                row = []
        if row:
            while len(row) < ROW_WIDTH:
                row.append(False)
            rows.append(row)
        result.append(rows)

    return result
