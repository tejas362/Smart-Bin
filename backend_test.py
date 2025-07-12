#!/usr/bin/env python3
"""
Smart Dustbin IoT Backend API Test Suite
Tests all backend functionality including CRUD operations, IoT simulation, and notifications
"""

import requests
import json
import time
from datetime import datetime
import sys

# Use the production backend URL from frontend/.env
BASE_URL = "https://e5c65fc7-7dcc-48fb-804c-34eedf8d85aa.preview.emergentagent.com/api"

class SmartDustbinTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.test_results = []
        self.created_dustbin_ids = []
        
    def log_test(self, test_name, success, message, response_data=None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        })
        
    def test_health_check(self):
        """Test GET /api/ - Basic health check"""
        try:
            response = self.session.get(f"{self.base_url}/")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "status" in data:
                    self.log_test("Health Check", True, f"API is active. Response: {data}")
                    return True
                else:
                    self.log_test("Health Check", False, f"Invalid response format: {data}")
                    return False
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Health Check", False, f"Connection error: {str(e)}")
            return False
    
    def test_initialize_demo_data(self):
        """Test POST /api/initialize-demo-data - Initialize 12 demo dustbins"""
        try:
            response = self.session.post(f"{self.base_url}/initialize-demo-data")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("bins") == 12:
                    self.log_test("Demo Data Initialization", True, f"Successfully created 12 demo dustbins: {data}")
                    return True
                else:
                    self.log_test("Demo Data Initialization", False, f"Expected 12 bins, got: {data}")
                    return False
            else:
                self.log_test("Demo Data Initialization", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Demo Data Initialization", False, f"Error: {str(e)}")
            return False
    
    def test_get_all_dustbins(self):
        """Test GET /api/dustbins - Fetch all dustbins"""
        try:
            response = self.session.get(f"{self.base_url}/dustbins")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Store dustbin IDs for later tests
                    self.created_dustbin_ids = [bin_data["id"] for bin_data in data]
                    
                    # Verify dustbin structure
                    first_bin = data[0]
                    required_fields = ["id", "name", "location", "fill_level", "battery_level", "status", "last_updated"]
                    
                    missing_fields = [field for field in required_fields if field not in first_bin]
                    if not missing_fields:
                        self.log_test("Get All Dustbins", True, f"Retrieved {len(data)} dustbins with correct structure")
                        return True
                    else:
                        self.log_test("Get All Dustbins", False, f"Missing fields in dustbin data: {missing_fields}")
                        return False
                else:
                    self.log_test("Get All Dustbins", False, f"Expected list of dustbins, got: {type(data)}")
                    return False
            else:
                self.log_test("Get All Dustbins", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Get All Dustbins", False, f"Error: {str(e)}")
            return False
    
    def test_dashboard_stats(self):
        """Test GET /api/dashboard/stats - Get dashboard statistics"""
        try:
            response = self.session.get(f"{self.base_url}/dashboard/stats")
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["total_bins", "full_bins", "offline_bins", "low_battery_bins", "unread_notifications", "avg_fill_level"]
                
                missing_fields = [field for field in required_fields if field not in data]
                if not missing_fields:
                    self.log_test("Dashboard Stats", True, f"Dashboard stats retrieved successfully: {data}")
                    return True
                else:
                    self.log_test("Dashboard Stats", False, f"Missing fields in stats: {missing_fields}")
                    return False
            else:
                self.log_test("Dashboard Stats", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Dashboard Stats", False, f"Error: {str(e)}")
            return False
    
    def test_get_specific_dustbin(self):
        """Test GET /api/dustbins/{id} - Get specific dustbin"""
        if not self.created_dustbin_ids:
            self.log_test("Get Specific Dustbin", False, "No dustbin IDs available for testing")
            return False
            
        try:
            dustbin_id = self.created_dustbin_ids[0]
            response = self.session.get(f"{self.base_url}/dustbins/{dustbin_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("id") == dustbin_id:
                    self.log_test("Get Specific Dustbin", True, f"Retrieved dustbin {dustbin_id} successfully")
                    return True
                else:
                    self.log_test("Get Specific Dustbin", False, f"ID mismatch: expected {dustbin_id}, got {data.get('id')}")
                    return False
            else:
                self.log_test("Get Specific Dustbin", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Get Specific Dustbin", False, f"Error: {str(e)}")
            return False
    
    def test_update_dustbin(self):
        """Test PUT /api/dustbins/{id} - Update dustbin data"""
        if not self.created_dustbin_ids:
            self.log_test("Update Dustbin", False, "No dustbin IDs available for testing")
            return False
            
        try:
            dustbin_id = self.created_dustbin_ids[0]
            
            # Update with high fill level to trigger notification
            update_data = {
                "fill_level": 95.0,
                "battery_level": 15.0  # Low battery to trigger notification
            }
            
            response = self.session.put(f"{self.base_url}/dustbins/{dustbin_id}", json=update_data)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("fill_level") == 95.0 and data.get("battery_level") == 15.0:
                    self.log_test("Update Dustbin", True, f"Dustbin updated successfully with fill_level=95% and battery=15%")
                    return True
                else:
                    self.log_test("Update Dustbin", False, f"Update values not reflected: {data}")
                    return False
            else:
                self.log_test("Update Dustbin", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Update Dustbin", False, f"Error: {str(e)}")
            return False
    
    def test_iot_simulation(self):
        """Test POST /api/simulate/iot-data - Simulate IoT sensor updates"""
        try:
            response = self.session.post(f"{self.base_url}/simulate/iot-data")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "timestamp" in data:
                    self.log_test("IoT Simulation", True, f"IoT simulation completed: {data}")
                    return True
                else:
                    self.log_test("IoT Simulation", False, f"Invalid response format: {data}")
                    return False
            else:
                self.log_test("IoT Simulation", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("IoT Simulation", False, f"Error: {str(e)}")
            return False
    
    def test_notifications(self):
        """Test GET /api/notifications - Fetch notifications"""
        try:
            response = self.session.get(f"{self.base_url}/notifications")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    if len(data) > 0:
                        # Check notification structure
                        first_notification = data[0]
                        required_fields = ["id", "dustbin_id", "dustbin_name", "message", "type", "priority", "timestamp"]
                        
                        missing_fields = [field for field in required_fields if field not in first_notification]
                        if not missing_fields:
                            self.log_test("Get Notifications", True, f"Retrieved {len(data)} notifications with correct structure")
                            return True
                        else:
                            self.log_test("Get Notifications", False, f"Missing fields in notification: {missing_fields}")
                            return False
                    else:
                        self.log_test("Get Notifications", True, "No notifications found (empty list is valid)")
                        return True
                else:
                    self.log_test("Get Notifications", False, f"Expected list, got: {type(data)}")
                    return False
            else:
                self.log_test("Get Notifications", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Get Notifications", False, f"Error: {str(e)}")
            return False
    
    def test_notification_generation(self):
        """Test that notifications are generated for full bins and low battery"""
        try:
            # First, get initial notification count
            initial_response = self.session.get(f"{self.base_url}/notifications")
            initial_count = len(initial_response.json()) if initial_response.status_code == 200 else 0
            
            # Update a dustbin to trigger notifications
            if self.created_dustbin_ids:
                dustbin_id = self.created_dustbin_ids[1] if len(self.created_dustbin_ids) > 1 else self.created_dustbin_ids[0]
                
                update_data = {
                    "fill_level": 92.0,  # Should trigger full bin notification
                    "battery_level": 18.0  # Should trigger low battery notification
                }
                
                update_response = self.session.put(f"{self.base_url}/dustbins/{dustbin_id}", json=update_data)
                
                if update_response.status_code == 200:
                    # Wait a moment for notifications to be created
                    time.sleep(1)
                    
                    # Check if new notifications were created
                    final_response = self.session.get(f"{self.base_url}/notifications")
                    if final_response.status_code == 200:
                        final_count = len(final_response.json())
                        
                        if final_count > initial_count:
                            self.log_test("Notification Generation", True, f"Notifications generated successfully. Count increased from {initial_count} to {final_count}")
                            return True
                        else:
                            self.log_test("Notification Generation", False, f"No new notifications generated. Count remained {final_count}")
                            return False
                    else:
                        self.log_test("Notification Generation", False, "Failed to fetch notifications after update")
                        return False
                else:
                    self.log_test("Notification Generation", False, "Failed to update dustbin for notification test")
                    return False
            else:
                self.log_test("Notification Generation", False, "No dustbin IDs available for testing")
                return False
                
        except Exception as e:
            self.log_test("Notification Generation", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests in sequence"""
        print("🧪 Starting Smart Dustbin IoT Backend API Tests")
        print(f"🔗 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test sequence
        tests = [
            ("Health Check", self.test_health_check),
            ("Initialize Demo Data", self.test_initialize_demo_data),
            ("Get All Dustbins", self.test_get_all_dustbins),
            ("Dashboard Stats", self.test_dashboard_stats),
            ("Get Specific Dustbin", self.test_get_specific_dustbin),
            ("Update Dustbin", self.test_update_dustbin),
            ("IoT Simulation", self.test_iot_simulation),
            ("Get Notifications", self.test_notifications),
            ("Notification Generation", self.test_notification_generation),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            print(f"\n🔍 Running: {test_name}")
            try:
                success = test_func()
                if success:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ FAIL {test_name}: Unexpected error - {str(e)}")
                failed += 1
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        if failed == 0:
            print("\n🎉 All tests passed! Backend API is working correctly.")
        else:
            print(f"\n⚠️  {failed} test(s) failed. Check the details above.")
        
        return passed, failed

def main():
    """Main test execution"""
    tester = SmartDustbinTester()
    passed, failed = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()