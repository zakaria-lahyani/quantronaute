#!/usr/bin/env python3
"""
Test all API endpoints.

This script tests all endpoints of the Quantronaute Trading API.
"""

import httpx
import json
from typing import Optional

# Configuration
API_BASE_URL = "http://localhost:8080"
USERNAME = "admin"
PASSWORD = "admin123"

class APITester:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def print_response(self, response: httpx.Response, title: str):
        """Print formatted response."""
        print(f"\n{'='*70}")
        print(f"{title}")
        print(f"{'='*70}")
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception:
            print(f"Response: {response.text}")

    def test_health(self):
        """Test health endpoint."""
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/health")
            self.print_response(response, "Health Check")
            return response.status_code == 200

    def test_root(self):
        """Test root endpoint."""
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/")
            self.print_response(response, "Root Endpoint")
            return response.status_code == 200

    def test_login(self):
        """Test login endpoint."""
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/auth/login",
                json={"username": self.username, "password": self.password}
            )
            self.print_response(response, "Login")

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                print(f"\n[+] Access Token saved")
                print(f"[+] Refresh Token saved")
                return True
            return False

    def test_validate_token(self):
        """Test token validation endpoint."""
        if not self.access_token:
            print("\n[-] No access token available. Run login first.")
            return False

        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/auth/me",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            self.print_response(response, "Validate Token")
            return response.status_code == 200

    def test_system_status(self):
        """Test system status endpoint."""
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/system/status")
            self.print_response(response, "System Status")
            return response.status_code == 200

    def test_system_metrics(self):
        """Test system metrics endpoint."""
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/system/metrics")
            self.print_response(response, "System Metrics")
            return response.status_code == 200

    def test_automation_status(self):
        """Test automation status endpoint."""
        if not self.access_token:
            print("\n[-] No access token available. Run login first.")
            return False

        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/automation/status",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            self.print_response(response, "Automation Status")
            return response.status_code == 200

    def test_positions(self):
        """Test positions endpoint."""
        if not self.access_token:
            print("\n[-] No access token available. Run login first.")
            return False

        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/positions",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            self.print_response(response, "Get Positions")
            return response.status_code in [200, 404]  # 404 is ok if no positions

    def test_account(self):
        """Test account endpoint."""
        if not self.access_token:
            print("\n[-] No access token available. Run login first.")
            return False

        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/account",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            self.print_response(response, "Get Account Info")
            return response.status_code in [200, 503]  # 503 if trading system not connected

    def run_all_tests(self):
        """Run all tests."""
        print(f"\n{'#'*70}")
        print("#  QUANTRONAUTE API TESTING")
        print(f"{'#'*70}")
        print(f"\nAPI Base URL: {self.base_url}")
        print(f"Username: {self.username}")
        print()

        results = []

        # Public endpoints (no auth)
        print("\n" + "="*70)
        print("TESTING PUBLIC ENDPOINTS")
        print("="*70)

        results.append(("Health Check", self.test_health()))
        results.append(("Root Endpoint", self.test_root()))
        results.append(("System Status", self.test_system_status()))
        results.append(("System Metrics", self.test_system_metrics()))

        # Authentication
        print("\n" + "="*70)
        print("TESTING AUTHENTICATION")
        print("="*70)

        results.append(("Login", self.test_login()))
        results.append(("Validate Token", self.test_validate_token()))

        # Protected endpoints
        print("\n" + "="*70)
        print("TESTING PROTECTED ENDPOINTS")
        print("="*70)

        results.append(("Automation Status", self.test_automation_status()))
        results.append(("Get Positions", self.test_positions()))
        results.append(("Get Account", self.test_account()))

        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for name, result in results:
            status = "[PASS]" if result else "[FAIL]"
            print(f"{status} {name}")

        print()
        print(f"Results: {passed}/{total} tests passed")
        print("="*70)

        if passed == total:
            print("\n[+] All tests passed!")
            return 0
        else:
            print(f"\n[-] {total - passed} test(s) failed")
            return 1


def main():
    """Main function."""
    tester = APITester(API_BASE_URL, USERNAME, PASSWORD)
    return tester.run_all_tests()


if __name__ == "__main__":
    import sys
    sys.exit(main())
