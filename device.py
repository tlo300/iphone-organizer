# device.py — pymobiledevice3 wrapper for iOS 26 (CoreDevice tunnel transport)
import asyncio
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Cached app info: bundle_id -> {'name': str, 'icon_b64': str|None}
_app_cache: dict = {}
_layout_cache: Optional[list] = None


def _run(coro):
    """Run an async coroutine from synchronous Flask route handlers."""
    return asyncio.run(coro)


async def _get_rsd():
    """
    Return an already-connected RemoteServiceDiscoveryService via tunneld.
    tunneld must be running as admin:
        python -m pymobiledevice3 remote tunneld
    """
    from pymobiledevice3.tunneld.api import get_tunneld_devices

    rsds = await get_tunneld_devices()
    if not rsds:
        raise ConnectionError(
            "No iOS devices found via tunneld.\n"
            "Run this in a separate admin terminal first:\n"
            "  python -m pymobiledevice3 remote tunneld"
        )
    return rsds[0]


def get_device_info() -> dict:
    """Return basic device info (name, iOS version, model, udid)."""
    async def _inner():
        rsd = await _get_rsd()
        return {
            "name": rsd.name,
            "version": rsd.product_version,
            "model": rsd.product_type,
            "udid": rsd.udid,
        }
    return _run(_inner())


def fetch_installed_apps() -> dict[str, str]:
    """
    Return dict of bundle_id -> display_name for all installed apps.
    Results are cached in _app_cache.
    """
    global _app_cache

    async def _inner():
        from pymobiledevice3.services.installation_proxy import InstallationProxyService
        rsd = await _get_rsd()
        async with InstallationProxyService(rsd) as svc:
            apps = await svc.get_apps(application_type="Any", calculate_sizes=False)
            result = {}
            for bid, info in apps.items():
                name = (
                    info.get("CFBundleDisplayName")
                    or info.get("CFBundleName")
                    or bid
                )
                result[bid] = name
            return result

    apps = _run(_inner())
    _app_cache.update({bid: {"name": name, "icon_b64": None} for bid, name in apps.items()})
    return {bid: data["name"] for bid, data in _app_cache.items()}


def get_layout() -> list:
    """Read current home screen layout from device and cache it."""
    global _layout_cache

    async def _inner():
        from pymobiledevice3.services.springboard import SpringBoardServicesService
        rsd = await _get_rsd()
        async with SpringBoardServicesService(rsd) as svc:
            # format_version="" omits the key → device returns its native dict format
            return await svc.get_icon_state(format_version="")

    _layout_cache = _run(_inner())
    return _layout_cache


def set_layout(layout) -> None:
    """Write a modified layout back to the device."""
    global _layout_cache

    async def _inner():
        from pymobiledevice3.services.springboard import SpringBoardServicesService
        rsd = await _get_rsd()
        async with SpringBoardServicesService(rsd) as svc:
            await svc.set_icon_state(layout)

    _run(_inner())
    _layout_cache = layout


def get_icon_png_b64(bundle_id: str) -> Optional[str]:
    """
    Return a base64-encoded PNG for the given app icon.
    Returns None if unavailable. Results are cached.
    """
    if bundle_id in _app_cache and _app_cache[bundle_id].get("icon_b64"):
        return _app_cache[bundle_id]["icon_b64"]

    async def _inner():
        from pymobiledevice3.services.springboard import SpringBoardServicesService
        rsd = await _get_rsd()
        async with SpringBoardServicesService(rsd) as svc:
            return await svc.get_icon_pngdata(bundle_id)

    try:
        png_bytes = _run(_inner())
        if png_bytes:
            b64 = base64.b64encode(png_bytes).decode()
            if bundle_id not in _app_cache:
                _app_cache[bundle_id] = {"name": bundle_id, "icon_b64": None}
            _app_cache[bundle_id]["icon_b64"] = b64
            return b64
    except Exception as e:
        logger.warning(f"Could not fetch icon for {bundle_id}: {e}")
    return None
