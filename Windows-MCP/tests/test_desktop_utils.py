from windows_mcp.desktop.utils import remove_private_use_chars


class TestRemovePrivateUseChars:
    def test_no_private_use_chars(self):
        assert remove_private_use_chars("hello world") == "hello world"

    def test_empty_string(self):
        assert remove_private_use_chars("") == ""

    def test_bmp_private_use_area(self):
        """U+E000..U+F8FF (Basic Multilingual Plane private use area)."""
        assert remove_private_use_chars("abc\ue000de\ueab6f") == "abcdef"
        assert remove_private_use_chars("\ue001\uf8ff") == ""

    def test_supplementary_private_use_area_a(self):
        """U+F0000..U+FFFFD (Supplementary Private Use Area-A)."""
        assert remove_private_use_chars("x\U000f0000y") == "xy"
        assert remove_private_use_chars("\U000ffffd") == ""

    def test_supplementary_private_use_area_b(self):
        """U+100000..U+10FFFD (Supplementary Private Use Area-B)."""
        assert remove_private_use_chars("x\U00100000y") == "xy"
        assert remove_private_use_chars("\U0010fffd") == ""

    def test_consecutive_private_use_chars(self):
        assert remove_private_use_chars("\ue000\ue001\ue002") == ""

    def test_mixed_content(self):
        text = "File\ue001Name\ue002.txt"
        assert remove_private_use_chars(text) == "FileName.txt"

    def test_preserves_non_private_unicode(self):
        text = "日本語テスト 🎉 café"
        assert remove_private_use_chars(text) == text

    def test_only_private_use_chars(self):
        assert remove_private_use_chars("\ue000\uf8ff\U000f0000\U0010fffd") == ""
