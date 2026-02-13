"""
기본 테스트 - 테스트 환경 검증
"""
import pytest


def test_basic_import():
    """기본 import 테스트"""
    assert True


def test_pytest_working():
    """pytest 동작 확인"""
    assert 1 + 1 == 2


class TestBasicMath:
    """기본 산술 연산 테스트"""

    def test_addition(self):
        assert 2 + 2 == 4

    def test_subtraction(self):
        assert 5 - 3 == 2

    def test_multiplication(self):
        assert 3 * 4 == 12
