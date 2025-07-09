import requests
import json
import time
import unittest
from datetime import datetime

# Get the backend URL from the frontend .env file
with open('/app/frontend/.env', 'r') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            BACKEND_URL = line.strip().split('=')[1].strip('"\'')
            break

# Add /api to the backend URL
API_URL = f"{BACKEND_URL}/api"
print(f"Testing API at: {API_URL}")

# Admin token for authentication
ADMIN_TOKEN = "EUROADMIN252024@"

class LotteryAPITest(unittest.TestCase):
    """Test suite for the AI Lottery Prediction System API"""
    
    def setUp(self):
        """Setup for each test"""
        self.admin_headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        self.user_token = None
        self.user_headers = None
        self.test_user_email = f"test_user_{int(time.time())}@example.com"
        self.test_user_name = "Test User"
    
    def test_01_health_check(self):
        """Test the health check endpoint"""
        print("\n=== Testing Health Check Endpoint ===")
        response = requests.get(f"{API_URL}/health")
        print(f"Response: {response.status_code} - {response.text}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("timestamp", data)
        print("✅ Health check endpoint is working")
    
    def test_02_admin_authentication(self):
        """Test admin authentication"""
        print("\n=== Testing Admin Authentication ===")
        # Test with valid admin token
        response = requests.get(
            f"{API_URL}/admin/users",
            headers=self.admin_headers
        )
        print(f"Response with valid token: {response.status_code}")
        self.assertEqual(response.status_code, 200)
        
        # Test with invalid admin token
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        response = requests.get(
            f"{API_URL}/admin/users",
            headers=invalid_headers
        )
        print(f"Response with invalid token: {response.status_code}")
        self.assertEqual(response.status_code, 401)
        
        print("✅ Admin authentication is working")
    
    def test_03_create_user(self):
        """Test user creation via admin endpoint"""
        print("\n=== Testing User Creation ===")
        payload = {
            "action": "create_user",
            "user_data": {
                "email": self.test_user_email,
                "name": self.test_user_name
            }
        }
        
        response = requests.post(
            f"{API_URL}/admin/manage-users",
            headers=self.admin_headers,
            json=payload
        )
        print(f"Response: {response.status_code}")
        print(f"Response body: {response.text[:200]}...")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "User created successfully")
        self.assertEqual(data["user"]["email"], self.test_user_email)
        self.assertEqual(data["user"]["name"], self.test_user_name)
        self.assertTrue(data["user"]["is_active"])
        
        # Save the user token for subsequent tests
        self.user_token = data["user"]["access_token"]
        self.user_headers = {"Authorization": f"Bearer {self.user_token}"}
        
        print(f"✅ User created successfully with token: {self.user_token[:10]}...")
    
    def test_04_get_users(self):
        """Test getting all users as admin"""
        print("\n=== Testing Get All Users ===")
        response = requests.get(
            f"{API_URL}/admin/users",
            headers=self.admin_headers
        )
        print(f"Response: {response.status_code}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("users", data)
        self.assertIsInstance(data["users"], list)
        
        # Check if our test user is in the list
        found = False
        for user in data["users"]:
            if user["email"] == self.test_user_email:
                found = True
                break
        
        self.assertTrue(found, "Test user not found in users list")
        print("✅ Get all users endpoint is working")
    
    def test_05_get_lottery_configs(self):
        """Test getting lottery configurations"""
        print("\n=== Testing Lottery Configurations ===")
        response = requests.get(f"{API_URL}/lottery-configs")
        print(f"Response: {response.status_code}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("lotteries", data)
        
        # Check if all three lottery types are present
        lotteries = data["lotteries"]
        self.assertIn("euromillones", lotteries)
        self.assertIn("la_primitiva", lotteries)
        self.assertIn("el_gordo", lotteries)
        
        print("✅ Lottery configurations endpoint is working")
    
    def test_06_predict_euromillones(self):
        """Test prediction for EuroMillones lottery"""
        if not self.user_token:
            self.skipTest("User token not available")
        
        print("\n=== Testing EuroMillones Prediction ===")
        payload = {
            "lottery_type": "euromillones",
            "language": "pt"
        }
        
        response = requests.post(
            f"{API_URL}/predict",
            headers=self.user_headers,
            json=payload
        )
        print(f"Response: {response.status_code}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Validate response structure
        self.assertEqual(data["lottery_type"], "euromillones")
        self.assertIn("numbers", data)
        self.assertIn("main_numbers", data["numbers"])
        self.assertIn("lucky_numbers", data["numbers"])
        self.assertIn("prediction_confidence", data)
        self.assertIn("ai_analysis", data)
        self.assertIn("prediction_date", data)
        
        # Validate number counts
        self.assertEqual(len(data["numbers"]["main_numbers"]), 5)
        self.assertEqual(len(data["numbers"]["lucky_numbers"]), 2)
        
        print("✅ EuroMillones prediction is working")
    
    def test_07_predict_la_primitiva(self):
        """Test prediction for La Primitiva lottery"""
        if not self.user_token:
            self.skipTest("User token not available")
        
        print("\n=== Testing La Primitiva Prediction ===")
        payload = {
            "lottery_type": "la_primitiva",
            "language": "es"
        }
        
        response = requests.post(
            f"{API_URL}/predict",
            headers=self.user_headers,
            json=payload
        )
        print(f"Response: {response.status_code}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Validate response structure
        self.assertEqual(data["lottery_type"], "la_primitiva")
        self.assertIn("numbers", data)
        self.assertIn("main_numbers", data["numbers"])
        self.assertIn("complementary", data["numbers"])
        self.assertIn("prediction_confidence", data)
        self.assertIn("ai_analysis", data)
        self.assertIn("prediction_date", data)
        
        # Validate number counts
        self.assertEqual(len(data["numbers"]["main_numbers"]), 6)
        self.assertEqual(len(data["numbers"]["complementary"]), 1)
        
        print("✅ La Primitiva prediction is working")
    
    def test_08_predict_el_gordo(self):
        """Test prediction for El Gordo lottery"""
        if not self.user_token:
            self.skipTest("User token not available")
        
        print("\n=== Testing El Gordo Prediction ===")
        payload = {
            "lottery_type": "el_gordo",
            "language": "es"
        }
        
        response = requests.post(
            f"{API_URL}/predict",
            headers=self.user_headers,
            json=payload
        )
        print(f"Response: {response.status_code}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Validate response structure
        self.assertEqual(data["lottery_type"], "el_gordo")
        self.assertIn("numbers", data)
        self.assertIn("main_numbers", data["numbers"])
        self.assertIn("key_number", data["numbers"])
        self.assertIn("prediction_confidence", data)
        self.assertIn("ai_analysis", data)
        self.assertIn("prediction_date", data)
        
        # Validate number counts
        self.assertEqual(len(data["numbers"]["main_numbers"]), 5)
        self.assertEqual(len(data["numbers"]["key_number"]), 1)
        
        print("✅ El Gordo prediction is working")
    
    def test_09_get_user_predictions(self):
        """Test getting user prediction history"""
        if not self.user_token:
            self.skipTest("User token not available")
        
        print("\n=== Testing User Prediction History ===")
        # Wait a moment for predictions to be saved
        time.sleep(1)
        
        response = requests.get(
            f"{API_URL}/user/predictions",
            headers=self.user_headers
        )
        print(f"Response: {response.status_code}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("predictions", data)
        self.assertIsInstance(data["predictions"], list)
        
        # We should have at least 3 predictions from previous tests
        self.assertGreaterEqual(len(data["predictions"]), 3)
        
        print("✅ User prediction history is working")
    
    def test_10_revoke_user_access(self):
        """Test revoking user access"""
        print("\n=== Testing Revoke User Access ===")
        payload = {
            "action": "revoke_access",
            "user_data": {
                "email": self.test_user_email
            }
        }
        
        response = requests.post(
            f"{API_URL}/admin/manage-users",
            headers=self.admin_headers,
            json=payload
        )
        print(f"Response: {response.status_code}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Access revoked successfully")
        
        # Try to use the revoked token
        response = requests.get(
            f"{API_URL}/user/predictions",
            headers=self.user_headers
        )
        print(f"Response with revoked token: {response.status_code}")
        self.assertEqual(response.status_code, 401)
        
        print("✅ User access revocation is working")
    
    def test_11_reactivate_user(self):
        """Test reactivating a user"""
        print("\n=== Testing Reactivate User ===")
        payload = {
            "action": "activate_user",
            "user_data": {
                "email": self.test_user_email
            }
        }
        
        response = requests.post(
            f"{API_URL}/admin/manage-users",
            headers=self.admin_headers,
            json=payload
        )
        print(f"Response: {response.status_code}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "User activated successfully")
        
        # Try to use the token again
        response = requests.get(
            f"{API_URL}/user/predictions",
            headers=self.user_headers
        )
        print(f"Response with reactivated token: {response.status_code}")
        self.assertEqual(response.status_code, 200)
        
        print("✅ User reactivation is working")
    
    def test_12_invalid_lottery_type(self):
        """Test prediction with invalid lottery type"""
        if not self.user_token:
            self.skipTest("User token not available")
        
        print("\n=== Testing Invalid Lottery Type ===")
        payload = {
            "lottery_type": "invalid_lottery",
            "language": "pt"
        }
        
        response = requests.post(
            f"{API_URL}/predict",
            headers=self.user_headers,
            json=payload
        )
        print(f"Response: {response.status_code}")
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("detail", data)
        self.assertEqual(data["detail"], "Invalid lottery type")
        
        print("✅ Invalid lottery type handling is working")

if __name__ == "__main__":
    # Run the tests in order
    unittest.main(argv=['first-arg-is-ignored'], exit=False)