#!/usr/bin/env python3
"""
i18n_utils - 橋接模組
將 utils.i18n 的函數重新導出，方便其他模組使用
"""

from utils.i18n import t, safe_t, init_i18n, get_available_languages

__all__ = ['t', 'safe_t', 'init_i18n', 'get_available_languages']
