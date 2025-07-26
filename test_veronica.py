#!/usr/bin/env python3
"""
Focused test for Veronica's sales reporting issue
"""

import requests
import sys
import json
from datetime import datetime, timedelta

class VeronicaTestRunner:
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

    def test_veronica_issue(self):
        """Test the specific Veronica sales reporting issue"""
        print("🎯 TESTING VERONICA SALES REPORTING ISSUE")
        print("=" * 50)
        
        if not self.login_admin():
            return False
        
        # Step 1: Try to login as existing VERONICA user
        print("\n1. Attempting to login as existing VERONICA user...")
        success, login_data = self.make_request('POST', 'login', {
            'username': 'VERONICA',
            'password': '123456'
        })
        
        if success and 'access_token' in login_data:
            veronica_token = login_data['access_token']
            veronica_user_id = login_data['user']['id']
            print(f"✅ VERONICA login successful - User ID: {veronica_user_id}")
        else:
            print(f"❌ VERONICA login failed: {login_data}")
            # Try to create the user
            print("\n   Creating VERONICA user...")
            success, create_data = self.make_request('POST', 'register', {
                'username': 'VERONICA',
                'email': 'veronica@vendas.com',
                'password': '123456',
                'role': 'vendas'
            }, self.admin_token)
            
            if success:
                print("✅ VERONICA user created")
                # Try login again
                success, login_data = self.make_request('POST', 'login', {
                    'username': 'VERONICA',
                    'password': '123456'
                })
                if success:
                    veronica_token = login_data['access_token']
                    veronica_user_id = login_data['user']['id']
                    print(f"✅ VERONICA login successful after creation - User ID: {veronica_user_id}")
                else:
                    print(f"❌ VERONICA login failed after creation: {login_data}")
                    return False
            else:
                print(f"❌ Failed to create VERONICA user: {create_data}")
                return False
        
        # Step 2: Check if VERONICA has any existing sales
        print(f"\n2. Checking existing sales for VERONICA (ID: {veronica_user_id})...")
        success, my_reports = self.make_request('GET', 'sales/my-reports', token=veronica_token)
        
        if success:
            print("✅ Successfully accessed 'Meus Relatórios' endpoint")
            
            if isinstance(my_reports, dict):
                sales_list = my_reports.get('sales', [])
                total_sales = my_reports.get('total_sales', 0)
                total_revenue = my_reports.get('total_revenue', 0)
                
                print(f"   📊 Report Summary:")
                print(f"      - Total Sales: {total_sales}")
                print(f"      - Total Revenue: R${total_revenue:.2f}")
                print(f"      - Sales Count: {len(sales_list)}")
                
                if len(sales_list) > 0:
                    print(f"✅ VERONICA can see {len(sales_list)} sales in 'Meus Relatórios'")
                    
                    # Show details of first sale
                    sample_sale = sales_list[0]
                    print(f"   📝 Sample Sale:")
                    print(f"      - Sale ID: {sample_sale.get('sale_id', 'N/A')}")
                    print(f"      - Client: {sample_sale.get('client_name', 'N/A')}")
                    print(f"      - Product: {sample_sale.get('product_name', 'N/A')}")
                    print(f"      - Value: R${sample_sale.get('total_value', 0):.2f}")
                    print(f"      - Vendedor ID: {sample_sale.get('vendedor_id', 'N/A')}")
                    print(f"      - Date: {sample_sale.get('sale_date', 'N/A')}")
                    
                    # Verify all sales belong to Veronica
                    all_belong_to_veronica = all(
                        sale.get('vendedor_id') == veronica_user_id for sale in sales_list
                    )
                    
                    if all_belong_to_veronica:
                        print("✅ All sales correctly belong to VERONICA")
                    else:
                        print("❌ Some sales don't belong to VERONICA!")
                        for i, sale in enumerate(sales_list):
                            if sale.get('vendedor_id') != veronica_user_id:
                                print(f"   ⚠️  Sale {i+1}: vendedor_id={sale.get('vendedor_id')} (should be {veronica_user_id})")
                    
                else:
                    print("❌ CRITICAL ISSUE: VERONICA sees NO sales in 'Meus Relatórios'")
                    
                    # Debug: Check if there are any sales in the database for Veronica
                    print("\n   🔍 DEBUGGING: Checking database for Veronica's sales...")
                    success, all_sales = self.make_request('GET', 'sales', token=self.admin_token)
                    if success:
                        veronica_sales_in_db = [s for s in all_sales if s.get('vendedor_id') == veronica_user_id]
                        print(f"   📊 Found {len(veronica_sales_in_db)} sales in database with vendedor_id={veronica_user_id}")
                        
                        if veronica_sales_in_db:
                            print("   📝 Sample database sale:")
                            sample_db_sale = veronica_sales_in_db[0]
                            print(f"      - ID: {sample_db_sale.get('id', 'N/A')}")
                            print(f"      - vendedor_id: {sample_db_sale.get('vendedor_id', 'N/A')}")
                            print(f"      - client_id: {sample_db_sale.get('client_id', 'N/A')}")
                            print(f"      - created_at: {sample_db_sale.get('created_at', 'N/A')}")
                            print(f"      - total_value: {sample_db_sale.get('total_value', 'N/A')}")
                            
                            print("\n   🔍 ISSUE IDENTIFIED: Sales exist in database but not returned by my-reports endpoint!")
                        else:
                            print("   ℹ️  No sales found in database for VERONICA - this is expected if no sales were created")
                    else:
                        print(f"   ❌ Failed to check database sales: {all_sales}")
            else:
                print(f"❌ Unexpected response format: {type(my_reports)}")
                print(f"   Response: {my_reports}")
        else:
            print(f"❌ Failed to access 'Meus Relatórios' endpoint: {my_reports}")
        
        # Step 3: Create a test sale as VERONICA to verify the issue
        print(f"\n3. Creating a test sale as VERONICA...")
        
        # First, get or create a client
        success, clients = self.make_request('GET', 'clients', token=veronica_token)
        if success and clients:
            client_id = clients[0]['id']
            print(f"✅ Using existing client: {clients[0]['name']}")
        else:
            # Create a client
            success, client = self.make_request('POST', 'clients', {
                'name': 'Cliente Teste Veronica',
                'email': 'cliente.veronica@test.com',
                'phone': '11999999999',
                'address': 'Endereço Teste',
                'cpf': '12345678909'  # Valid CPF format
            }, veronica_token)
            
            if success:
                client_id = client['id']
                print(f"✅ Created test client: {client['name']}")
            else:
                print(f"❌ Failed to create client: {client}")
                return False
        
        # Get or create a product
        success, products = self.make_request('GET', 'products', token=veronica_token)
        if success and products:
            product_id = products[0]['id']
            print(f"✅ Using existing product: {products[0]['name']}")
        else:
            print("❌ No products available for sale")
            return False
        
        # Create a sale
        success, sale = self.make_request('POST', 'sales', {
            'client_id': client_id,
            'product_id': product_id,
            'quantity': 1,
            'payment_method': 'dinheiro'
        }, veronica_token)
        
        if success:
            print(f"✅ Created test sale:")
            print(f"   - Sale ID: {sale.get('id', 'N/A')}")
            print(f"   - vendedor_id: {sale.get('vendedor_id', 'N/A')}")
            print(f"   - Expected vendedor_id: {veronica_user_id}")
            print(f"   - Match: {sale.get('vendedor_id') == veronica_user_id}")
            
            # Step 4: Check if the new sale appears in "Meus Relatórios"
            print(f"\n4. Checking if new sale appears in 'Meus Relatórios'...")
            success, updated_reports = self.make_request('GET', 'sales/my-reports', token=veronica_token)
            
            if success:
                updated_sales_list = updated_reports.get('sales', [])
                updated_total_sales = updated_reports.get('total_sales', 0)
                updated_total_revenue = updated_reports.get('total_revenue', 0)
                
                print(f"   📊 Updated Report Summary:")
                print(f"      - Total Sales: {updated_total_sales}")
                print(f"      - Total Revenue: R${updated_total_revenue:.2f}")
                print(f"      - Sales Count: {len(updated_sales_list)}")
                
                if len(updated_sales_list) > 0:
                    print(f"✅ VERONICA now sees {len(updated_sales_list)} sales")
                    
                    # Check if our new sale is there
                    new_sale_found = any(s.get('sale_id') == sale.get('id') for s in updated_sales_list)
                    if new_sale_found:
                        print("✅ New sale appears in 'Meus Relatórios'")
                    else:
                        print("❌ New sale does NOT appear in 'Meus Relatórios'")
                        print("   🔍 This indicates a problem with the my-reports endpoint filtering")
                else:
                    print("❌ CRITICAL: Even after creating a sale, VERONICA sees NO sales in 'Meus Relatórios'")
                    print("   🔍 This confirms there's an issue with the my-reports endpoint")
            else:
                print(f"❌ Failed to check updated reports: {updated_reports}")
        else:
            print(f"❌ Failed to create test sale: {sale}")
        
        print("\n" + "=" * 50)
        print("🎯 VERONICA INVESTIGATION COMPLETED")
        return True

if __name__ == "__main__":
    tester = VeronicaTestRunner()
    tester.test_veronica_issue()