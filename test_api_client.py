"""
Quick test client for Manual Trading API.

This script tests all available endpoints and shows which ones work.

Usage:
    python test_api_client.py
"""

import requests
import json
import sys


class APITestClient:
    def __init__(self, base_url="http://localhost:8080", username="admin", password="admin"):
        self.base_url = base_url
        self.token = None
        self.username = username
        self.password = password
        self.tests_passed = 0
        self.tests_failed = 0

    def print_section(self, title):
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60)

    def print_test(self, name, success, details=None):
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"     {details}")
        if success:
            self.tests_passed += 1
        else:
            self.tests_failed += 1

    def login(self):
        """Authenticate and get JWT token."""
        self.print_section("Authentication Tests")
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={"username": self.username, "password": self.password},
                timeout=5
            )
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                self.print_test("Login", True, f"Token: {self.token[:20]}...")
                return True
            else:
                self.print_test("Login", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.print_test("Login", False, f"Error: {str(e)}")
            return False

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def _get(self, endpoint, test_name):
        try:
            response = requests.get(f"{self.base_url}{endpoint}", headers=self._headers(), timeout=5)
            data = response.json()

            if response.status_code == 200:
                if "error" in data:
                    # Service not available (expected in standalone mode)
                    self.print_test(test_name, False, f"Service not available: {data.get('reason', 'unknown')}")
                else:
                    self.print_test(test_name, True, "Data received")
                    print(f"     Preview: {json.dumps(data, indent=2)[:200]}...")
            else:
                self.print_test(test_name, False, f"HTTP {response.status_code}")

        except Exception as e:
            self.print_test(test_name, False, f"Error: {str(e)}")

    def _post(self, endpoint, test_name, data=None):
        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                headers=self._headers(),
                json=data,
                timeout=5
            )
            resp_data = response.json()

            if response.status_code == 200:
                self.print_test(test_name, True, resp_data.get("message", "Success"))
            else:
                self.print_test(test_name, False, f"HTTP {response.status_code}")

        except Exception as e:
            self.print_test(test_name, False, f"Error: {str(e)}")

    def test_system_endpoints(self):
        """Test system monitoring endpoints (always available)."""
        self.print_section("System Monitoring Tests")
        self._get("/system/status", "System Status")
        self._get("/system/metrics", "System Metrics")

    def test_manual_trading(self):
        """Test manual trading endpoints (always available)."""
        self.print_section("Manual Trading Tests")
        self._post("/signals/entry", "Entry Signal", {
            "symbol": "XAUUSD",
            "direction": "long",
            "entry_price": 2650.25
        })
        self._post("/signals/exit", "Exit Signal", {
            "symbol": "XAUUSD",
            "direction": "long",
            "reason": "test"
        })

    def test_automation(self):
        """Test automation control endpoints (always available)."""
        self.print_section("Automation Control Tests")
        self._post("/automation/disable", "Disable Automation")
        self._post("/automation/enable", "Enable Automation")
        self._get("/automation/status", "Automation Status")

    def test_account_endpoints(self):
        """Test account monitoring (requires MT5Client)."""
        self.print_section("Account Monitoring Tests (requires MT5Client)")
        self._get("/account/summary", "Account Summary")
        self._get("/account/balance", "Account Balance")
        self._get("/account/equity", "Account Equity")
        self._get("/account/margin", "Margin Info")

    def test_position_endpoints(self):
        """Test position management (requires MT5Client)."""
        self.print_section("Position Management Tests (requires MT5Client)")
        self._get("/positions", "List All Positions")
        self._get("/positions/XAUUSD", "Positions by Symbol")

    def test_indicator_endpoints(self):
        """Test indicator monitoring (requires Orchestrator)."""
        self.print_section("Indicator Monitoring Tests (requires Orchestrator)")
        self._get("/indicators/XAUUSD", "All Indicators")
        self._get("/indicators/XAUUSD/H1", "H1 Indicators")
        self._get("/indicators/XAUUSD/H1/rsi_14", "Specific Indicator")

    def test_strategy_endpoints(self):
        """Test strategy monitoring (requires Orchestrator)."""
        self.print_section("Strategy Monitoring Tests (requires Orchestrator)")
        self._get("/strategies/XAUUSD", "List Strategies")
        self._get("/strategies/XAUUSD/metrics", "Strategy Metrics")

    def run_all_tests(self):
        """Run complete test suite."""
        print("\n" + "=" * 60)
        print("  Manual Trading API - Test Suite")
        print("=" * 60)
        print(f"Testing API at: {self.base_url}")
        print(f"Username: {self.username}")
        print("")

        # Authenticate first
        if not self.login():
            print("\n❌ Authentication failed. Cannot continue tests.")
            return False

        # Run all test suites
        self.test_system_endpoints()
        self.test_manual_trading()
        self.test_automation()
        self.test_account_endpoints()
        self.test_position_endpoints()
        self.test_indicator_endpoints()
        self.test_strategy_endpoints()

        # Print summary
        self.print_section("Test Summary")
        total = self.tests_passed + self.tests_failed
        print(f"Total Tests: {total}")
        print(f"✓ Passed: {self.tests_passed}")
        print(f"✗ Failed: {self.tests_failed}")

        if self.tests_failed == 0:
            print("\n🎉 All tests passed!")
        elif self.tests_passed >= 7:  # Auth + System + Manual Trading + Automation
            print("\n✅ Core functionality working!")
            print("   Failed tests likely require MT5Client/Orchestrator integration.")
        else:
            print("\n⚠️  Some core tests failed. Check API server status.")

        print("")
        return self.tests_failed == 0


def main():
    """Main entry point."""
    # Check if server is specified
    api_url = "http://localhost:8080"
    username = "admin"
    password = "admin"  # Change this to match your configuration

    if len(sys.argv) > 1:
        api_url = sys.argv[1]
    if len(sys.argv) > 2:
        username = sys.argv[2]
    if len(sys.argv) > 3:
        password = sys.argv[3]

    # Run tests
    client = APITestClient(api_url, username, password)
    success = client.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
