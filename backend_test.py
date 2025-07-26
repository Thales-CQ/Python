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
    def __init__(self, base_url="https://cefc370c-9290-41bc-bb27-a556498755ba.preview.emergentagent.com"):
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

    def test_uppercase_conversion(self):
        """Test automatic uppercase conversion in all forms"""
        if not self.admin_token:
            self.log_test("Uppercase Conversion", False, "No admin token")
            return

        print("   Testing uppercase conversion in user creation...")
        # Test user creation with lowercase input
        user_data = {
            'username': 'lowercase_user',
            'email': 'lowercase@test.com',
            'password': 'test123',
            'role': 'salesperson'
        }
        
        success, data = self.make_request('POST', 'register', user_data, self.admin_token)
        if success:
            # Get the created user to verify uppercase conversion
            success_get, users = self.make_request('GET', 'users', token=self.admin_token)
            if success_get:
                created_user = next((u for u in users if 'LOWERCASE_USER' in u['username']), None)
                if created_user:
                    uppercase_correct = (created_user['username'] == 'LOWERCASE_USER' and 
                                       created_user['email'] == 'LOWERCASE@TEST.COM')
                    self.log_test("User Fields Uppercase Conversion", uppercase_correct,
                                 f"Username: {created_user['username']}, Email: {created_user['email']}")
                else:
                    self.log_test("User Fields Uppercase Conversion", False, "Created user not found")
            else:
                self.log_test("User Fields Uppercase Conversion", False, "Could not retrieve users")
        else:
            self.log_test("User Fields Uppercase Conversion", False, str(data))

    def test_cpf_validation(self):
        """Test CPF validation and formatting"""
        if not self.admin_token:
            self.log_test("CPF Validation", False, "No admin token")
            return

        print("   Testing valid CPF...")
        # Test with valid CPF
        valid_client_data = {
            'name': 'Valid CPF Client',
            'email': 'validcpf@test.com',
            'phone': '11999999999',
            'address': 'Test Address 123',
            'cpf': '11144477735'  # Valid CPF
        }

        success, data = self.make_request('POST', 'clients', valid_client_data, self.admin_token)
        if success:
            # Check if CPF was formatted correctly
            formatted_cpf = data.get('cpf', '')
            expected_format = '111.444.777-35'
            cpf_formatted_correctly = formatted_cpf == expected_format
            self.log_test("Valid CPF Creation and Formatting", cpf_formatted_correctly,
                         f"CPF formatted as: {formatted_cpf}")
            if success:
                self.test_clients['valid_cpf'] = data
        else:
            self.log_test("Valid CPF Creation and Formatting", False, str(data))

        print("   Testing invalid CPF...")
        # Test with invalid CPF
        invalid_client_data = {
            'name': 'Invalid CPF Client',
            'email': 'invalidcpf@test.com',
            'phone': '11999999999',
            'address': 'Test Address 123',
            'cpf': '12345678901'  # Invalid CPF
        }

        success, data = self.make_request('POST', 'clients', invalid_client_data, 
                                        self.admin_token, expected_status=422)
        self.log_test("Invalid CPF Rejection", success, 
                     "Invalid CPF correctly rejected" if success else f"Should have been rejected: {data}")

        print("   Testing duplicate CPF...")
        # Test duplicate CPF
        if 'valid_cpf' in self.test_clients:
            duplicate_client_data = {
                'name': 'Duplicate CPF Client',
                'email': 'duplicate@test.com',
                'phone': '11999999999',
                'address': 'Test Address 456',
                'cpf': '11144477735'  # Same CPF as before
            }

            success, data = self.make_request('POST', 'clients', duplicate_client_data, 
                                            self.admin_token, expected_status=400)
            self.log_test("Duplicate CPF Rejection", success,
                         "Duplicate CPF correctly rejected" if success else f"Should have been rejected: {data}")

    def test_product_system(self):
        """Test product creation, search, and admin visibility"""
        if not self.admin_token:
            self.log_test("Product System", False, "No admin token")
            return

        print("   Testing product creation with unique code...")
        # Create test product
        product_data = {
            'code': 'TEST001',
            'name': 'Test Product One',
            'price': 99.99,
            'description': 'Test product description'
        }

        success, data = self.make_request('POST', 'products', product_data, self.admin_token)
        if success:
            self.log_test("Create Product with Unique Code", True, 
                         f"Product created: {data.get('code', 'N/A')} - {data.get('name', 'N/A')}")
            
            # Verify uppercase conversion
            uppercase_correct = (data.get('code') == 'TEST001' and 
                               data.get('name') == 'TEST PRODUCT ONE' and
                               data.get('description') == 'TEST PRODUCT DESCRIPTION')
            self.log_test("Product Fields Uppercase Conversion", uppercase_correct,
                         f"Code: {data.get('code')}, Name: {data.get('name')}")
        else:
            self.log_test("Create Product with Unique Code", False, str(data))

        # Create second product for search testing
        product_data2 = {
            'code': 'TEST002',
            'name': 'Another Test Product',
            'price': 149.99,
            'description': 'Another test product'
        }

        success, data = self.make_request('POST', 'products', product_data2, self.admin_token)
        self.log_test("Create Second Product", success, 
                     f"Second product created" if success else str(data))

        print("   Testing duplicate product code rejection...")
        # Test duplicate product code
        duplicate_product = {
            'code': 'TEST001',  # Same code as first product
            'name': 'Duplicate Code Product',
            'price': 199.99,
            'description': 'Should not be created'
        }

        success, data = self.make_request('POST', 'products', duplicate_product, 
                                        self.admin_token, expected_status=400)
        self.log_test("Duplicate Product Code Rejection", success,
                     "Duplicate code correctly rejected" if success else f"Should have been rejected: {data}")

        print("   Testing product search by code...")
        # Test product search by code
        success, data = self.make_request('GET', 'products/search?q=TEST001', token=self.admin_token)
        if success:
            found_product = len(data) > 0 and any(p.get('code') == 'TEST001' for p in data)
            self.log_test("Product Search by Code", found_product,
                         f"Found {len(data)} products, TEST001 found: {found_product}")
        else:
            self.log_test("Product Search by Code", False, str(data))

        print("   Testing product search by name...")
        # Test product search by name
        success, data = self.make_request('GET', 'products/search?q=ANOTHER', token=self.admin_token)
        if success:
            found_product = len(data) > 0 and any('ANOTHER' in p.get('name', '') for p in data)
            self.log_test("Product Search by Name", found_product,
                         f"Found {len(data)} products with 'ANOTHER' in name")
        else:
            self.log_test("Product Search by Name", False, str(data))

        print("   Testing admin can see all products...")
        # Test admin can see products
        success, data = self.make_request('GET', 'products', token=self.admin_token)
        self.log_test("Admin Can See Products", success,
                     f"Admin can see {len(data) if isinstance(data, list) else 0} products" if success else str(data))

    def test_transaction_filters(self):
        """Test transaction filtering by various criteria"""
        if not self.admin_token:
            self.log_test("Transaction Filters", False, "No admin token")
            return

        # Create some test transactions first
        test_transactions = [
            {
                'type': 'entrada',
                'amount': 100.0,
                'description': 'FILTER TEST ENTRADA',
                'payment_method': 'dinheiro'
            },
            {
                'type': 'saida',
                'amount': 50.0,
                'description': 'FILTER TEST SAIDA',
                'payment_method': 'pix'
            },
            {
                'type': 'entrada',
                'amount': 200.0,
                'description': 'CARTAO TEST TRANSACTION',
                'payment_method': 'cartao'
            }
        ]

        print("   Creating test transactions for filtering...")
        for i, trans_data in enumerate(test_transactions):
            success, data = self.make_request('POST', 'transactions', trans_data, self.admin_token)
            if success:
                print(f"      ✅ Created test transaction {i+1}")
            else:
                print(f"      ❌ Failed to create test transaction {i+1}: {data}")

        print("   Testing filter by description/name...")
        # Test filter by search term
        success, data = self.make_request('GET', 'transactions?search=FILTER', token=self.admin_token)
        if success:
            filter_matches = [t for t in data if 'FILTER' in t.get('description', '')]
            self.log_test("Filter by Description", len(filter_matches) >= 2,
                         f"Found {len(filter_matches)} transactions with 'FILTER' in description")
        else:
            self.log_test("Filter by Description", False, str(data))

        print("   Testing filter by transaction type...")
        # Test filter by type
        success, data = self.make_request('GET', 'transactions?transaction_type=entrada', token=self.admin_token)
        if success:
            entrada_only = all(t.get('type') == 'entrada' for t in data)
            self.log_test("Filter by Type (ENTRADA)", entrada_only,
                         f"All {len(data)} transactions are ENTRADA type: {entrada_only}")
        else:
            self.log_test("Filter by Type (ENTRADA)", False, str(data))

        print("   Testing filter by payment method...")
        # Test filter by payment method
        success, data = self.make_request('GET', 'transactions?payment_method=cartao', token=self.admin_token)
        if success:
            cartao_only = all(t.get('payment_method') == 'cartao' for t in data)
            self.log_test("Filter by Payment Method (CARTAO)", cartao_only,
                         f"All {len(data)} transactions use CARTAO: {cartao_only}")
        else:
            self.log_test("Filter by Payment Method (CARTAO)", False, str(data))

        print("   Testing filter by month/year...")
        # Test filter by current month/year
        current_date = datetime.now()
        success, data = self.make_request('GET', 
                                        f'transactions?month={current_date.month}&year={current_date.year}', 
                                        token=self.admin_token)
        self.log_test("Filter by Month/Year", success,
                     f"Found {len(data) if isinstance(data, list) else 0} transactions for current month" if success else str(data))

    def test_pdf_generation(self):
        """Test PDF report generation"""
        if not self.admin_token:
            self.log_test("PDF Generation", False, "No admin token")
            return

        print("   Testing PDF generation for all transactions...")
        # Test PDF generation for all transactions
        success, response_data = self.make_request('GET', 'reports/transactions/pdf', token=self.admin_token)
        
        # For PDF, we expect binary data, so we need to check differently
        if 'error' not in str(response_data):
            self.log_test("Generate PDF Report (All Transactions)", True, "PDF generated successfully")
        else:
            self.log_test("Generate PDF Report (All Transactions)", False, str(response_data))

        print("   Testing PDF generation for specific month...")
        # Test PDF generation for specific month
        current_date = datetime.now()
        success, response_data = self.make_request('GET', 
                                                 f'reports/transactions/pdf?month={current_date.month}&year={current_date.year}', 
                                                 token=self.admin_token)
        
        if 'error' not in str(response_data):
            self.log_test("Generate PDF Report (Current Month)", True, "Monthly PDF generated successfully")
        else:
            self.log_test("Generate PDF Report (Current Month)", False, str(response_data))

    def test_cancellation_features(self):
        """Test cancellation features for transactions, payments, and bills"""
        if not self.admin_token:
            self.log_test("Cancellation Features", False, "No admin token")
            return

        print("   Testing transaction cancellation...")
        # Create a transaction to cancel
        trans_data = {
            'type': 'entrada',
            'amount': 150.0,
            'description': 'TRANSACTION TO CANCEL',
            'payment_method': 'dinheiro'
        }

        success, transaction = self.make_request('POST', 'transactions', trans_data, self.admin_token)
        if success:
            transaction_id = transaction.get('id')
            
            # Cancel the transaction
            success, data = self.make_request('DELETE', f'transactions/{transaction_id}', token=self.admin_token)
            self.log_test("Cancel Transaction (Admin)", success,
                         "Transaction cancelled successfully" if success else str(data))
            
            # Verify transaction appears as cancelled
            success, transactions = self.make_request('GET', 'transactions', token=self.admin_token)
            if success:
                cancelled_transaction = next((t for t in transactions if t.get('id') == transaction_id), None)
                if cancelled_transaction:
                    is_cancelled = cancelled_transaction.get('cancelled', False)
                    self.log_test("Transaction Shows as Cancelled", is_cancelled,
                                 f"Transaction cancelled status: {is_cancelled}")
                else:
                    self.log_test("Transaction Shows as Cancelled", False, "Cancelled transaction not found")
        else:
            self.log_test("Create Transaction for Cancellation Test", False, str(transaction))

        print("   Testing bill and payment cancellation...")
        # Test bill cancellation if we have a test bill
        if 'main' in self.test_bills:
            bill_id = self.test_bills['main']['id']
            
            # Get installments
            success, installments = self.make_request('GET', f'bills/{bill_id}/installments', token=self.admin_token)
            if success and installments:
                # Find a paid installment to cancel payment
                paid_installment = next((inst for inst in installments if inst.get('status') == 'paid'), None)
                
                if paid_installment:
                    print("      Testing payment cancellation...")
                    success, data = self.make_request('DELETE', f'installments/{paid_installment["id"]}/cancel', 
                                                    token=self.admin_token)
                    self.log_test("Cancel Installment Payment (Manager)", success,
                                 f"Payment cancelled for installment {paid_installment['installment_number']}" if success else str(data))
                
                print("      Testing entire bill cancellation...")
                # Cancel entire bill
                success, data = self.make_request('DELETE', f'bills/{bill_id}/cancel', token=self.admin_token)
                self.log_test("Cancel Entire Bill (Manager)", success,
                             "Entire bill cancelled successfully" if success else str(data))

    def test_client_management(self):
        """Test client creation and management"""
        if not self.admin_token:
            self.log_test("Client Management", False, "No admin token")
            return

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
        """Test activity logging system with enhanced filtering"""
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

        # Test activity log filtering by date
        print("   Testing activity log filtering by date...")
        today = datetime.now().strftime('%Y-%m-%d')
        success, filtered_logs = self.make_request('GET', f'activity-logs?start_date={today}', token=self.admin_token)
        if success:
            self.log_test("Filter Activity Logs by Date", True, f"Found {len(filtered_logs)} logs for today")
        else:
            self.log_test("Filter Activity Logs by Date", False, str(filtered_logs))

        # Test activity log filtering by user name
        print("   Testing activity log filtering by user name...")
        success, filtered_logs = self.make_request('GET', 'activity-logs?user_name=ADMIN', token=self.admin_token)
        if success:
            admin_logs = [log for log in filtered_logs if 'ADMIN' in log.get('user_name', '')]
            self.log_test("Filter Activity Logs by User Name", len(admin_logs) > 0, 
                         f"Found {len(admin_logs)} logs for ADMIN user")
        else:
            self.log_test("Filter Activity Logs by User Name", False, str(filtered_logs))

        # Test activity log filtering by activity type
        print("   Testing activity log filtering by activity type...")
        success, filtered_logs = self.make_request('GET', 'activity-logs?activity_type=login', token=self.admin_token)
        if success:
            login_logs = [log for log in filtered_logs if log.get('activity_type') == 'login']
            self.log_test("Filter Activity Logs by Activity Type", len(login_logs) > 0,
                         f"Found {len(login_logs)} login activity logs")
        else:
            self.log_test("Filter Activity Logs by Activity Type", False, str(filtered_logs))

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

        # NEW: Uppercase Conversion Tests
        print("\n🔤 Uppercase Conversion Tests")
        self.test_uppercase_conversion()

        # NEW: CPF Validation Tests
        print("\n🆔 CPF Validation Tests")
        self.test_cpf_validation()

        # NEW: Product System Tests
        print("\n📦 Product System Tests")
        self.test_product_system()

        # Transaction Tests
        print("\n💰 Transaction Tests")
        self.test_transaction_payment_restrictions()
        self.test_transaction_history()

        # NEW: Transaction Filter Tests
        print("\n🔍 Transaction Filter Tests")
        self.test_transaction_filters()

        # NEW: PDF Generation Tests
        print("\n📄 PDF Generation Tests")
        self.test_pdf_generation()

        # Client and Billing Tests
        print("\n🧾 Client and Billing Tests")
        self.test_client_management()
        self.test_billing_system()

        # NEW: Cancellation Feature Tests
        print("\n❌ Cancellation Feature Tests")
        self.test_cancellation_features()

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
    backend_url = "https://cefc370c-9290-41bc-bb27-a556498755ba.preview.emergentagent.com"
    
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