#!/usr/bin/env python3
"""
Focused test for critical manager restrictions and password change functionality
"""

import requests
import json

class FocusedTester:
    def __init__(self):
        self.base_url = "https://08bda96a-88a3-4a43-8d93-935b8a4e0c07.preview.emergentagent.com"
        self.admin_token = None
        self.manager_token = None
        
    def make_request(self, method, endpoint, data=None, token=None, expected_status=200):
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
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

    def test_manager_restrictions(self):
        print("🔐 Testing Manager Restrictions")
        
        # Login as admin
        success, data = self.make_request('POST', 'login', {
            'username': 'admin',
            'password': 'admin123'
        })
        
        if not success or 'access_token' not in data:
            print("❌ Admin login failed")
            return
            
        self.admin_token = data['access_token']
        print("✅ Admin login successful")
        
        # Create a fresh manager user
        manager_data = {
            'username': 'focused_test_manager',
            'email': 'focused_manager@test.com',
            'password': 'manager123',
            'role': 'manager'
        }
        
        success, data = self.make_request('POST', 'register', manager_data, self.admin_token)
        if success:
            print("✅ Manager user created")
        else:
            print(f"⚠️  Manager creation: {data}")
        
        # Login as manager
        success, login_data = self.make_request('POST', 'login', {
            'username': manager_data['username'],
            'password': manager_data['password']
        })
        
        if not success or 'access_token' not in login_data:
            print(f"❌ Manager login failed: {login_data}")
            return
            
        self.manager_token = login_data['access_token']
        print("✅ Manager login successful")
        
        # Test 1: Manager trying to create another manager (should fail)
        print("\n📋 Test 1: Manager creating another manager (should FAIL)")
        another_manager = {
            'username': 'manager_created_manager_test',
            'email': 'manager_created@test.com',
            'password': 'manager123',
            'role': 'manager'
        }
        
        success, data = self.make_request('POST', 'register', another_manager, 
                                        self.manager_token, expected_status=403)
        if success:
            print("✅ Manager correctly blocked from creating another manager")
        else:
            print(f"❌ CRITICAL: Manager was able to create another manager: {data}")
        
        # Test 2: Manager trying to create admin (should fail)
        print("\n📋 Test 2: Manager creating admin (should FAIL)")
        admin_data = {
            'username': 'manager_created_admin_test',
            'email': 'manager_admin@test.com',
            'password': 'admin123',
            'role': 'admin'
        }
        
        success, data = self.make_request('POST', 'register', admin_data, 
                                        self.manager_token, expected_status=403)
        if success:
            print("✅ Manager correctly blocked from creating admin")
        else:
            print(f"❌ CRITICAL: Manager was able to create admin: {data}")
        
        # Test 3: Manager creating reception (should work)
        print("\n📋 Test 3: Manager creating reception (should WORK)")
        reception_data = {
            'username': 'manager_created_reception_test',
            'email': 'manager_reception@test.com',
            'password': 'reception123',
            'role': 'reception'
        }
        
        success, data = self.make_request('POST', 'register', reception_data, self.manager_token)
        if success:
            print("✅ Manager successfully created reception user")
        else:
            print(f"❌ Manager failed to create reception user: {data}")

    def test_password_change_system(self):
        print("\n🔑 Testing Password Change System")
        
        if not self.admin_token:
            print("❌ No admin token available")
            return
        
        # Create test user
        test_user = {
            'username': 'password_test_user',
            'email': 'password_test@test.com',
            'password': 'initial123',
            'role': 'reception'
        }
        
        success, data = self.make_request('POST', 'register', test_user, self.admin_token)
        if success:
            print("✅ Test user created for password change test")
        else:
            print(f"⚠️  Test user creation: {data}")
            return
        
        # Get user list to find the user ID
        success, users = self.make_request('GET', 'users', token=self.admin_token)
        if not success:
            print(f"❌ Failed to get users: {users}")
            return
        
        test_user_obj = next((u for u in users if u['username'] == test_user['username']), None)
        if not test_user_obj:
            print("❌ Test user not found in users list")
            return
        
        user_id = test_user_obj['id']
        print(f"✅ Found test user ID: {user_id}")
        
        # Force password change
        success, data = self.make_request('PUT', f'users/{user_id}', {
            'require_password_change': True
        }, token=self.admin_token)
        
        if success:
            print("✅ Admin successfully set require_password_change to true")
        else:
            print(f"❌ Failed to set require_password_change: {data}")
            return
        
        # Test login is blocked
        success, login_data = self.make_request('POST', 'login', {
            'username': test_user['username'],
            'password': test_user['password']
        }, expected_status=401)
        
        if success:
            error_msg = login_data.get('detail', '')
            print(f"✅ Login correctly blocked: {error_msg}")
        else:
            print(f"❌ Login should have been blocked but wasn't: {login_data}")

    def test_check_permission_endpoint(self):
        print("\n🔐 Testing Check Permission Endpoint")
        
        if not self.admin_token:
            print("❌ No admin token available")
            return
        
        # Test admin permissions
        success, data = self.make_request('POST', 'check-permission', {
            'permission': 'bills'
        }, token=self.admin_token)
        
        if success:
            has_permission = data.get('has_permission', False)
            print(f"✅ Admin bills permission: {has_permission}")
        else:
            print(f"❌ Check permission failed: {data}")
        
        # Test manager permissions
        if self.manager_token:
            success, data = self.make_request('POST', 'check-permission', {
                'permission': 'products'
            }, token=self.manager_token)
            
            if success:
                has_permission = data.get('has_permission', False)
                print(f"✅ Manager products permission: {has_permission}")
            else:
                print(f"❌ Manager check permission failed: {data}")

def main():
    tester = FocusedTester()
    tester.test_manager_restrictions()
    tester.test_password_change_system()
    tester.test_check_permission_endpoint()

if __name__ == "__main__":
    main()