#!/usr/bin/env python3
"""
Backend API Testing for Sistema de Caixa - New Features Focus
Tests the new functionalities: Products in Billing, Client Payments, Smart Installments, etc.
"""

import requests
import sys
import json
from datetime import datetime, timedelta
import time

class CashSystemTester:
    def __init__(self, base_url="https://496eea55-995e-4134-a00e-558ced9e7934.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_resources = {
            'products': [],
            'clients': [],
            'bills': [],
            'transactions': []
        }

    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    self.log(f"   Error: {error_detail}")
                except:
                    self.log(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}")
            return False, {}

    def test_login(self):
        """Test admin login"""
        self.log("🔐 Testing Admin Login...")
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "login",
            200,
            data={"username": "ADMIN", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.log(f"✅ Login successful, token obtained")
            return True
        return False

    def test_create_product(self):
        """Test creating a product with unique code"""
        self.log("📦 Testing Product Creation...")
        
        product_data = {
            "code": f"PLANO_INTERNET_{int(time.time())}",
            "name": "PLANO DE INTERNET",
            "price": 100.00,
            "description": "PLANO MENSAL DE INTERNET"
        }
        
        success, response = self.run_test(
            "Create Product",
            "POST",
            "products",
            200,
            data=product_data
        )
        
        if success and 'id' in response:
            self.created_resources['products'].append(response['id'])
            self.log(f"✅ Product created with ID: {response['id']}")
            return response['id']
        return None

    def test_create_client(self):
        """Test creating a client with valid CPF"""
        self.log("👤 Testing Client Creation...")
        
        timestamp = int(time.time())
        client_data = {
            "name": f"JOÃO DA SILVA {timestamp}",
            "email": f"JOAO{timestamp}@EMAIL.COM",
            "phone": "11999999999",
            "address": "RUA DAS FLORES, 123",
            "cpf": "52998224725"  # Different valid CPF
        }
        
        success, response = self.run_test(
            "Create Client",
            "POST",
            "clients",
            200,
            data=client_data
        )
        
        if success and 'id' in response:
            self.created_resources['clients'].append(response['id'])
            self.log(f"✅ Client created with ID: {response['id']}")
            return response['id']
        return None

    def test_create_bill_with_product(self, client_id, product_id):
        """Test creating a bill using a product (should use product price automatically)"""
        self.log("📄 Testing Bill Creation with Product...")
        
        bill_data = {
            "client_id": client_id,
            "product_id": product_id,
            "description": "COBRANÇA PLANO INTERNET",
            "installments": 12
        }
        
        success, response = self.run_test(
            "Create Bill with Product",
            "POST",
            "bills",
            200,
            data=bill_data
        )
        
        if success and 'id' in response:
            self.created_resources['bills'].append(response['id'])
            self.log(f"✅ Bill created with ID: {response['id']}")
            self.log(f"   Total Amount: R$ {response.get('total_amount', 0):.2f}")
            self.log(f"   Installments: {response.get('installments', 0)}")
            return response['id']
        return None

    def test_get_bill_installments(self, bill_id):
        """Test getting bill installments"""
        self.log("📋 Testing Bill Installments Retrieval...")
        
        success, response = self.run_test(
            "Get Bill Installments",
            "GET",
            f"bills/{bill_id}/installments",
            200
        )
        
        if success and isinstance(response, list):
            self.log(f"✅ Found {len(response)} installments")
            for i, installment in enumerate(response[:3]):  # Show first 3
                self.log(f"   Installment {installment.get('installment_number')}: R$ {installment.get('amount', 0):.2f} - Due: {installment.get('due_date', 'N/A')[:10]}")
            return response
        return []

    def test_clients_with_bills(self):
        """Test getting clients with pending bills"""
        self.log("👥 Testing Clients with Bills...")
        
        success, response = self.run_test(
            "Get Clients with Bills",
            "GET",
            "clients/with-bills",
            200
        )
        
        if success and isinstance(response, list):
            self.log(f"✅ Found {len(response)} clients with pending bills")
            for client in response:
                self.log(f"   Client: {client.get('client_name')} - {client.get('total_pending')} pending")
            return response
        return []

    def test_client_pending_bills(self, client_id):
        """Test getting client's pending bills by product"""
        self.log("📊 Testing Client Pending Bills...")
        
        success, response = self.run_test(
            "Get Client Pending Bills",
            "GET",
            f"clients/{client_id}/pending-bills",
            200
        )
        
        if success and 'products_with_bills' in response:
            products = response['products_with_bills']
            self.log(f"✅ Found {len(products)} products with pending bills")
            for product in products:
                self.log(f"   Product: {product.get('product_name')} - {len(product.get('pending_installments', []))} pending")
                if product.get('oldest_overdue'):
                    overdue = product['oldest_overdue']
                    self.log(f"     ⚠️ Oldest overdue: Installment {overdue.get('installment_number')} - R$ {overdue.get('amount', 0):.2f}")
            return response
        return {}

    def test_client_payment(self, client_id, product_id):
        """Test processing client payment (should pay oldest installment)"""
        self.log("💰 Testing Client Payment Processing...")
        
        payment_data = {
            "client_id": client_id,
            "product_id": product_id,
            "payment_method": "dinheiro"
        }
        
        success, response = self.run_test(
            "Process Client Payment",
            "POST",
            "transactions/client-payment",
            200,
            data=payment_data
        )
        
        if success and 'transaction' in response:
            transaction = response['transaction']
            self.created_resources['transactions'].append(transaction['id'])
            self.log(f"✅ Payment processed successfully")
            self.log(f"   Installment paid: {response.get('installment_paid')}")
            self.log(f"   Amount: R$ {response.get('amount', 0):.2f}")
            self.log(f"   Transaction ID: {transaction['id']}")
            return transaction['id']
        return None

    def test_transaction_history_with_filters(self):
        """Test transaction history with different filters"""
        self.log("📈 Testing Transaction History with Filters...")
        
        # Test filter by transaction type "pagamento_cliente"
        success, response = self.run_test(
            "Get Transactions - Payment Client Filter",
            "GET",
            "transactions?transaction_type=pagamento_cliente",
            200
        )
        
        if success and isinstance(response, list):
            client_payments = [t for t in response if t.get('type') == 'pagamento_cliente']
            self.log(f"✅ Found {len(client_payments)} client payment transactions")
            for payment in client_payments[:3]:  # Show first 3
                self.log(f"   Client: {payment.get('client_name')} - R$ {payment.get('amount', 0):.2f}")
            return True
        return False

    def test_transaction_cancellation(self, transaction_id):
        """Test cancelling a client payment transaction"""
        self.log("❌ Testing Transaction Cancellation...")
        
        success, response = self.run_test(
            "Cancel Transaction",
            "DELETE",
            f"transactions/{transaction_id}",
            200
        )
        
        if success:
            self.log(f"✅ Transaction {transaction_id} cancelled successfully")
            return True
        return False

    def test_installment_status_after_cancellation(self, client_id, product_id):
        """Test that installment status reverts to pending after cancellation"""
        self.log("🔄 Testing Installment Status After Cancellation...")
        
        success, response = self.run_test(
            "Check Installment Status",
            "GET",
            f"clients/{client_id}/pending-bills",
            200
        )
        
        if success and 'products_with_bills' in response:
            products = response['products_with_bills']
            for product in products:
                if product.get('product_id') == product_id:
                    pending_count = len(product.get('pending_installments', []))
                    self.log(f"✅ Product now has {pending_count} pending installments")
                    return True
        return False

    def test_dashboard_summary(self):
        """Test dashboard summary includes client payments"""
        self.log("📊 Testing Dashboard Summary...")
        
        success, response = self.run_test(
            "Get Dashboard Summary",
            "GET",
            "transactions/summary",
            200
        )
        
        if success:
            self.log(f"✅ Dashboard Summary:")
            self.log(f"   Total Entrada: R$ {response.get('total_entrada', 0):.2f}")
            self.log(f"   Total Saída: R$ {response.get('total_saida', 0):.2f}")
            self.log(f"   Saldo: R$ {response.get('saldo', 0):.2f}")
            self.log(f"   Total Transactions: {response.get('total_transactions', 0)}")
            return True
        return False

    def run_complete_test_scenario(self):
        """Run the complete test scenario as requested"""
        self.log("🚀 Starting Complete Cash System Test Scenario")
        self.log("=" * 60)
        
        # 1. Login
        if not self.test_login():
            self.log("❌ Login failed, stopping tests")
            return False
        
        # 2. Create product "PLANO_INTERNET" - R$ 100,00
        product_id = self.test_create_product()
        if not product_id:
            self.log("❌ Product creation failed, stopping tests")
            return False
        
        # 3. Create client with valid CPF
        client_id = self.test_create_client()
        if not client_id:
            self.log("❌ Client creation failed, stopping tests")
            return False
        
        # 4. Create bill for client using product (12 installments)
        bill_id = self.test_create_bill_with_product(client_id, product_id)
        if not bill_id:
            self.log("❌ Bill creation failed, stopping tests")
            return False
        
        # 5. Verify installments were created
        installments = self.test_get_bill_installments(bill_id)
        if not installments:
            self.log("❌ Installments retrieval failed, stopping tests")
            return False
        
        # 6. Test clients with bills endpoint
        if not self.test_clients_with_bills():
            self.log("❌ Clients with bills test failed")
        
        # 7. Test client pending bills
        if not self.test_client_pending_bills(client_id):
            self.log("❌ Client pending bills test failed")
        
        # 8. Process payment using "Receber Pagamento de Cliente"
        transaction_id = self.test_client_payment(client_id, product_id)
        if not transaction_id:
            self.log("❌ Client payment failed, stopping tests")
            return False
        
        # 9. Test transaction history with "Pagamento Cliente" filter
        if not self.test_transaction_history_with_filters():
            self.log("❌ Transaction history filter test failed")
        
        # 10. Test dashboard summary
        if not self.test_dashboard_summary():
            self.log("❌ Dashboard summary test failed")
        
        # 11. Cancel transaction and verify installment reverts
        if self.test_transaction_cancellation(transaction_id):
            time.sleep(1)  # Give time for database update
            if not self.test_installment_status_after_cancellation(client_id, product_id):
                self.log("❌ Installment status reversion test failed")
        
        return True

    def print_summary(self):
        """Print test summary"""
        self.log("=" * 60)
        self.log("📊 TEST SUMMARY")
        self.log("=" * 60)
        self.log(f"Tests Run: {self.tests_run}")
        self.log(f"Tests Passed: {self.tests_passed}")
        self.log(f"Tests Failed: {self.tests_run - self.tests_passed}")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.tests_passed == self.tests_run:
            self.log("🎉 ALL TESTS PASSED!")
        else:
            self.log("⚠️ Some tests failed")
        
        self.log("=" * 60)

def main():
    tester = CashSystemTester()
    
    try:
        success = tester.run_complete_test_scenario()
        tester.print_summary()
        return 0 if success and tester.tests_passed == tester.tests_run else 1
    except KeyboardInterrupt:
        tester.log("❌ Tests interrupted by user")
        tester.print_summary()
        return 1
    except Exception as e:
        tester.log(f"❌ Unexpected error: {str(e)}")
        tester.print_summary()
        return 1

if __name__ == "__main__":
    sys.exit(main())