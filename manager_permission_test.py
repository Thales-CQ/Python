#!/usr/bin/env python3
"""
Focused Test for Manager Permission Restrictions Security Issue
Tests the specific security vulnerability fix for manager role restrictions
"""

import requests
import sys
import json
from datetime import datetime

class ManagerPermissionTester:
    def __init__(self, base_url="https://08bda96a-88a3-4a43-8d93-935b8a4e0c07.preview.emergentagent.com"):
        self.base_url = base_url.rstrip('/')
        self.admin_token = None
        self.manager_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.errors = []
        self.session = requests.Session()

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
            if details:
                print(f"   📝 {details}")
        else:
            print(f"❌ {name}")
            if details:
                print(f"   💥 {details}")
            self.errors.append(f"{name}: {details}")

    def make_request(self, method: str, endpoint: str, data: dict = None, 
                    token: str = None, expected_status: int = 200) -> tuple:
        """Make HTTP request and return success status and response data"""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, headers=headers, timeout=10)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, headers=headers, timeout=10)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=headers, timeout=10)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}

            return success, response_data

        except Exception as e:
            return False, {"error": str(e)}

    def setup_tokens(self):
        """Setup admin and manager tokens for testing"""
        print("🔐 Setting up authentication tokens...")
        
        # Login as admin
        success, data = self.make_request('POST', 'login', {
            'username': 'ADMIN',
            'password': 'admin123'
        })
        
        if success and 'access_token' in data:
            self.admin_token = data['access_token']
            print(f"   ✅ Admin login successful")
        else:
            print(f"   ❌ Admin login failed: {data}")
            return False

        # Create a manager user for testing
        manager_data = {
            'username': 'TEST_MANAGER_SECURITY',
            'email': 'MANAGER_SECURITY@TEST.COM',
            'password': 'manager123',
            'role': 'manager'
        }
        
        success, data = self.make_request('POST', 'register', manager_data, self.admin_token)
        if success:
            print(f"   ✅ Manager user created")
        else:
            # Manager might already exist, try to login
            print(f"   ⚠️ Manager creation failed (might already exist): {data}")

        # Login as manager
        success, data = self.make_request('POST', 'login', {
            'username': 'TEST_MANAGER_SECURITY',
            'password': 'manager123'
        })
        
        if success and 'access_token' in data:
            self.manager_token = data['access_token']
            print(f"   ✅ Manager login successful")
            return True
        else:
            print(f"   ❌ Manager login failed: {data}")
            return False

    def test_manager_creating_reception(self):
        """Test that manager CAN create reception users (should work)"""
        print("\n📝 Testing Manager Creating Reception User (SHOULD WORK)...")
        
        reception_data = {
            'username': f'RECEPTION_BY_MANAGER_{datetime.now().strftime("%H%M%S")}',
            'email': f'RECEPTION_BY_MANAGER_{datetime.now().strftime("%H%M%S")}@TEST.COM',
            'password': 'reception123',
            'role': 'reception'
        }
        
        success, data = self.make_request('POST', 'register', reception_data, 
                                        self.manager_token, 200)
        
        if success:
            self.log_test("Manager Creating Reception User", True, 
                         f"Manager successfully created reception user: {reception_data['username']}")
        else:
            self.log_test("Manager Creating Reception User", False, 
                         f"Manager should be able to create reception users. Error: {data}")

    def test_manager_creating_manager(self):
        """Test that manager CANNOT create other managers (should fail)"""
        print("\n📝 Testing Manager Creating Manager User (SHOULD FAIL)...")
        
        manager_data = {
            'username': f'MANAGER_BY_MANAGER_{datetime.now().strftime("%H%M%S")}',
            'email': f'MANAGER_BY_MANAGER_{datetime.now().strftime("%H%M%S")}@TEST.COM',
            'password': 'manager123',
            'role': 'manager'
        }
        
        success, data = self.make_request('POST', 'register', manager_data, 
                                        self.manager_token, 403)
        
        if success:
            error_msg = data.get('detail', '')
            correct_error = 'Gerentes só podem criar usuários de recepção' in error_msg
            self.log_test("Manager Creating Manager User (Blocked)", correct_error, 
                         f"Correct error message: '{error_msg}'")
        else:
            self.log_test("Manager Creating Manager User (Blocked)", False, 
                         f"Manager should be blocked from creating managers. Response: {data}")

    def test_manager_creating_admin(self):
        """Test that manager CANNOT create admin users (should fail)"""
        print("\n📝 Testing Manager Creating Admin User (SHOULD FAIL)...")
        
        admin_data = {
            'username': f'ADMIN_BY_MANAGER_{datetime.now().strftime("%H%M%S")}',
            'email': f'ADMIN_BY_MANAGER_{datetime.now().strftime("%H%M%S")}@TEST.COM',
            'password': 'admin123',
            'role': 'admin'
        }
        
        success, data = self.make_request('POST', 'register', admin_data, 
                                        self.manager_token, 403)
        
        if success:
            error_msg = data.get('detail', '')
            correct_error = 'Gerentes só podem criar usuários de recepção' in error_msg
            self.log_test("Manager Creating Admin User (Blocked)", correct_error, 
                         f"Correct error message: '{error_msg}'")
        else:
            self.log_test("Manager Creating Admin User (Blocked)", False, 
                         f"Manager should be blocked from creating admins. Response: {data}")

    def test_admin_creating_any_role(self):
        """Test that admin CAN create users with any role (should work)"""
        print("\n📝 Testing Admin Creating Users with Any Role (SHOULD WORK)...")
        
        # Test admin creating manager
        manager_data = {
            'username': f'MANAGER_BY_ADMIN_{datetime.now().strftime("%H%M%S")}',
            'email': f'MANAGER_BY_ADMIN_{datetime.now().strftime("%H%M%S")}@TEST.COM',
            'password': 'manager123',
            'role': 'manager'
        }
        
        success, data = self.make_request('POST', 'register', manager_data, 
                                        self.admin_token, 200)
        
        if success:
            self.log_test("Admin Creating Manager User", True, 
                         f"Admin successfully created manager: {manager_data['username']}")
        else:
            self.log_test("Admin Creating Manager User", False, 
                         f"Admin should be able to create managers. Error: {data}")

        # Test admin creating admin
        admin_data = {
            'username': f'ADMIN_BY_ADMIN_{datetime.now().strftime("%H%M%S")}',
            'email': f'ADMIN_BY_ADMIN_{datetime.now().strftime("%H%M%S")}@TEST.COM',
            'password': 'admin123',
            'role': 'admin'
        }
        
        success, data = self.make_request('POST', 'register', admin_data, 
                                        self.admin_token, 200)
        
        if success:
            self.log_test("Admin Creating Admin User", True, 
                         f"Admin successfully created admin: {admin_data['username']}")
        else:
            self.log_test("Admin Creating Admin User", False, 
                         f"Admin should be able to create admins. Error: {data}")

        # Test admin creating reception
        reception_data = {
            'username': f'RECEPTION_BY_ADMIN_{datetime.now().strftime("%H%M%S")}',
            'email': f'RECEPTION_BY_ADMIN_{datetime.now().strftime("%H%M%S")}@TEST.COM',
            'password': 'reception123',
            'role': 'reception'
        }
        
        success, data = self.make_request('POST', 'register', reception_data, 
                                        self.admin_token, 200)
        
        if success:
            self.log_test("Admin Creating Reception User", True, 
                         f"Admin successfully created reception: {reception_data['username']}")
        else:
            self.log_test("Admin Creating Reception User", False, 
                         f"Admin should be able to create reception users. Error: {data}")

    def run_security_tests(self):
        """Run all security tests for manager permission restrictions"""
        print("🔒 MANAGER PERMISSION RESTRICTIONS SECURITY TEST")
        print("=" * 60)
        print("Testing the critical security fix for manager role restrictions")
        print("=" * 60)

        # Setup authentication
        if not self.setup_tokens():
            print("❌ Failed to setup authentication tokens. Cannot proceed.")
            return False

        # Run the specific tests requested
        self.test_manager_creating_reception()
        self.test_manager_creating_manager()
        self.test_manager_creating_admin()
        self.test_admin_creating_any_role()

        # Print summary
        print("\n" + "=" * 60)
        print("🔒 SECURITY TEST SUMMARY")
        print("=" * 60)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.errors:
            print(f"\n❌ FAILED TESTS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
        else:
            print("\n✅ ALL SECURITY TESTS PASSED!")

        # Determine if security vulnerability is fixed
        critical_tests = [
            "Manager Creating Manager User (Blocked)",
            "Manager Creating Admin User (Blocked)",
            "Manager Creating Reception User"
        ]
        
        critical_passed = sum(1 for error in self.errors if not any(test in error for test in critical_tests))
        critical_total = len(critical_tests)
        
        if len(self.errors) == 0:
            print("\n🔒 SECURITY STATUS: ✅ VULNERABILITY FIXED")
            print("   Manager permission restrictions are working correctly.")
        else:
            critical_failures = [error for error in self.errors if any(test in error for test in critical_tests)]
            if critical_failures:
                print("\n🔒 SECURITY STATUS: ❌ VULNERABILITY STILL EXISTS")
                print("   Critical security issues found:")
                for failure in critical_failures:
                    print(f"   • {failure}")
            else:
                print("\n🔒 SECURITY STATUS: ✅ VULNERABILITY FIXED")
                print("   Manager permission restrictions are working correctly.")

        return len(self.errors) == 0

if __name__ == "__main__":
    tester = ManagerPermissionTester()
    success = tester.run_security_tests()
    sys.exit(0 if success else 1)