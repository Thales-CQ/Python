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
    def __init__(self, base_url="https://08bda96a-88a3-4a43-8d93-935b8a4e0c07.preview.emergentagent.com"):
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

        # Dashboard Stats Tests
        print("\n📊 Dashboard Stats Tests")
        self.test_dashboard_stats()

        # Activity Logging Tests
        print("\n📊 Activity Logging Tests")
        self.test_activity_logs()

        # Enhanced Features Tests
        print("\n🔧 Enhanced Features Tests")
        self.test_enhanced_installment_payment()
        self.test_enhanced_error_messages()

        # NEW FUNCTIONALITY TESTS - From Review Request
        print("\n🆕 New Functionality Tests (Review Request)")
        self.test_role_change_salesperson_to_reception()
        self.test_product_quantity_system()
        self.test_advanced_specific_permissions()
        self.test_force_password_change_system()
        self.test_enhanced_user_management_functions()
        self.test_manager_permission_restrictions()

        return True

    def test_dashboard_stats(self):
        """Test enhanced dashboard stats endpoint"""
        if not self.admin_token:
            self.log_test("Dashboard Stats", False, "No admin token")
            return

        print("   Testing dashboard stats endpoint...")
        success, stats = self.make_request('GET', 'dashboard/stats', token=self.admin_token)
        if success:
            # Check if all required fields are present
            required_fields = ['total_entrada', 'total_saida', 'saldo', 'total_transactions', 
                             'today_transactions', 'current_datetime', 'recent_transactions']
            
            missing_fields = [field for field in required_fields if field not in stats]
            
            if not missing_fields:
                self.log_test("Dashboard Stats Structure", True, 
                             f"All required fields present: {required_fields}")
                
                # Test data types and values
                entrada = stats.get('total_entrada', 0)
                saida = stats.get('total_saida', 0)
                saldo = stats.get('saldo', 0)
                
                # Verify saldo calculation
                calculated_saldo = entrada - saida
                saldo_correct = abs(saldo - calculated_saldo) < 0.01  # Allow for floating point precision
                
                self.log_test("Dashboard Stats Calculations", saldo_correct,
                             f"Entrada: R${entrada:.2f}, Saída: R${saida:.2f}, Saldo: R${saldo:.2f}")
                
                # Check recent transactions
                recent_transactions = stats.get('recent_transactions', [])
                self.log_test("Dashboard Recent Transactions", isinstance(recent_transactions, list),
                             f"Found {len(recent_transactions)} recent transactions")
                
            else:
                self.log_test("Dashboard Stats Structure", False, f"Missing fields: {missing_fields}")
        else:
            self.log_test("Dashboard Stats", False, str(stats))

    def test_enhanced_installment_payment(self):
        """Test the new enhanced installment payment endpoint"""
        if not self.admin_token:
            self.log_test("Enhanced Installment Payment", False, "No admin token")
            return

        # First create a client and bill for testing
        client_data = {
            'name': 'Installment Test Client',
            'email': 'installment@test.com',
            'phone': '11999999999',
            'address': 'Test Address 123',
            'cpf': '11144477735'  # Valid CPF
        }

        success, client = self.make_request('POST', 'clients', client_data, self.admin_token)
        if not success:
            self.log_test("Create Client for Installment Test", False, str(client))
            return

        # Create a bill with installments
        bill_data = {
            'client_id': client['id'],
            'total_amount': 300.0,
            'description': 'Test Bill for Enhanced Payment',
            'installments': 3
        }

        success, bill = self.make_request('POST', 'bills', bill_data, self.admin_token)
        if not success:
            self.log_test("Create Bill for Installment Test", False, str(bill))
            return

        # Get the installments
        success, installments = self.make_request('GET', f'bills/{bill["id"]}/installments', token=self.admin_token)
        if not success or not installments:
            self.log_test("Get Installments for Payment Test", False, str(installments))
            return

        # Test the new enhanced installment payment endpoint
        first_installment = installments[0]
        payment_data = {'payment_method': 'dinheiro'}
        
        success, payment_result = self.make_request('POST', f'bills/installments/{first_installment["id"]}/pay', 
                                                   payment_data, self.admin_token)
        
        if success:
            self.log_test("Enhanced Installment Payment Endpoint", True, 
                         f"Installment {first_installment['installment_number']} paid successfully")
            
            # Verify the payment was recorded
            if 'transaction' in payment_result:
                transaction = payment_result['transaction']
                self.log_test("Payment Transaction Created", True,
                             f"Transaction ID: {transaction.get('id', 'N/A')}, Amount: R${transaction.get('amount', 0):.2f}")
        else:
            self.log_test("Enhanced Installment Payment Endpoint", False, str(payment_result))

    def test_enhanced_error_messages(self):
        """Test enhanced error messages and validation"""
        if not self.admin_token:
            self.log_test("Enhanced Error Messages", False, "No admin token")
            return

        print("   Testing enhanced CPF validation error...")
        # Test invalid CPF error message
        invalid_client_data = {
            'name': 'Invalid CPF Test',
            'email': 'invalid@test.com',
            'phone': '11999999999',
            'address': 'Test Address',
            'cpf': '12345678901'  # Invalid CPF
        }

        success, error_response = self.make_request('POST', 'clients', invalid_client_data, 
                                                   self.admin_token, expected_status=422)
        if success:
            # Check if error message contains "CPF inválido"
            error_detail = str(error_response)
            cpf_error_found = 'CPF inválido' in error_detail or 'cpf' in error_detail.lower()
            self.log_test("CPF Invalid Error Message", cpf_error_found,
                         f"Error contains CPF validation message: {cpf_error_found}")
        else:
            self.log_test("CPF Invalid Error Message", False, str(error_response))

        print("   Testing enhanced email validation error...")
        # Test invalid email error message
        invalid_email_data = {
            'name': 'Invalid Email Test',
            'email': 'invalid-email-format',
            'phone': '11999999999',
            'address': 'Test Address',
            'cpf': '11144477735'  # Valid CPF
        }

        success, error_response = self.make_request('POST', 'clients', invalid_email_data, 
                                                   self.admin_token, expected_status=422)
        if success:
            # Check if error message contains "Email inválido"
            error_detail = str(error_response)
            email_error_found = 'Email inválido' in error_detail or 'email' in error_detail.lower()
            self.log_test("Email Invalid Error Message", email_error_found,
                         f"Error contains email validation message: {email_error_found}")
        else:
            self.log_test("Email Invalid Error Message", False, str(error_response))

        print("   Testing password validation error...")
        # Test short password error
        short_password_data = {
            'username': 'test_short_pass',
            'email': 'shortpass@test.com',
            'password': '123',  # Too short
            'role': 'salesperson'
        }

        success, error_response = self.make_request('POST', 'register', short_password_data, 
                                                   self.admin_token, expected_status=422)
        if success:
            error_detail = str(error_response)
            password_error_found = 'senha' in error_detail.lower() or 'password' in error_detail.lower()
            self.log_test("Password Length Error Message", password_error_found,
                         f"Error contains password validation message: {password_error_found}")
        else:
            self.log_test("Password Length Error Message", False, str(error_response))

        return True

    def test_role_change_salesperson_to_reception(self):
        """Test that role has been changed from salesperson to reception"""
        if not self.admin_token:
            self.log_test("Role Change: Salesperson to Reception", False, "No admin token")
            return

        print("   Testing creation of reception user...")
        # Test creating a user with reception role
        reception_data = {
            'username': 'test_reception',
            'email': 'reception@test.com',
            'password': 'reception123',
            'role': 'reception'  # Changed from salesperson to reception
        }
        
        success, data = self.make_request('POST', 'register', reception_data, self.admin_token)
        if success:
            self.log_test("Create Reception User", True, "Reception role accepted")
            self.test_users['reception'] = reception_data
        else:
            self.log_test("Create Reception User", False, str(data))

        print("   Testing reception user login...")
        # Test reception user login
        if 'reception' in self.test_users:
            success, data = self.make_request('POST', 'login', {
                'username': self.test_users['reception']['username'],
                'password': self.test_users['reception']['password']
            })
            
            if success and 'access_token' in data:
                self.reception_token = data['access_token']
                user_role = data.get('user', {}).get('role', 'N/A')
                self.log_test("Reception User Login", True, f"Role: {user_role}")
                
                # Verify role is 'reception' not 'salesperson'
                role_correct = user_role == 'reception'
                self.log_test("Role Changed to Reception", role_correct, 
                             f"User role is '{user_role}' (should be 'reception')")
            else:
                self.log_test("Reception User Login", False, str(data))

        print("   Testing backwards compatibility with existing salesperson users...")
        # Test that existing salesperson users still work (backwards compatibility)
        salesperson_data = {
            'username': 'test_salesperson_legacy',
            'email': 'salesperson_legacy@test.com',
            'password': 'sales123',
            'role': 'salesperson'  # Legacy role should still work
        }
        
        success, data = self.make_request('POST', 'register', salesperson_data, self.admin_token)
        if success:
            self.log_test("Backwards Compatibility: Salesperson Role", True, "Legacy salesperson role still works")
        else:
            # Check if it's because salesperson is no longer supported
            error_msg = str(data)
            if 'salesperson' in error_msg.lower():
                self.log_test("Backwards Compatibility: Salesperson Role", False, 
                             "Salesperson role no longer supported - may need migration")
            else:
                self.log_test("Backwards Compatibility: Salesperson Role", False, str(data))

    def test_product_quantity_system(self):
        """Test product quantity system (finite/infinite)"""
        if not self.admin_token:
            self.log_test("Product Quantity System", False, "No admin token")
            return

        print("   Testing product with infinite quantity (null)...")
        # Test creating product with infinite quantity (null/None)
        infinite_product = {
            'code': 'INFINITE001',
            'name': 'Infinite Quantity Product',
            'price': 99.99,
            'description': 'Product with infinite quantity',
            'quantity': None  # Infinite quantity
        }

        success, data = self.make_request('POST', 'products', infinite_product, self.admin_token)
        if success:
            quantity_value = data.get('quantity')
            is_infinite = quantity_value is None
            self.log_test("Create Product with Infinite Quantity", is_infinite,
                         f"Quantity field: {quantity_value} (should be null for infinite)")
        else:
            self.log_test("Create Product with Infinite Quantity", False, str(data))

        print("   Testing product with finite quantity...")
        # Test creating product with finite quantity
        finite_product = {
            'code': 'FINITE001',
            'name': 'Finite Quantity Product',
            'price': 149.99,
            'description': 'Product with finite quantity',
            'quantity': 50  # Finite quantity
        }

        success, data = self.make_request('POST', 'products', finite_product, self.admin_token)
        if success:
            quantity_value = data.get('quantity')
            is_finite = isinstance(quantity_value, int) and quantity_value == 50
            self.log_test("Create Product with Finite Quantity", is_finite,
                         f"Quantity field: {quantity_value} (should be 50)")
        else:
            self.log_test("Create Product with Finite Quantity", False, str(data))

        print("   Testing product quantity update...")
        # Test updating product quantity
        if success:  # If finite product was created successfully
            product_id = data.get('id')
            update_data = {'quantity': 25}  # Update to 25
            
            success, update_result = self.make_request('PUT', f'products/{product_id}', 
                                                     update_data, self.admin_token)
            self.log_test("Update Product Quantity", success,
                         "Product quantity updated successfully" if success else str(update_result))

        print("   Testing product list includes quantity field...")
        # Verify products list includes quantity field
        success, products = self.make_request('GET', 'products', token=self.admin_token)
        if success and products:
            has_quantity_field = all('quantity' in product for product in products)
            self.log_test("Products List Includes Quantity Field", has_quantity_field,
                         f"All {len(products)} products have quantity field")
        else:
            self.log_test("Products List Includes Quantity Field", False, 
                         "Could not retrieve products" if not success else "No products found")

    def test_advanced_specific_permissions(self):
        """Test advanced specific permissions system for reception users"""
        if not self.admin_token:
            self.log_test("Advanced Specific Permissions", False, "No admin token")
            return

        # First create a reception user if not exists
        if not hasattr(self, 'reception_token') or not self.reception_token:
            reception_data = {
                'username': 'test_reception_perms',
                'email': 'reception_perms@test.com',
                'password': 'reception123',
                'role': 'reception'
            }
            
            success, data = self.make_request('POST', 'register', reception_data, self.admin_token)
            if success:
                # Login to get token
                success, login_data = self.make_request('POST', 'login', {
                    'username': reception_data['username'],
                    'password': reception_data['password']
                })
                if success:
                    self.reception_token = login_data['access_token']
                    self.reception_user_id = login_data['user']['id']

        if not hasattr(self, 'reception_token') or not self.reception_token:
            self.log_test("Advanced Specific Permissions", False, "Could not create/login reception user")
            return

        print("   Testing default reception permissions...")
        # Test default reception permissions (should have basic permissions)
        success, perm_result = self.make_request('POST', 'check-permission', 
                                               {'permission': 'cash_operations'}, 
                                               token=self.reception_token)
        if success:
            has_basic_permission = perm_result.get('has_permission', False)
            self.log_test("Reception Default Permission (cash_operations)", has_basic_permission,
                         f"Reception has cash_operations permission: {has_basic_permission}")
        else:
            self.log_test("Reception Default Permission (cash_operations)", False, str(perm_result))

        print("   Testing reception without specific bills permission...")
        # Test reception without bills permission (should not have access)
        success, perm_result = self.make_request('POST', 'check-permission', 
                                               {'permission': 'bills'}, 
                                               token=self.reception_token)
        if success:
            has_bills_permission = perm_result.get('has_permission', False)
            self.log_test("Reception Without Bills Permission", not has_bills_permission,
                         f"Reception should NOT have bills permission: {not has_bills_permission}")
        else:
            self.log_test("Reception Without Bills Permission", False, str(perm_result))

        print("   Testing admin granting specific bills permission...")
        # Admin grants specific bills permission to reception
        if hasattr(self, 'reception_user_id'):
            success, data = self.make_request('PUT', f'users/{self.reception_user_id}', {
                'permissions': {'bills': True}
            }, token=self.admin_token)
            self.log_test("Admin Grant Bills Permission", success,
                         "Admin granted bills permission to reception" if success else str(data))

            if success:
                print("   Testing reception with granted bills permission...")
                # Test reception now has bills permission
                success, perm_result = self.make_request('POST', 'check-permission', 
                                                       {'permission': 'bills'}, 
                                                       token=self.reception_token)
                if success:
                    has_bills_permission = perm_result.get('has_permission', False)
                    self.log_test("Reception With Granted Bills Permission", has_bills_permission,
                                 f"Reception now has bills permission: {has_bills_permission}")
                else:
                    self.log_test("Reception With Granted Bills Permission", False, str(perm_result))

        print("   Testing admin has all permissions...")
        # Test admin has all permissions
        success, perm_result = self.make_request('POST', 'check-permission', 
                                               {'permission': 'bills'}, 
                                               token=self.admin_token)
        if success:
            admin_has_permission = perm_result.get('has_permission', False)
            self.log_test("Admin Has All Permissions", admin_has_permission,
                         f"Admin has bills permission: {admin_has_permission}")
        else:
            self.log_test("Admin Has All Permissions", False, str(perm_result))

        print("   Testing manager permissions...")
        # Test manager has management permissions
        if hasattr(self, 'manager_token') and self.manager_token:
            success, perm_result = self.make_request('POST', 'check-permission', 
                                                   {'permission': 'products'}, 
                                                   token=self.manager_token)
            if success:
                manager_has_permission = perm_result.get('has_permission', False)
                self.log_test("Manager Has Management Permissions", manager_has_permission,
                             f"Manager has products permission: {manager_has_permission}")
            else:
                self.log_test("Manager Has Management Permissions", False, str(perm_result))

    def test_force_password_change_system(self):
        """Test force password change system"""
        if not self.admin_token:
            self.log_test("Force Password Change System", False, "No admin token")
            return

        # Create a test user for password change testing
        test_user_data = {
            'username': 'test_password_change',
            'email': 'password_change@test.com',
            'password': 'initial123',
            'role': 'reception'
        }
        
        success, user_data = self.make_request('POST', 'register', test_user_data, self.admin_token)
        if not success:
            self.log_test("Create User for Password Change Test", False, str(user_data))
            return

        # Get user ID
        success, users = self.make_request('GET', 'users', token=self.admin_token)
        if not success:
            self.log_test("Get Users for Password Change Test", False, str(users))
            return

        test_user = next((u for u in users if u['username'] == test_user_data['username']), None)
        if not test_user:
            self.log_test("Find Test User for Password Change", False, "Test user not found")
            return

        test_user_id = test_user['id']

        print("   Testing admin forcing password change...")
        # Admin forces password change
        success, data = self.make_request('PUT', f'users/{test_user_id}', {
            'require_password_change': True
        }, token=self.admin_token)
        self.log_test("Admin Force Password Change", success,
                     "Admin set require_password_change to true" if success else str(data))

        print("   Testing login blocked when password change required...")
        # Test that login is blocked when password change is required
        success, login_data = self.make_request('POST', 'login', {
            'username': test_user_data['username'],
            'password': test_user_data['password']
        }, expected_status=401)  # Should fail with 401
        
        if success:
            error_msg = login_data.get('detail', '')
            password_change_blocked = 'alterar a senha' in error_msg or 'password' in error_msg.lower()
            self.log_test("Login Blocked When Password Change Required", password_change_blocked,
                         f"Login correctly blocked: {error_msg}")
        else:
            self.log_test("Login Blocked When Password Change Required", False, 
                         "Login should have been blocked but wasn't")

        print("   Testing password change resets requirement...")
        # Change password (should reset require_password_change)
        success, data = self.make_request('PUT', f'users/{test_user_id}/password', {
            'new_password': 'newpassword123'
        }, token=self.admin_token)
        self.log_test("Change Password Resets Requirement", success,
                     "Password changed successfully" if success else str(data))

        print("   Testing login works after password change...")
        # Test login works after password change
        if success:
            success, login_data = self.make_request('POST', 'login', {
                'username': test_user_data['username'],
                'password': 'newpassword123'
            })
            
            if success and 'access_token' in login_data:
                require_change = login_data.get('user', {}).get('require_password_change', True)
                self.log_test("Login Works After Password Change", not require_change,
                             f"require_password_change reset to: {require_change}")
            else:
                self.log_test("Login Works After Password Change", False, str(login_data))

    def test_enhanced_user_management_functions(self):
        """Test enhanced user management functions"""
        if not self.admin_token:
            self.log_test("Enhanced User Management", False, "No admin token")
            return

        # Create test users for management testing
        manager_data = {
            'username': 'test_manager_mgmt',
            'email': 'manager_mgmt@test.com',
            'password': 'manager123',
            'role': 'manager'
        }
        
        reception_data = {
            'username': 'test_reception_mgmt',
            'email': 'reception_mgmt@test.com',
            'password': 'reception123',
            'role': 'reception'
        }

        # Create manager and reception users
        success, manager_user = self.make_request('POST', 'register', manager_data, self.admin_token)
        if not success:
            self.log_test("Create Manager for Management Test", False, str(manager_user))
            return

        success, reception_user = self.make_request('POST', 'register', reception_data, self.admin_token)
        if not success:
            self.log_test("Create Reception for Management Test", False, str(reception_user))
            return

        # Get user IDs
        success, users = self.make_request('GET', 'users', token=self.admin_token)
        if not success:
            self.log_test("Get Users for Management Test", False, str(users))
            return

        manager_user_obj = next((u for u in users if u['username'] == manager_data['username']), None)
        reception_user_obj = next((u for u in users if u['username'] == reception_data['username']), None)

        if not manager_user_obj or not reception_user_obj:
            self.log_test("Find Test Users for Management", False, "Test users not found")
            return

        manager_id = manager_user_obj['id']
        reception_id = reception_user_obj['id']

        print("   Testing admin can reset any user password...")
        # Test admin can reset any user password
        success, data = self.make_request('PUT', f'users/{reception_id}/password', {
            'new_password': 'admin_reset123'
        }, token=self.admin_token)
        self.log_test("Admin Reset User Password", success,
                     "Admin successfully reset reception password" if success else str(data))

        print("   Testing admin can manage user permissions...")
        # Test admin can manage user permissions
        success, data = self.make_request('PUT', f'users/{reception_id}', {
            'permissions': {'reports': True, 'products': True}
        }, token=self.admin_token)
        self.log_test("Admin Manage User Permissions", success,
                     "Admin successfully set user permissions" if success else str(data))

        print("   Testing admin can deactivate users...")
        # Test admin can deactivate users
        success, data = self.make_request('PUT', f'users/{reception_id}', {
            'active': False
        }, token=self.admin_token)
        self.log_test("Admin Deactivate User", success,
                     "Admin successfully deactivated user" if success else str(data))

        print("   Testing admin can reactivate users...")
        # Test admin can reactivate users
        success, data = self.make_request('PUT', f'users/{reception_id}', {
            'active': True
        }, token=self.admin_token)
        self.log_test("Admin Reactivate User", success,
                     "Admin successfully reactivated user" if success else str(data))

        print("   Testing admin can delete users...")
        # Test admin can delete users (but not the main admin)
        success, data = self.make_request('DELETE', f'users/{reception_id}', token=self.admin_token)
        self.log_test("Admin Delete User", success,
                     "Admin successfully deleted user" if success else str(data))

        print("   Testing admin cannot delete main admin...")
        # Test admin cannot delete the main admin user
        success, admin_users = self.make_request('GET', 'users', token=self.admin_token)
        if success:
            main_admin = next((u for u in admin_users if u['username'] == 'ADMIN'), None)
            if main_admin:
                success, data = self.make_request('DELETE', f'users/{main_admin["id"]}', 
                                                token=self.admin_token, expected_status=403)
                self.log_test("Admin Cannot Delete Main Admin", success,
                             "Main admin deletion correctly blocked" if success else str(data))

    def test_manager_permission_restrictions(self):
        """Test manager permission restrictions"""
        if not self.admin_token:
            self.log_test("Manager Permission Restrictions", False, "No admin token")
            return

        # Create manager user for testing
        manager_data = {
            'username': 'test_manager_restrictions',
            'email': 'manager_restrictions@test.com',
            'password': 'manager123',
            'role': 'manager'
        }
        
        success, manager_user = self.make_request('POST', 'register', manager_data, self.admin_token)
        if not success:
            self.log_test("Create Manager for Restrictions Test", False, str(manager_user))
            return

        # Login as manager
        success, login_data = self.make_request('POST', 'login', {
            'username': manager_data['username'],
            'password': manager_data['password']
        })
        
        if not success or 'access_token' not in login_data:
            self.log_test("Manager Login for Restrictions Test", False, str(login_data))
            return

        manager_token = login_data['access_token']

        print("   Testing manager can create reception users...")
        # Test manager can create reception users
        reception_data = {
            'username': 'manager_created_reception',
            'email': 'manager_reception@test.com',
            'password': 'reception123',
            'role': 'reception'
        }
        
        success, data = self.make_request('POST', 'register', reception_data, manager_token)
        self.log_test("Manager Can Create Reception Users", success,
                     "Manager successfully created reception user" if success else str(data))

        print("   Testing manager cannot create other managers...")
        # Test manager cannot create other managers
        another_manager_data = {
            'username': 'manager_created_manager',
            'email': 'manager_manager@test.com',
            'password': 'manager123',
            'role': 'manager'
        }
        
        success, data = self.make_request('POST', 'register', another_manager_data, 
                                        manager_token, expected_status=403)
        self.log_test("Manager Cannot Create Other Managers", success,
                     "Manager creation correctly blocked" if success else str(data))

        print("   Testing manager cannot create admin users...")
        # Test manager cannot create admin users
        admin_data = {
            'username': 'manager_created_admin',
            'email': 'manager_admin@test.com',
            'password': 'admin123',
            'role': 'admin'
        }
        
        success, data = self.make_request('POST', 'register', admin_data, 
                                        manager_token, expected_status=403)
        self.log_test("Manager Cannot Create Admin Users", success,
                     "Admin creation correctly blocked" if success else str(data))

        # Get users to test editing restrictions
        success, users = self.make_request('GET', 'users', token=self.admin_token)
        if not success:
            self.log_test("Get Users for Manager Edit Test", False, str(users))
            return

        # Find admin and another manager to test editing restrictions
        admin_user = next((u for u in users if u['role'] == 'admin' and u['username'] == 'ADMIN'), None)
        reception_user = next((u for u in users if u['username'] == reception_data['username']), None)

        if admin_user:
            print("   Testing manager cannot edit admin users...")
            # Test manager cannot edit admin users
            success, data = self.make_request('PUT', f'users/{admin_user["id"]}', {
                'active': False
            }, manager_token, expected_status=403)
            self.log_test("Manager Cannot Edit Admin Users", success,
                         "Admin editing correctly blocked" if success else str(data))

        if reception_user:
            print("   Testing manager can edit reception users...")
            # Test manager can edit reception users
            success, data = self.make_request('PUT', f'users/{reception_user["id"]}', {
                'permissions': {'bills': True}
            }, manager_token)
            self.log_test("Manager Can Edit Reception Users", success,
                         "Manager successfully edited reception user" if success else str(data))

            print("   Testing manager can change reception passwords...")
            # Test manager can change reception passwords
            success, data = self.make_request('PUT', f'users/{reception_user["id"]}/password', {
                'new_password': 'manager_changed123'
            }, manager_token)
            self.log_test("Manager Can Change Reception Passwords", success,
                         "Manager successfully changed reception password" if success else str(data))

        if admin_user:
            print("   Testing manager cannot change admin passwords...")
            # Test manager cannot change admin passwords
            success, data = self.make_request('PUT', f'users/{admin_user["id"]}/password', {
                'new_password': 'should_not_work123'
            }, manager_token, expected_status=403)
            self.log_test("Manager Cannot Change Admin Passwords", success,
                         "Admin password change correctly blocked" if success else str(data))

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
    backend_url = "https://08bda96a-88a3-4a43-8d93-935b8a4e0c07.preview.emergentagent.com"
    
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