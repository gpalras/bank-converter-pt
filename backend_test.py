import requests
import sys
import json
from datetime import datetime
import time

class BankConverterAPITester:
    def __init__(self, base_url="https://finance-converter-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if not success:
                try:
                    error_data = response.json()
                    details += f", Response: {error_data}"
                except:
                    details += f", Response: {response.text[:200]}"
            
            self.log_test(name, success, details)
            
            if success:
                try:
                    return response.json()
                except:
                    return response.text
            return None

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return None

    def test_user_registration(self):
        """Test user registration"""
        timestamp = int(time.time())
        user_data = {
            "name": f"Test User {timestamp}",
            "email": f"test{timestamp}@example.com",
            "password": "TestPassword123!"
        }
        
        response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=user_data
        )
        
        if response and 'token' in response:
            self.token = response['token']
            self.user_data = response['user']
            return True
        return False

    def test_user_login(self):
        """Test user login with existing credentials"""
        if not self.user_data:
            return False
            
        login_data = {
            "email": self.user_data['email'],
            "password": "TestPassword123!"
        }
        
        # Clear token to test login
        old_token = self.token
        self.token = None
        
        response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if response and 'token' in response:
            self.token = response['token']
            return True
        else:
            self.token = old_token  # Restore token if login failed
            return False

    def test_get_current_user(self):
        """Test getting current user info"""
        response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        return response is not None

    def test_get_subscription_plans(self):
        """Test getting subscription plans"""
        response = self.run_test(
            "Get Subscription Plans",
            "GET",
            "subscriptions/plans",
            200
        )
        
        if response:
            expected_plans = ['free', 'starter', 'pro']
            has_all_plans = all(plan in response for plan in expected_plans)
            if not has_all_plans:
                self.log_test("Subscription Plans Content", False, f"Missing plans. Got: {list(response.keys())}")
            else:
                self.log_test("Subscription Plans Content", True, "All plans present")
            return has_all_plans
        return False

    def test_get_current_subscription(self):
        """Test getting current user subscription"""
        response = self.run_test(
            "Get Current Subscription",
            "GET",
            "subscriptions/current",
            200
        )
        
        if response:
            required_fields = ['plan_type', 'pages_limit', 'pages_used_this_month']
            has_required_fields = all(field in response for field in required_fields)
            if not has_required_fields:
                self.log_test("Subscription Fields", False, f"Missing fields. Got: {list(response.keys())}")
            else:
                self.log_test("Subscription Fields", True, "All required fields present")
            return has_required_fields
        return False

    def test_create_checkout_session(self):
        """Test creating Stripe checkout session"""
        checkout_data = {
            "plan_type": "starter",
            "origin_url": self.base_url
        }
        
        response = self.run_test(
            "Create Checkout Session",
            "POST",
            "payments/checkout/session",
            200,
            data=checkout_data
        )
        
        if response and 'url' in response and 'session_id' in response:
            self.log_test("Checkout Session Content", True, "URL and session_id present")
            return response['session_id']
        else:
            self.log_test("Checkout Session Content", False, "Missing URL or session_id")
            return None

    def test_get_conversions(self):
        """Test getting user conversions"""
        response = self.run_test(
            "Get Conversions",
            "GET",
            "conversions",
            200
        )
        return response is not None

    def test_invalid_endpoints(self):
        """Test invalid endpoints return proper errors"""
        # Test non-existent endpoint
        self.run_test(
            "Invalid Endpoint",
            "GET",
            "nonexistent",
            404
        )
        
        # Test unauthorized access
        old_token = self.token
        self.token = "invalid_token"
        self.run_test(
            "Invalid Token",
            "GET",
            "auth/me",
            401
        )
        self.token = old_token

    def test_file_upload_without_file(self):
        """Test file upload endpoint without actual file"""
        # This will test the endpoint structure but won't upload a real file
        url = f"{self.api_url}/conversions/upload?bank_name=Millennium"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            # Send request without file to test endpoint availability
            response = requests.post(url, headers=headers, timeout=30)
            # Expect 422 (validation error) since no file is provided
            success = response.status_code == 422
            self.log_test("File Upload Endpoint", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("File Upload Endpoint", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Bank Converter API Tests...")
        print(f"Testing against: {self.base_url}")
        print("=" * 50)

        # Authentication Tests
        if not self.test_user_registration():
            print("❌ Registration failed, stopping tests")
            return False

        self.test_user_login()
        self.test_get_current_user()

        # Subscription Tests
        self.test_get_subscription_plans()
        self.test_get_current_subscription()

        # Payment Tests
        session_id = self.test_create_checkout_session()

        # Conversion Tests
        self.test_get_conversions()
        self.test_file_upload_without_file()

        # Error Handling Tests
        self.test_invalid_endpoints()

        # Print Results
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

    def get_test_summary(self):
        """Get test summary for reporting"""
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": self.tests_run - self.tests_passed,
            "success_rate": (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0,
            "test_results": self.test_results
        }

def main():
    tester = BankConverterAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    summary = tester.get_test_summary()
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())