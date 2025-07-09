import json
import time
import unittest
from datetime import datetime
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Add the backend directory to the path
sys.path.append('/app/backend')

# Import the FastAPI app
try:
    from server import app
    print("Successfully imported the FastAPI app")
except ImportError as e:
    print(f"Error importing the FastAPI app: {e}")
    sys.exit(1)

# Create a test client
client = TestClient(app)

# Admin token for authentication
ADMIN_TOKEN = "EUROADMIN252024@"

# Mock MongoDB client
class MockCollection:
    def __init__(self):
        self.data = []
        
    async def find_one(self, query):
        for item in self.data:
            match = True
            for key, value in query.items():
                if key not in item or item[key] != value:
                    match = False
                    break
            if match:
                return item
        return None
    
    async def insert_one(self, document):
        self.data.append(document)
        return MagicMock()
    
    async def update_one(self, query, update):
        for i, item in enumerate(self.data):
            match = True
            for key, value in query.items():
                if key not in item or item[key] != value:
                    match = False
                    break
            if match:
                for set_key, set_value in update["$set"].items():
                    self.data[i][set_key] = set_value
                return MagicMock(matched_count=1)
        return MagicMock(matched_count=0)
    
    def find(self, query=None):
        return MockCursor(self.data)

class MockCursor:
    def __init__(self, data):
        self.data = data
        
    def sort(self, *args, **kwargs):
        return self
    
    def limit(self, *args, **kwargs):
        return self
    
    async def __aiter__(self):
        for item in self.data:
            yield item

class MockDB:
    def __init__(self):
        self.users = MockCollection()
        self.lottery_predictions = MockCollection()
        self.lottery_history = MockCollection()

# Create mock database
mock_db = MockDB()

class LotteryAPITest(unittest.TestCase):
    """Test suite for the AI Lottery Prediction System API"""
    
    def setUp(self):
        """Setup for each test"""
        self.admin_headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        self.user_token = None
        self.user_headers = None
        self.test_user_email = f"test_user_{int(time.time())}@example.com"
        self.test_user_name = "Test User"
        
        # Apply the patch for the database
        self.db_patcher = patch('server.db', mock_db)
        self.db_patcher.start()
    
    def tearDown(self):
        """Teardown after each test"""
        self.db_patcher.stop()
    
    def test_01_health_check(self):
        """Test the health check endpoint"""
        print("\n=== Testing Health Check Endpoint ===")
        response = client.get("/api/health")
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
        response = client.get(
            "/api/admin/users",
            headers=self.admin_headers
        )
        print(f"Response with valid token: {response.status_code}")
        self.assertEqual(response.status_code, 200)
        
        # Test with invalid admin token
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        response = client.get(
            "/api/admin/users",
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
        
        response = client.post(
            "/api/admin/manage-users",
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
        response = client.get(
            "/api/admin/users",
            headers=self.admin_headers
        )
        print(f"Response: {response.status_code}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("users", data)
        self.assertIsInstance(data["users"], list)
        
        print("✅ Get all users endpoint is working")
    
    def test_05_get_lottery_configs(self):
        """Test getting lottery configurations"""
        print("\n=== Testing Lottery Configurations ===")
        response = client.get("/api/lottery-configs")
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
        
        # Add a mock user to the database
        mock_db.users.data.append({
            "id": "test_user_id",
            "email": self.test_user_email,
            "name": self.test_user_name,
            "access_token": self.user_token,
            "created_at": datetime.utcnow(),
            "is_active": True
        })
        
        response = client.post(
            "/api/predict",
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
        
        response = client.post(
            "/api/predict",
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
        
        response = client.post(
            "/api/predict",
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
        
        # Add some mock predictions to the database
        for i in range(3):
            mock_db.lottery_predictions.data.append({
                "id": f"pred_{i}",
                "user_id": "test_user_id",
                "lottery_type": "euromillones",
                "numbers": {
                    "main_numbers": [1, 2, 3, 4, 5],
                    "lucky_numbers": [6, 7]
                },
                "prediction_confidence": 0.8,
                "ai_analysis": "Test analysis",
                "prediction_date": datetime.utcnow()
            })
        
        response = client.get(
            "/api/user/predictions",
            headers=self.user_headers
        )
        print(f"Response: {response.status_code}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("predictions", data)
        self.assertIsInstance(data["predictions"], list)
        
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
        
        response = client.post(
            "/api/admin/manage-users",
            headers=self.admin_headers,
            json=payload
        )
        print(f"Response: {response.status_code}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Access revoked successfully")
        
        # Update the mock user in the database
        for user in mock_db.users.data:
            if user["email"] == self.test_user_email:
                user["is_active"] = False
        
        # Try to use the revoked token
        response = client.get(
            "/api/user/predictions",
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
        
        response = client.post(
            "/api/admin/manage-users",
            headers=self.admin_headers,
            json=payload
        )
        print(f"Response: {response.status_code}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "User activated successfully")
        
        # Update the mock user in the database
        for user in mock_db.users.data:
            if user["email"] == self.test_user_email:
                user["is_active"] = True
        
        # Try to use the token again
        response = client.get(
            "/api/user/predictions",
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
        
        response = client.post(
            "/api/predict",
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