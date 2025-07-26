#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Sistema de Caixa
Tests all endpoints, authentication, permissions, and business logic
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class CaixaAPITester:
    def __init__(self, base_url="https://4b7a0316-949f-4a96-8246-8c7230b403be.preview.emergentagent.com"):
        self.base_url = base_url.rstrip('/')
        self.admin_token = None
        self.manager_token = None
        self.salesperson_token = None
        self.test_users = {}
        self.test_clients = {}
        self.test_bills = {}
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

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                    token: Optional[str] = None, expected_status: int = 200) -> tuple:
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

    def test_admin_login(self):
        """Test admin login and store token"""
        success, data = self.make_request('POST', 'login', {
            'username': 'admin',
            'password': 'admin123'
        })
        
        if success and 'access_token' in data:
            self.admin_token = data['access_token']
            self.log_test("Admin Login", True, f"Role: {data.get('user', {}).get('role', 'N/A')}")
            return True
        else:
            self.log_test("Admin Login", False, str(data))
            return False

    def test_user_creation(self):
        """Test creating users with different roles"""
        if not self.admin_token:
            self.log_test("User Creation", False, "No admin token")
            return False

        # Create manager user
        manager_data = {
            'username': 'test_manager',
            'email': 'manager@test.com',
            'password': 'manager123',
            'role': 'manager'
        }
        
        success, data = self.make_request('POST', 'register', manager_data, 
                                        self.admin_token, 200)
        self.log_test("Create Manager User", success, str(data) if not success else "Manager created successfully")
        
        if success:
            self.test_users['manager'] = manager_data

        # Create salesperson user
        salesperson_data = {
            'username': 'test_salesperson',
            'email': 'salesperson@test.com',
            'password': 'sales123',
            'role': 'salesperson'
        }
        
        success, data = self.make_request('POST', 'register', salesperson_data, 
                                        self.admin_token, 200)
        self.log_test("Create Salesperson User", success, str(data) if not success else "Salesperson created successfully")
        
        if success:
            self.test_users['salesperson'] = salesperson_data

    def test_user_login_roles(self):
        """Test login for different user roles"""
        # Test manager login
        if 'manager' in self.test_users:
            success, data = self.make_request('POST', 'login', {
                'username': self.test_users['manager']['username'],
                'password': self.test_users['manager']['password']
            })
            
            if success and 'access_token' in data:
                self.manager_token = data['access_token']
                self.log_test("Manager Login", True, f"Token received for {data.get('user', {}).get('username', 'N/A')}")
            else:
                self.log_test("Manager Login", False, str(data))

        # Test salesperson login
        if 'salesperson' in self.test_users:
            success, data = self.make_request('POST', 'login', {
                'username': self.test_users['salesperson']['username'],
                'password': self.test_users['salesperson']['password']
            })
            
            if success and 'access_token' in data:
                self.salesperson_token = data['access_token']
                self.log_test("Salesperson Login", True, f"Token received for {data.get('user', {}).get('username', 'N/A')}")
            else:
                self.log_test("Salesperson Login", False, str(data))

    def test_user_permissions(self):
        """Test role-based permissions"""
        # Test admin can access activity logs
        success, data = self.make_request('GET', 'activity-logs', token=self.admin_token)
        self.log_test("Admin Access Activity Logs", success, f"Found {len(data) if isinstance(data, list) else 0} logs" if success else str(data))

        # Test manager cannot access activity logs
        if self.manager_token:
            success, data = self.make_request('GET', 'activity-logs', token=self.manager_token, expected_status=403)
            self.log_test("Manager Cannot Access Activity Logs", success, "Correctly blocked" if success else str(data))

        # Test salesperson cannot create users
        if self.salesperson_token:
            success, data = self.make_request('POST', 'register', {
                'username': 'unauthorized_user',
                'email': 'unauth@test.com',
                'password': 'test123',
                'role': 'salesperson'
            }, token=self.salesperson_token, expected_status=403)
            self.log_test("Salesperson Cannot Create Users", success, "Correctly blocked" if success else str(data))

    def test_transaction_payment_restrictions(self):
        """Test payment method restrictions for transactions"""
        if not self.admin_token:
            self.log_test("Transaction Payment Restrictions", False, "No admin token")
            return

        print("   Testing ENTRADA with all payment methods...")
        # Test ENTRADA with all payment methods (should work)
        entrada_methods = ['dinheiro', 'cartao', 'pix', 'boleto']
        entrada_success = 0
        for method in entrada_methods:
            success, data = self.make_request('POST', 'transactions', {
                'type': 'entrada',
                'amount': 100.0,
                'description': f'Test entrada {method}',
                'payment_method': method
            }, token=self.admin_token)
            if success:
                entrada_success += 1
                print(f"      ✅ Entrada with {method}")
            else:
                print(f"      ❌ Entrada with {method} - {data}")
        
        self.log_test("ENTRADA Payment Methods", entrada_success == len(entrada_methods), 
                     f"{entrada_success}/{len(entrada_methods)} methods worked")

        print("   Testing SAÍDA with allowed methods...")
        # Test SAÍDA with allowed methods (should work)
        saida_allowed = ['dinheiro', 'pix']
        saida_allowed_success = 0
        for method in saida_allowed:
            success, data = self.make_request('POST', 'transactions', {
                'type': 'saida',
                'amount': 50.0,
                'description': f'Test saida {method}',
                'payment_method': method
            }, token=self.admin_token)
            if success:
                saida_allowed_success += 1
                print(f"      ✅ Saída with {method} (allowed)")
            else:
                print(f"      ❌ Saída with {method} (allowed) - {data}")
        
        self.log_test("SAÍDA Allowed Payment Methods", saida_allowed_success == len(saida_allowed),
                     f"{saida_allowed_success}/{len(saida_allowed)} allowed methods worked")

        print("   Testing SAÍDA with restricted methods...")
        # Test SAÍDA with restricted methods (should fail)
        saida_restricted = ['cartao', 'boleto']
        saida_restricted_success = 0
        for method in saida_restricted:
            success, data = self.make_request('POST', 'transactions', {
                'type': 'saida',
                'amount': 50.0,
                'description': f'Test saida {method}',
                'payment_method': method
            }, token=self.admin_token, expected_status=400)
            if success:
                saida_restricted_success += 1
                print(f"      ✅ Saída with {method} (correctly blocked)")
            else:
                print(f"      ❌ Saída with {method} (should be blocked) - {data}")
        
        self.log_test("SAÍDA Restricted Payment Methods", saida_restricted_success == len(saida_restricted),
                     f"{saida_restricted_success}/{len(saida_restricted)} restricted methods correctly blocked")

    def test_client_management(self):
        """Test client creation and management"""
        if not self.admin_token:
            self.log_test("Client Management", False, "No admin token")
            return

        # Create test client
        client_data = {
            'name': 'Test Client',
            'email': 'client@test.com',
            'phone': '11999999999',
            'address': 'Test Address 123'
        }

        success, data = self.make_request('POST', 'clients', client_data, self.admin_token)
        if success:
            self.test_clients['main'] = data
            self.log_test("Create Client", True, f"Client ID: {data.get('id', 'N/A')}")
        else:
            self.log_test("Create Client", False, str(data))

        # Get clients list
        success, data = self.make_request('GET', 'clients', token=self.admin_token)
        self.log_test("Get Clients List", success, f"Found {len(data) if isinstance(data, list) else 0} clients" if success else str(data))

    def test_billing_system(self):
        """Test complete billing system with installments"""
        if not self.admin_token or 'main' not in self.test_clients:
            self.log_test("Billing System", False, "Missing admin token or client")
            return

        client_id = self.test_clients['main']['id']

        # Create bill with 3 installments
        bill_data = {
            'client_id': client_id,
            'total_amount': 300.0,
            'description': 'Test Bill with 3 installments',
            'installments': 3
        }

        success, data = self.make_request('POST', 'bills', bill_data, self.admin_token)
        if success:
            self.test_bills['main'] = data
            self.log_test("Create Bill with 3 Installments", True, f"Bill ID: {data.get('id', 'N/A')}")
        else:
            self.log_test("Create Bill with 3 Installments", False, str(data))
            return

        bill_id = data['id']

        # Get installments for the bill
        success, installments = self.make_request('GET', f'bills/{bill_id}/installments', token=self.admin_token)
        if success:
            self.log_test("Get Bill Installments", True, f"Found {len(installments)} installments")
            
            # Verify 3 installments were created
            if len(installments) == 3:
                self.log_test("Correct Number of Installments", True, "3 installments created as expected")
                
                # Test paying first installment with dinheiro
                first_installment = installments[0]
                success, data = self.make_request('PUT', f'installments/{first_installment["id"]}/pay', {
                    'payment_method': 'dinheiro'
                }, token=self.admin_token)
                self.log_test("Pay First Installment (Dinheiro)", success, 
                             f"Installment {first_installment['installment_number']} paid" if success else str(data))

                # Test paying second installment with PIX
                if len(installments) > 1:
                    second_installment = installments[1]
                    success, data = self.make_request('PUT', f'installments/{second_installment["id"]}/pay', {
                        'payment_method': 'pix'
                    }, token=self.admin_token)
                    self.log_test("Pay Second Installment (PIX)", success,
                                 f"Installment {second_installment['installment_number']} paid" if success else str(data))

            else:
                self.log_test("Correct Number of Installments", False, f"Expected 3, got {len(installments)}")
        else:
            self.log_test("Get Bill Installments", False, str(installments))

        # Test pending bills endpoint
        success, data = self.make_request('GET', 'bills/pending', token=self.admin_token)
        self.log_test("Get Pending Bills", success, f"Found {len(data) if isinstance(data, list) else 0} pending bills" if success else str(data))

    def test_activity_logs(self):
        """Test activity logging system"""
        if not self.admin_token:
            self.log_test("Activity Logs", False, "No admin token")
            return

        # Get activity logs
        success, logs = self.make_request('GET', 'activity-logs', token=self.admin_token)
        if success:
            self.log_test("Get Activity Logs", True, f"Found {len(logs)} log entries")
            
            # Check if logs contain expected activities
            log_types = [log.get('activity_type', '') for log in logs]
            
            expected_activities = ['login', 'user_created', 'transaction_created', 'bill_created']
            found_activities = []
            
            for activity in expected_activities:
                if any(activity in log_type for log_type in log_types):
                    found_activities.append(activity)
            
            self.log_test(f"Activity Logs Content", len(found_activities) > 0, 
                         f"Found activity types: {found_activities}")
        else:
            self.log_test("Get Activity Logs", False, str(logs))

    def test_user_activation_deactivation(self):
        """Test user activation/deactivation"""
        if not self.admin_token or 'manager' not in self.test_users:
            self.log_test("User Activation/Deactivation", False, "Missing requirements")
            return

        # Get users to find the manager user ID
        success, users = self.make_request('GET', 'users', token=self.admin_token)
        if not success:
            self.log_test("Get Users for Deactivation Test", False, str(users))
            return

        manager_user = None
        for user in users:
            if user['username'] == self.test_users['manager']['username']:
                manager_user = user
                break

        if not manager_user:
            self.log_test("Find Manager User for Deactivation", False, "Manager user not found")
            return

        # Deactivate user
        success, data = self.make_request('PUT', f'users/{manager_user["id"]}', {
            'active': False
        }, token=self.admin_token)
        self.log_test("Deactivate User", success, f"User {manager_user['username']} deactivated" if success else str(data))

        # Reactivate user
        success, data = self.make_request('PUT', f'users/{manager_user["id"]}', {
            'active': True
        }, token=self.admin_token)
        self.log_test("Reactivate User", success, f"User {manager_user['username']} reactivated" if success else str(data))

    def test_transaction_history(self):
        """Test transaction history with user details"""
        if not self.admin_token:
            self.log_test("Transaction History", False, "No admin token")
            return

        # Get transactions
        success, transactions = self.make_request('GET', 'transactions', token=self.admin_token)
        if success:
            self.log_test("Get Transaction History", True, f"Found {len(transactions)} transactions")
            
            # Check if transactions have user names
            if transactions:
                has_user_names = all('user_name' in t for t in transactions)
                self.log_test("Transactions Have User Names", has_user_names, 
                             "All transactions include user_name field" if has_user_names else "Some transactions missing user_name field")
            else:
                self.log_test("Transactions Have User Names", True, "No transactions to check")
        else:
            self.log_test("Get Transaction History", False, str(transactions))

        # Get transaction summary
        success, summary = self.make_request('GET', 'transactions/summary', token=self.admin_token)
        if success:
            self.log_test("Get Transaction Summary", True, 
                         f"Entrada: R${summary.get('total_entrada', 0):.2f}, Saída: R${summary.get('total_saida', 0):.2f}, Saldo: R${summary.get('saldo', 0):.2f}")
        else:
            self.log_test("Get Transaction Summary", False, str(summary))

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Comprehensive Backend API Tests")
        print(f"📡 Testing endpoint: {self.base_url}")
        print("=" * 60)

        # Authentication Tests
        print("\n🔐 Authentication Tests")
        if not self.test_admin_login():
            print("❌ Cannot proceed without admin login")
            return False

        # User Management Tests
        print("\n👥 User Management Tests")
        self.test_user_creation()
        self.test_user_login_roles()
        self.test_user_permissions()
        self.test_user_activation_deactivation()

        # Transaction Tests
        print("\n💰 Transaction Tests")
        self.test_transaction_payment_restrictions()
        self.test_transaction_history()

        # Client and Billing Tests
        print("\n🧾 Client and Billing Tests")
        self.test_client_management()
        self.test_billing_system()

        # Activity Logging Tests
        print("\n📊 Activity Logging Tests")
        self.test_activity_logs()

        return True

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")

        if self.errors:
            print(f"\n❌ FAILED TESTS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")

        print("\n" + "=" * 60)

def main():
    # Get backend URL from environment
    backend_url = "https://4b7a0316-949f-4a96-8246-8c7230b403be.preview.emergentagent.com"
    
    print(f"Testing backend at: {backend_url}")
    
    tester = CaixaAPITester(backend_url)
    
    try:
        success = tester.run_all_tests()
        tester.print_summary()
        
        # Return appropriate exit code
        if tester.tests_run == 0:
            print("⚠️  No tests were run!")
            return 1
        elif tester.tests_passed == tester.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())