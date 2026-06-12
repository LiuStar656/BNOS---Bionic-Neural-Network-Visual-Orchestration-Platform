"""
验证器模块测试
测试 NodeNameValidator 和 PathValidator 的功能
"""
import pytest
import os
from ui.core.validators import NodeNameValidator, PathValidator


class TestNodeNameValidator:
    """节点名称验证器测试"""

    def test_valid_name(self):
        """测试有效的节点名称"""
        # 英文名称
        valid, msg = NodeNameValidator.validate("my_node")
        assert valid is True
        assert msg == ""

        # 中文名称
        valid, msg = NodeNameValidator.validate("我的节点")
        assert valid is True
        assert msg == ""

        # 混合名称
        valid, msg = NodeNameValidator.validate("Node_001")
        assert valid is True
        assert msg == ""

    def test_empty_name(self):
        """测试空名称"""
        valid, msg = NodeNameValidator.validate("")
        assert valid is False
        assert "不能为空" in msg

    def test_name_with_special_chars(self):
        """测试包含特殊字符的名称"""
        special_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in special_chars:
            valid, msg = NodeNameValidator.validate(f"node{char}name")
            assert valid is False
            assert "只能包含字母" in msg

    def test_name_too_long(self):
        """测试过长的名称"""
        long_name = "a" * 100
        valid, msg = NodeNameValidator.validate(long_name)
        assert valid is False
        assert "超过" in msg

    def test_path_traversal(self):
        """测试路径穿越攻击"""
        valid, msg = NodeNameValidator.validate("../malicious")
        assert valid is False

    def test_sanitize(self):
        """测试名称清理功能"""
        assert NodeNameValidator.sanitize("node/name") == "nodename"
        assert NodeNameValidator.sanitize("node*name") == "nodename"


class TestPathValidator:
    """路径验证器测试"""

    def test_valid_path(self):
        """测试有效的路径"""
        valid, msg = PathValidator.validate_path("/home/user/project")
        assert valid is True
        assert msg == ""

    def test_empty_path(self):
        """测试空路径"""
        valid, msg = PathValidator.validate_path("")
        assert valid is False
        assert "不能为空" in msg

    def test_path_traversal(self):
        """测试路径穿越（直接以..开头）"""
        # 直接以 .. 开头的路径
        valid, msg = PathValidator.validate_path("../etc/passwd")
        assert valid is False
        assert "父目录" in msg

    def test_path_traversal_double(self):
        """测试双点路径穿越"""
        valid, msg = PathValidator.validate_path("../../etc/passwd")
        assert valid is False
        assert "父目录" in msg

    def test_path_traversal_with_current(self):
        """测试包含当前目录的路径穿越"""
        # 规范化后仍然包含 .. 的路径
        valid, msg = PathValidator.validate_path("./../etc/passwd")
        assert valid is False
        assert "父目录" in msg

    def test_is_within_directory(self):
        """测试路径是否在目录内"""
        assert PathValidator.is_within_directory("/home/user/project/file.txt", "/home/user/project") is True
        assert PathValidator.is_within_directory("/home/other/file.txt", "/home/user/project") is False