#!/usr/bin/env python3
"""
Focused Test for Vendas Role Permissions - Review Request Priority
Tests specifically the updated permissions for vendas users
"""

import requests
import sys
import json
import uuid
from datetime import datetime

class VendasPermissionsTest:
    def __init__(self, base_url="https://08bda96a-88a3-4a43-8d93-935b8a4e0c07.preview.emergentagent.com"):
        self.base_url = base_url.rstrip('/')
        self.admin_token = None
        self.vendas_token = None
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

    def make_request(self, method: str, endpoint: str, data=None, token=None, expected_status: int = 200):
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

    def setup_admin_login(self):
        """Login as admin"""
        success, data = self.make_request('POST', 'login', {
            'username': 'ADMIN',
            'password': '!$3man@d3c1%'
        })
        
        if success and 'access_token' in data:
            self.admin_token = data['access_token']
            self.log_test("Admin Login", True, f"Role: {data.get('user', {}).get('role', 'N/A')}")
            return True
        else:
            self.log_test("Admin Login", False, str(data))
            return False

    def setup_vendas_user(self):
        """Create and login vendas user"""
        # Generate unique username to avoid conflicts
        unique_id = str(uuid.uuid4())[:8]
        vendas_data = {
            'username': f'VENDAS_TEST_{unique_id}',
            'email': f'vendas.test.{unique_id}@teste.com',
            'password': '123456',
            'role': 'vendas'
        }
        
        success, user_result = self.make_request('POST', 'register', vendas_data, self.admin_token)
        if not success:
            self.log_test("Create Vendas User", False, str(user_result))
            return False
        
        # Login as vendas user
        success, login_data = self.make_request('POST', 'login', {
            'username': vendas_data['username'],
            'password': vendas_data['password']
        })
        
        if not success or 'access_token' not in login_data:
            self.log_test("Vendas User Login", False, str(login_data))
            return False
            
        self.vendas_token = login_data['access_token']
        self.vendas_username = vendas_data['username']
        self.log_test("Vendas User Login", True, f"Role: {login_data.get('user', {}).get('role', 'N/A')}")
        return True

    def test_vendas_can_create_clients(self):
        """Test that vendas users can create clients (POST /api/clients)"""
        print("   🔍 Testing vendas can CREATE clients (POST /api/clients)...")
        
        unique_id = str(uuid.uuid4())[:8]
        client_data = {
            'name': f'Cliente Vendas {unique_id}',
            'email': f'cliente.vendas.{unique_id}@teste.com',
            'phone': '11999999999',
            'address': 'Rua Teste 123',
            'cpf': '52998224725'  # Different valid CPF
        }
        
        success, client_result = self.make_request('POST', 'clients', client_data, self.vendas_token)
        self.log_test("Vendas Can CREATE Clients", success, 
                     f"Client created: {client_result.get('name', 'N/A')}" if success else str(client_result))
        
        return client_result.get('id') if success else None

    def test_vendas_can_update_clients(self, client_id):
        """Test that vendas users can update clients (PUT /api/clients/{id})"""
        if not client_id:
            self.log_test("Vendas Can UPDATE Clients", False, "No client ID available")
            return
            
        print("   🔍 Testing vendas can UPDATE clients (PUT /api/clients/{id})...")
        
        update_data = {
            'phone': '11888888888',
            'address': 'Rua Atualizada 456'
        }
        
        success, update_result = self.make_request('PUT', f'clients/{client_id}', 
                                                 update_data, self.vendas_token)
        self.log_test("Vendas Can UPDATE Clients", success,
                     "Client updated successfully" if success else str(update_result))

    def test_vendas_can_view_clients(self):
        """Test that vendas users can view clients (GET /api/clients)"""
        print("   🔍 Testing vendas can VIEW clients (GET /api/clients)...")
        
        success, clients_result = self.make_request('GET', 'clients', token=self.vendas_token)
        self.log_test("Vendas Can VIEW Clients", success,
                     f"Found {len(clients_result) if isinstance(clients_result, list) else 0} clients" if success else str(clients_result))

    def test_vendas_can_view_products(self):
        """Test that vendas users can view products (GET /api/products)"""
        print("   🔍 Testing vendas can VIEW products (GET /api/products)...")
        
        success, products_result = self.make_request('GET', 'products', token=self.vendas_token)
        self.log_test("Vendas Can VIEW Products", success,
                     f"Found {len(products_result) if isinstance(products_result, list) else 0} products" if success else str(products_result))
        
        return products_result if success else []

    def test_vendas_can_create_sales(self, client_id, products):
        """Test that vendas users can create sales (POST /api/sales)"""
        print("   🔍 Testing vendas can CREATE sales (POST /api/sales)...")
        
        if not client_id:
            self.log_test("Vendas Can CREATE Sales", False, "No client available for sale test")
            return
            
        if not products or not isinstance(products, list):
            self.log_test("Vendas Can CREATE Sales", False, "No products available for sale test")
            return
            
        product_id = products[0].get('id')
        if not product_id:
            self.log_test("Vendas Can CREATE Sales", False, "No valid product ID found")
            return
            
        sale_data = {
            'client_id': client_id,
            'product_id': product_id,
            'quantity': 2,
            'payment_method': 'dinheiro'
        }
        
        success, sale_result = self.make_request('POST', 'sales', sale_data, self.vendas_token)
        self.log_test("Vendas Can CREATE Sales", success,
                     f"Sale created: R${sale_result.get('total_value', 0):.2f}" if success else str(sale_result))

    def test_vendas_security_restrictions(self):
        """Test that vendas users are properly restricted from other operations"""
        print("   🔒 Testing vendas SECURITY RESTRICTIONS...")
        
        # Test 1: Cannot create products
        product_data = {
            'code': f'VENDAS_TEST_{str(uuid.uuid4())[:8]}',
            'name': 'Produto Teste Vendas',
            'price': 99.99,
            'description': 'Should not be created'
        }
        
        success, product_result = self.make_request('POST', 'products', product_data, 
                                                   self.vendas_token, expected_status=403)
        self.log_test("Vendas CANNOT CREATE Products", success,
                     "Correctly blocked from creating products" if success else f"SECURITY ISSUE: {product_result}")

        # Test 2: Cannot access performance dashboard
        success, dashboard_result = self.make_request('GET', 'performance/dashboard', 
                                                     token=self.vendas_token, expected_status=403)
        self.log_test("Vendas CANNOT ACCESS Performance Dashboard", success,
                     "Correctly blocked from performance dashboard" if success else f"SECURITY ISSUE: {dashboard_result}")

        # Test 3: Cannot manage users
        success, users_result = self.make_request('GET', 'users', 
                                                 token=self.vendas_token, expected_status=403)
        self.log_test("Vendas CANNOT MANAGE Users", success,
                     "Correctly blocked from user management" if success else f"SECURITY ISSUE: {users_result}")

        # Test 4: Cannot create bills
        success, bill_result = self.make_request('POST', 'bills', {
            'client_id': 'dummy_id',
            'total_amount': 300.0,
            'description': 'Should not be created',
            'installments': 3
        }, self.vendas_token, expected_status=403)
        self.log_test("Vendas CANNOT CREATE Bills", success,
                     "Correctly blocked from creating bills" if success else f"SECURITY ISSUE: {bill_result}")

    def run_tests(self):
        """Run all vendas permission tests"""
        print("🎯 VENDAS ROLE PERMISSIONS TESTING")
        print("=" * 60)
        print("Testing updated permissions for vendas users:")
        print("✓ Should be able to CREATE clients (POST /api/clients)")
        print("✓ Should be able to UPDATE clients (PUT /api/clients/{id})")
        print("✓ Should be able to CREATE sales (POST /api/sales)")
        print("✓ Should be able to VIEW clients and products")
        print("✗ Should NOT be able to create products, access dashboard, manage users")
        print("=" * 60)

        # Setup
        if not self.setup_admin_login():
            return False
            
        if not self.setup_vendas_user():
            return False

        # Core permission tests
        client_id = self.test_vendas_can_create_clients()
        self.test_vendas_can_update_clients(client_id)
        self.test_vendas_can_view_clients()
        products = self.test_vendas_can_view_products()
        self.test_vendas_can_create_sales(client_id, products)
        
        # Security restriction tests
        self.test_vendas_security_restrictions()

        return True

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 VENDAS PERMISSIONS TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")

        if self.errors:
            print(f"\n❌ FAILED TESTS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")
        else:
            print("\n🎉 ALL VENDAS PERMISSION TESTS PASSED!")

        print("\n" + "=" * 60)

def main():
    tester = VendasPermissionsTest()
    
    try:
        success = tester.run_tests()
        tester.print_summary()
        
        if tester.tests_run == 0:
            print("⚠️  No tests were run!")
            return 1
        elif tester.tests_passed == tester.tests_run:
            print("🎉 All vendas permission tests passed!")
            return 0
        else:
            print("⚠️  Some vendas permission tests failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())