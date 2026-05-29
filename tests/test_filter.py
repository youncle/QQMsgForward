"""Tests for QQ number regex tightening (8+ digits)"""
import pytest
from filter import _check_contact_detail

# Shared contact filter config (matches default/wizard/sample configs)
CONTACT_CONFIG = {
    "keywords": ["QQ", "微信", "加好友", "私聊我", "加我"],
    "patterns": {
        "phone": r"1[3-9]\d{9}",
        "qq": r"(?<!\d)[1-9]\d{7,9}(?!\d)",
        "wechat": r"wxid_[a-z0-9]+",
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    },
}

def _msg(text: str) -> list:
    """Build a OneBot v11 array message from plain text."""
    return [{"type": "text", "data": {"text": text}}]


class TestQQRegexMinimum:
    """RED: 7-digit numbers should NOT trigger QQ filter (currently matches = fail)"""

    def test_contact_qq_7_digit_no_match(self):
        """7-digit number should NOT be intercepted after tightening"""
        result = _check_contact_detail(_msg("号码 1234567"), CONTACT_CONFIG)
        assert result == '', f"Expected no match for 7-digit number, got {result!r}"


class TestQQRegexRegression:
    """Regression: 8-10 digit matches, 11+ digit non-matches"""

    def test_contact_qq_8_digit_matches(self):
        """8-digit number SHOULD be intercepted"""
        result = _check_contact_detail(_msg("号码 12345678"), CONTACT_CONFIG)
        assert result == 'qq', f"Expected 'qq' for 8-digit number, got {result!r}"

    def test_contact_qq_10_digit_matches(self):
        """10-digit number SHOULD be intercepted"""
        result = _check_contact_detail(_msg("号码 1234567890"), CONTACT_CONFIG)
        assert result == 'qq', f"Expected 'qq' for 10-digit number, got {result!r}"

    def test_contact_qq_11_digit_no_match(self):
        """11-digit number should NOT be intercepted"""
        result = _check_contact_detail(_msg("号码 12345678901"), CONTACT_CONFIG)
        assert result == '', f"Expected no match for 11-digit number, got {result!r}"
