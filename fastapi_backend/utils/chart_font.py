# -*- coding: utf-8 -*-
"""matplotlib 图表中文字体：优先 bundled Noto Sans SC，其次系统常见 CJK 字体。"""
from __future__ import annotations

import logging
import os
import platform
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_BUNDLED_FONT = (
    Path(__file__).resolve().parent.parent / "assets" / "fonts" / "NotoSansSC-Regular.otf"
)

_SYSTEM_FONT_CANDIDATES = {
    "Windows": [
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "msyh.ttc",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "msyhbd.ttc",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "simhei.ttf",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "simsun.ttc",
    ],
    "Linux": [
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    ],
    "Darwin": [
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/STHeiti Light.ttc"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
    ],
}


def _iter_font_paths() -> list[Path]:
    paths: list[Path] = []
    if _BUNDLED_FONT.is_file():
        paths.append(_BUNDLED_FONT)
    sysname = platform.system()
    paths.extend(_SYSTEM_FONT_CANDIDATES.get(sysname, []))
    return paths


@lru_cache(maxsize=1)
def get_cjk_font_properties():
    """返回可用于 matplotlib 的中文字体 FontProperties；找不到则 None。"""
    from matplotlib import font_manager

    for fp in _iter_font_paths():
        try:
            font_manager.fontManager.addfont(str(fp))
            prop = font_manager.FontProperties(fname=str(fp))
            name = prop.get_name()
            logger.info("matplotlib 中文字体已加载: %s (%s)", name, fp)
            return prop
        except Exception as e:
            logger.debug("跳过字体 %s: %s", fp, e)

    # 按名称扫描已安装字体（Windows 上有时 addfont 路径失败但名称可用）
    for family in ("Microsoft YaHei", "SimHei", "Noto Sans SC", "WenQuanYi Micro Hei", "PingFang SC"):
        try:
            path = font_manager.findfont(family, fallback_to_default=False)
            if path and Path(path).is_file():
                prop = font_manager.FontProperties(fname=path)
                logger.info("matplotlib 中文字体（按名称）: %s -> %s", family, path)
                return prop
        except Exception:
            continue

    logger.warning(
        "未找到中文字体，图表汉字可能显示为方框；"
        "请将 NotoSansSC-Regular.otf 放到 fastapi_backend/assets/fonts/"
    )
    return None


def configure_matplotlib_cjk() -> Optional[str]:
    """设置 matplotlib 全局 rcParams，返回字体 family 名（失败则 None）。"""
    import matplotlib.pyplot as plt

    prop = get_cjk_font_properties()
    if prop is None:
        plt.rcParams["axes.unicode_minus"] = False
        return None
    family = prop.get_name()
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [family, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    return family
