#!/usr/bin/env python3
"""
Debug existing users and reset Veronica's password
"""

import requests
import sys
import json

class UserDebugger:
    def __init__(self, base_url="https://08bda96a-88a3-4a43-8d93-935b8a4e0c07.preview.emergentagent.com"):
        self.base_url = base_url.rstrip('/')
        self.admin_token = None
        self.session = requests.Session()

    def make_request(self, method: str, endpoint: str, data=None, token=None, expected_status=200):
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

    def login_admin(self):
        """Login as admin"""
        success, data = self.make_request('POST', 'login', {
            'username': 'ADMIN',
            'password': '!$3man@d3c1%'
        })
        
        if success and 'access_token' in data:
            self.admin_token = data['access_token']
            print("✅ Admin login successful")
            return True
        else:
            print(f"❌ Admin login failed: {data}")
            return False

    def debug_users(self):
        """Debug existing users"""
        if not self.login_admin():
            return False
        
        print("🔍 DEBUGGING EXISTING USERS")
        print("=" * 40)
        
        # Get all users
        success, users = self.make_request('GET', 'users', token=self.admin_token)
        if success:
            print(f"Found {len(users)} users:")
            
            veronica_user = None
            for user in users:
                print(f"  - {user['username']} ({user['role']}) - ID: {user['id']}")
                if user['username'] == 'VERONICA':
                    veronica_user = user
            
            if veronica_user:
                print(f"\n✅ Found VERONICA user:")
                print(f"   - ID: {veronica_user['id']}")
                print(f"   - Email: {veronica_user['email']}")
                print(f"   - Role: {veronica_user['role']}")
                print(f"   - Active: {veronica_user['active']}")
                
                # Reset Veronica's password
                print(f"\n🔧 Resetting VERONICA's password to '123456'...")
                success, reset_data = self.make_request('PUT', f'users/{veronica_user["id"]}/password', {
                    'new_password': '123456'
                }, token=self.admin_token)
                
                if success:
                    print("✅ Password reset successful")
                    
                    # Test login
                    print("🔐 Testing login with new password...")
                    success, login_data = self.make_request('POST', 'login', {
                        'username': 'VERONICA',
                        'password': '123456'
                    })
                    
                    if success:
                        print("✅ VERONICA login successful!")
                        return veronica_user['id'], login_data['access_token']
                    else:
                        print(f"❌ Login still failed: {login_data}")
                else:
                    print(f"❌ Password reset failed: {reset_data}")
            else:
                print("❌ VERONICA user not found")
        else:
            print(f"❌ Failed to get users: {users}")
        
        return None, None

if __name__ == "__main__":
    debugger = UserDebugger()
    user_id, token = debugger.debug_users()
    
    if user_id and token:
        print(f"\n🎯 VERONICA is ready for testing!")
        print(f"   User ID: {user_id}")
        print(f"   Token: {token[:50]}...")