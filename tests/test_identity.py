import pytest
import sys
sys.path.insert(0, '/home/one/cellular-app')

from app.api.identity import luhn_check_digit, validate_imei, generate_random_imei


class TestLuhnCheck:
    def test_luhn_known_valid(self):
        # Known valid Luhn check digits from Wikipedia
        assert luhn_check_digit("49015420323751") == 8
        assert luhn_check_digit("12345678901234") == 7
    
    def test_luhn_zero_padding(self):
        result = luhn_check_digit("00000000000000")
        assert isinstance(result, int)
        assert 0 <= result <= 9


class TestValidateIMEI:
    def test_valid_imei(self):
        # Use known valid IMEI from current modem
        assert validate_imei("868371055978783") == True
        # Test with simple known valid
        assert validate_imei("123456789012347") == True
    
    def test_invalid_length(self):
        assert validate_imei("12345") == False
        assert validate_imei("12345678901234") == False
        assert validate_imei("1234567890123456") == False
    
    def test_invalid_luhn(self):
        assert validate_imei("123456789012340") == False
    
    def test_non_numeric(self):
        assert validate_imei("abcdefghijk lmno") == False


class TestGenerateIMEI:
    def test_generates_valid_imei(self):
        for _ in range(10):
            imei = generate_random_imei()
            assert len(imei) == 15
            assert imei.isdigit()
            assert validate_imei(imei)
    
    def test_generates_unique_imeis(self):
        imeis = [generate_random_imei() for _ in range(100)]
        assert len(set(imeis)) > 90


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
