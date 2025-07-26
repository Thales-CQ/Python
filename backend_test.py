#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime, timedelta

class CashSystemAPITester:
    def __init__(self, base_url="https://4b7a0316-949f-4a96-8246-8c7230b403be.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def make_request(self, method, endpoint, data=None, expected_status=200):
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=headers)
            
            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}
            
            return success, response.status_code, response_data
            
        except Exception as e:
            return False, 0, {"error": str(e)}

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        success, status, data = self.make_request(
            'POST', 'login', 
            {"username": "invalid", "password": "invalid"}, 
            expected_status=401
        )
        return self.log_test(
            "Login with invalid credentials", 
            success, 
            f"Status: {status}"
        )

    def test_login_valid_credentials(self):
        """Test login with valid admin credentials"""
        success, status, data = self.make_request(
            'POST', 'login', 
            {"username": "admin", "password": "admin123"}, 
            expected_status=200
        )
        
        if success and 'access_token' in data:
            self.token = data['access_token']
            self.user_data = data.get('user', {})
            
        return self.log_test(
            "Login with valid credentials", 
            success and 'access_token' in data, 
            f"Status: {status}, Token received: {'access_token' in data}"
        )

    def test_get_current_user(self):
        """Test getting current user info"""
        if not self.token:
            return self.log_test("Get current user", False, "No token available")
            
        success, status, data = self.make_request('GET', 'me')
        
        return self.log_test(
            "Get current user info", 
            success and 'username' in data, 
            f"Status: {status}, User: {data.get('username', 'N/A')}"
        )

    def test_get_transactions_summary(self):
        """Test getting transactions summary for dashboard"""
        if not self.token:
            return self.log_test("Get transactions summary", False, "No token available")
            
        success, status, data = self.make_request('GET', 'transactions/summary')
        
        expected_fields = ['total_entrada', 'total_saida', 'saldo', 'total_transactions']
        has_all_fields = all(field in data for field in expected_fields)
        
        return self.log_test(
            "Get transactions summary", 
            success and has_all_fields, 
            f"Status: {status}, Fields: {list(data.keys()) if success else 'N/A'}"
        )

    def test_create_transaction_entrada(self):
        """Test creating an entrada (income) transaction"""
        if not self.token:
            return self.log_test("Create entrada transaction", False, "No token available")
            
        transaction_data = {
            "type": "entrada",
            "amount": 100.50,
            "description": "Test entrada transaction",
            "payment_method": "dinheiro"
        }
        
        success, status, data = self.make_request(
            'POST', 'transactions', 
            transaction_data, 
            expected_status=200
        )
        
        return self.log_test(
            "Create entrada transaction", 
            success and data.get('type') == 'entrada', 
            f"Status: {status}, Amount: {data.get('amount', 'N/A')}"
        )

    def test_create_transaction_saida(self):
        """Test creating a saida (expense) transaction"""
        if not self.token:
            return self.log_test("Create saida transaction", False, "No token available")
            
        transaction_data = {
            "type": "saida",
            "amount": 50.25,
            "description": "Test saida transaction",
            "payment_method": "cartao"
        }
        
        success, status, data = self.make_request(
            'POST', 'transactions', 
            transaction_data, 
            expected_status=200
        )
        
        return self.log_test(
            "Create saida transaction", 
            success and data.get('type') == 'saida', 
            f"Status: {status}, Amount: {data.get('amount', 'N/A')}"
        )

    def test_get_transactions_list(self):
        """Test getting list of transactions"""
        if not self.token:
            return self.log_test("Get transactions list", False, "No token available")
            
        success, status, data = self.make_request('GET', 'transactions')
        
        is_list = isinstance(data, list)
        
        return self.log_test(
            "Get transactions list", 
            success and is_list, 
            f"Status: {status}, Count: {len(data) if is_list else 'N/A'}"
        )

    def test_payment_methods(self):
        """Test all payment methods"""
        if not self.token:
            return self.log_test("Test payment methods", False, "No token available")
            
        payment_methods = ["dinheiro", "cartao", "pix", "boleto"]
        all_success = True
        
        for method in payment_methods:
            transaction_data = {
                "type": "entrada",
                "amount": 10.00,
                "description": f"Test {method} payment",
                "payment_method": method
            }
            
            success, status, data = self.make_request(
                'POST', 'transactions', 
                transaction_data, 
                expected_status=200
            )
            
            if not success:
                all_success = False
                print(f"   ❌ Payment method {method} failed - Status: {status}")
            else:
                print(f"   ✅ Payment method {method} works")
        
        return self.log_test(
            "Test all payment methods", 
            all_success, 
            f"Tested: {', '.join(payment_methods)}"
        )

    def test_unauthorized_access(self):
        """Test accessing protected endpoints without token"""
        # Temporarily remove token
        temp_token = self.token
        self.token = None
        
        success, status, data = self.make_request(
            'GET', 'transactions', 
            expected_status=403
        )
        
        # Restore token
        self.token = temp_token
        
        return self.log_test(
            "Unauthorized access protection", 
            success, 
            f"Status: {status} (should be 403)"
        )

    def test_get_users(self):
        """Test getting users list (admin only)"""
        if not self.token:
            return self.log_test("Get users list", False, "No token available")
            
        success, status, data = self.make_request('GET', 'users')
        
        is_list = isinstance(data, list)
        has_admin = any(user.get('username') == 'admin' for user in data) if is_list else False
        
        return self.log_test(
            "Get users list", 
            success and is_list and has_admin, 
            f"Status: {status}, Count: {len(data) if is_list else 'N/A'}"
        )

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Cash System API Tests")
        print(f"📡 Testing endpoint: {self.base_url}")
        print("=" * 60)
        
        # Authentication tests
        print("\n🔐 Authentication Tests:")
        self.test_login_invalid_credentials()
        self.test_login_valid_credentials()
        self.test_get_current_user()
        self.test_unauthorized_access()
        
        # Transaction tests
        print("\n💰 Transaction Tests:")
        self.test_get_transactions_summary()
        self.test_create_transaction_entrada()
        self.test_create_transaction_saida()
        self.test_get_transactions_list()
        self.test_payment_methods()
        
        # User management tests
        print("\n👥 User Management Tests:")
        self.test_get_users()
        
        # Final results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return 1

def main():
    tester = CashSystemAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())