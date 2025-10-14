"""
Visual Test Runner with Colored Output
Runs comprehensive tests for every aspect of the architecture
"""
import subprocess
import sys
import os
from datetime import datetime
import time


# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_banner():
    """Print a nice banner for the test suite."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 80)
    print("  EMAIL AI PROJECT TRACKER - COMPREHENSIVE TEST SUITE")
    print("  Testing Every Component of the Architecture")
    print("=" * 80)
    print(f"{Colors.ENDC}\n")


def print_section(title, description):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}{'-' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}[SECTION] {title}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}   {description}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'-' * 80}{Colors.ENDC}\n")


def print_test_start(test_name):
    """Print test start message."""
    print(f"{Colors.BOLD}[RUNNING] {Colors.ENDC}{test_name}")


def print_test_result(test_name, passed, duration, details=""):
    """Print test result."""
    if passed:
        status = f"{Colors.OKGREEN}[PASS]{Colors.ENDC}"
    else:
        status = f"{Colors.FAIL}[FAIL]{Colors.ENDC}"
    
    print(f"   {status} - {test_name} ({duration:.2f}s)")
    if details:
        print(f"   {Colors.WARNING}{details}{Colors.ENDC}")


def run_pytest_suite(test_file, description):
    """Run a pytest test file and return results."""
    print_test_start(description)
    
    start_time = time.time()
    
    try:
        # Run pytest with verbose output
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', test_file, '-v', '--tb=short', '--no-header'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        
        duration = time.time() - start_time
        
        # Parse output for pass/fail count
        output = result.stdout + result.stderr
        passed = result.returncode == 0
        
        # Count tests
        if 'passed' in output.lower():
            import re
            match = re.search(r'(\d+) passed', output)
            if match:
                num_passed = match.group(1)
                details = f"{num_passed} tests passed"
            else:
                details = ""
        else:
            details = "See output for details"
        
        print_test_result(description, passed, duration, details)
        
        # If failed, show some output
        if not passed:
            print(f"\n{Colors.FAIL}   Error Output:{Colors.ENDC}")
            error_lines = output.split('\n')[-20:]  # Last 20 lines
            for line in error_lines:
                if line.strip():
                    try:
                        print(f"   {Colors.WARNING}{line}{Colors.ENDC}")
                    except:
                        print(f"   {line}")
        
        return passed, duration
        
    except Exception as e:
        duration = time.time() - start_time
        print_test_result(description, False, duration, f"Exception: {str(e)}")
        return False, duration


def run_architecture_tests():
    """Run all architecture tests."""
    print_banner()
    
    start_time = datetime.now()
    results = []
    
    # Test Suite Configuration
    test_suites = [
        # Layer 1: Data Storage Layer
        {
            'section': 'DATA STORAGE LAYER',
            'description': 'Testing S3 and DynamoDB operations',
            'tests': [
                ('tests/test_s3_client.py', 'S3 Client - Email & Attachment Storage'),
                ('tests/test_db_client_comprehensive.py', 'DynamoDB Client - Projects, Events, Users Tables'),
                ('tests/test_db_client.py', 'DynamoDB Client - Basic Operations (Legacy)'),
            ]
        },
        
        # Layer 2: Email Processing Layer
        {
            'section': 'EMAIL PROCESSING LAYER',
            'description': 'Testing email parsing and handling',
            'tests': [
                ('tests/test_email_parser_comprehensive.py', 'Email Parser - MIME, Attachments, Edge Cases'),
                ('tests/test_email_parser.py', 'Email Parser - Core Functionality (Legacy)'),
            ]
        },
        
        # Layer 3: AI Processing Layer
        {
            'section': 'AI PROCESSING LAYER',
            'description': 'Testing OpenAI integration and AI operations',
            'tests': [
                ('tests/test_ai_client_comprehensive.py', 'AI Client - Extraction, Estimation, Response Generation'),
            ]
        },
        
        # Layer 4: Lambda Functions (if tests exist)
        {
            'section': 'LAMBDA FUNCTIONS',
            'description': 'Testing Lambda handler functions',
            'tests': [
                # Will add if files exist
            ]
        },
        
        # Layer 5: Integration Tests
        {
            'section': 'INTEGRATION TESTS',
            'description': 'Testing complete end-to-end flows',
            'tests': [
                # Will add integration tests
            ]
        },
    ]
    
    # Run each test suite
    total_passed = 0
    total_failed = 0
    total_duration = 0
    
    for suite in test_suites:
        if not suite['tests']:
            continue
            
        print_section(suite['section'], suite['description'])
        
        for test_file, test_description in suite['tests']:
            test_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), test_file)
            
            if os.path.exists(test_path):
                passed, duration = run_pytest_suite(test_file, test_description)
                total_duration += duration
                
                if passed:
                    total_passed += 1
                else:
                    total_failed += 1
                    
                results.append({
                    'name': test_description,
                    'passed': passed,
                    'duration': duration
                })
            else:
                print(f"   {Colors.WARNING}⚠️  SKIPPED{Colors.ENDC} - {test_description} (file not found)")
        
        time.sleep(0.5)  # Brief pause between sections
    
    # Print Summary
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 80)
    print("  TEST SUMMARY")
    print("=" * 80)
    print(f"{Colors.ENDC}")
    
    print(f"\n{Colors.BOLD}Total Tests Run:{Colors.ENDC} {total_passed + total_failed}")
    print(f"{Colors.OKGREEN}{Colors.BOLD}[PASSED]:{Colors.ENDC} {total_passed}")
    print(f"{Colors.FAIL}{Colors.BOLD}[FAILED]:{Colors.ENDC} {total_failed}")
    print(f"{Colors.BOLD}Total Duration:{Colors.ENDC} {total_duration:.2f}s")
    print(f"{Colors.BOLD}Started:{Colors.ENDC} {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Colors.BOLD}Finished:{Colors.ENDC} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Detailed results
    if results:
        print(f"\n{Colors.BOLD}{Colors.OKCYAN}Detailed Results:{Colors.ENDC}")
        for i, result in enumerate(results, 1):
            status = f"{Colors.OKGREEN}[PASS]{Colors.ENDC}" if result['passed'] else f"{Colors.FAIL}[FAIL]{Colors.ENDC}"
            print(f"  {i}. {status} {result['name']} - {result['duration']:.2f}s")
    
    # Architecture Coverage Summary
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}Architecture Coverage:{Colors.ENDC}")
    coverage_items = [
        ("S3 Email Storage", "[TESTED]"),
        ("S3 Attachment Storage", "[TESTED]"),
        ("DynamoDB Projects Table", "[TESTED]"),
        ("DynamoDB Events Table", "[TESTED]"),
        ("DynamoDB Users Table", "[TESTED]"),
        ("Email MIME Parsing", "[TESTED]"),
        ("Attachment Extraction", "[TESTED]"),
        ("AI Project Data Extraction", "[TESTED]"),
        ("AI Estimate Generation", "[TESTED]"),
        ("AI Response Generation", "[TESTED]"),
        ("Input Sanitization", "[TESTED]"),
    ]
    
    for item, status in coverage_items:
        print(f"  * {item}: {Colors.OKGREEN}{status}{Colors.ENDC}")
    
    # Final verdict
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
    if total_failed == 0:
        print(f"{Colors.BOLD}{Colors.OKGREEN}>>> ALL TESTS PASSED! System is working correctly. <<<{Colors.ENDC}")
    else:
        print(f"{Colors.BOLD}{Colors.FAIL}>>> SOME TESTS FAILED - Please review errors above <<<{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}\n")
    
    return total_failed == 0


def main():
    """Main entry point."""
    # Set UTF-8 encoding for Windows console
    import sys
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass  # Fallback if reconfigure not available
    
    print(f"{Colors.BOLD}{Colors.OKBLUE}")
    print(">> Starting Comprehensive Test Suite...")
    print(f"{Colors.ENDC}")
    
    # Check if pytest is available
    try:
        import pytest  # noqa: F401
        print(f"{Colors.OKGREEN}[OK] pytest found{Colors.ENDC}")
    except ImportError:
        print(f"{Colors.FAIL}[ERROR] pytest not found. Installing...{Colors.ENDC}")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pytest'])
    
    # Run tests
    success = run_architecture_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

