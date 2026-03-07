#!/usr/bin/env python
"""
Test script to verify Jarvis-OS Dashboard Phase 1 Implementation
Tests all components and ensures everything is working correctly
"""

import os
import sys
import asyncio
from pathlib import Path

def test_files_exist():
    """Test that all required Phase 1 files exist"""
    print("=" * 60)
    print("TEST 1: Checking required files...")
    print("=" * 60)
    
    required_files = [
        "dashboard_api.py",
        "dashboard_ui_setup.py",
        "jarvis_os.py",
        "DASHBOARD_QUICKSTART.md",
        "STATUS_REPORT.md",
    ]
    
    all_exist = True
    for fname in required_files:
        fpath = Path(fname)
        exists = fpath.exists()
        status = "✅" if exists else "❌"
        print(f"{status} {fname}")
        if not exists:
            all_exist = False
    
    return all_exist

def test_imports():
    """Test that all required modules can be imported"""
    print("\n" + "=" * 60)
    print("TEST 2: Checking Python imports...")
    print("=" * 60)
    
    # Test standard library imports
    imports_to_test = [
        ("asyncio", "Async support"),
        ("json", "JSON support"),
        ("os", "OS operations"),
        ("time", "Time functions"),
        ("datetime", "Date/time"),
    ]
    
    all_ok = True
    for module_name, desc in imports_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name}: {desc}")
        except ImportError as e:
            print(f"❌ {module_name}: {desc} - {e}")
            all_ok = False
    
    # Test Jarvis-OS import
    try:
        from jarvis_os import JarvisOS, AgentConfig, TaskPriority
        print(f"✅ jarvis_os: Main Jarvis-OS classes")
    except ImportError as e:
        print(f"❌ jarvis_os: {e}")
        all_ok = False
    
    # Test dashboard_ui_setup import
    try:
        from dashboard_ui_setup import create_dashboard_ui
        print(f"✅ dashboard_ui_setup: UI generator function")
    except ImportError as e:
        print(f"❌ dashboard_ui_setup: {e}")
        all_ok = False
    
    return all_ok

def test_dashboard_ui_setup():
    """Test that dashboard UI setup works"""
    print("\n" + "=" * 60)
    print("TEST 3: Testing dashboard UI setup...")
    print("=" * 60)
    
    try:
        from dashboard_ui_setup import create_dashboard_ui
        
        static_dir = create_dashboard_ui()
        print(f"✅ Dashboard UI created at: {static_dir}")
        
        # Check if static directory exists
        if Path(static_dir).exists():
            print(f"✅ Static directory exists")
        else:
            print(f"❌ Static directory not found")
            return False
        
        # Check if index.html was created
        index_path = Path(static_dir) / "index.html"
        if index_path.exists():
            print(f"✅ index.html created ({index_path.stat().st_size} bytes)")
            
            # Check if HTML has expected content
            with open(index_path, 'r') as f:
                content = f.read()
                checks = [
                    ("Jarvis-OS Dashboard", "Dashboard title"),
                    ("Chart.js", "Chart library"),
                    ("/api/agent/start", "Agent start endpoint"),
                    ("/ws/metrics", "WebSocket metrics"),
                ]
                
                all_found = True
                for needle, desc in checks:
                    if needle in content:
                        print(f"✅ {desc}: found")
                    else:
                        print(f"❌ {desc}: NOT FOUND")
                        all_found = False
                
                return all_found
        else:
            print(f"❌ index.html not created")
            return False
            
    except Exception as e:
        print(f"❌ Error testing dashboard UI setup: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_jarvis_os_core():
    """Test that Jarvis-OS core components work"""
    print("\n" + "=" * 60)
    print("TEST 4: Testing Jarvis-OS core...")
    print("=" * 60)
    
    try:
        from jarvis_os import JarvisOS, AgentConfig
        from fast_router import TaskPriority
        from executor import Executor
        from autopsy import Autopsy
        from mutation import Mutation
        
        print(f"✅ All Jarvis-OS modules imported")
        
        # Test creating agent config
        config = AgentConfig(
            name="test_agent",
            optimization_mode="adaptive"
        )
        print(f"✅ AgentConfig created: {config.name}")
        
        # Test TaskPriority enum
        print(f"✅ TaskPriority enum available: {TaskPriority.HIGH}, {TaskPriority.NORMAL}")
        
        return True
    except Exception as e:
        print(f"❌ Error testing Jarvis-OS: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dashboard_api_syntax():
    """Test that dashboard_api.py has valid syntax"""
    print("\n" + "=" * 60)
    print("TEST 5: Checking dashboard_api.py syntax...")
    print("=" * 60)
    
    try:
        with open("dashboard_api.py", "r") as f:
            code = f.read()
        
        # Try to compile the code
        compile(code, "dashboard_api.py", "exec")
        print(f"✅ dashboard_api.py: Valid Python syntax")
        
        # Check for required endpoints
        endpoints = [
            "/api/health",
            "/api/agent/status",
            "/api/agent/start",
            "/api/agent/stop",
            "/api/tasks/submit",
            "/ws/metrics",
        ]
        
        all_found = True
        for endpoint in endpoints:
            if endpoint in code:
                print(f"✅ Endpoint {endpoint}: found")
            else:
                print(f"❌ Endpoint {endpoint}: NOT FOUND")
                all_found = False
        
        return all_found
    except Exception as e:
        print(f"❌ Error checking dashboard_api.py: {e}")
        return False

def test_documentation():
    """Test that documentation files exist and have content"""
    print("\n" + "=" * 60)
    print("TEST 6: Checking documentation...")
    print("=" * 60)
    
    docs = [
        ("DASHBOARD_QUICKSTART.md", "Quick start guide"),
        ("STATUS_REPORT.md", "Status report"),
        ("PHASE_1_SUMMARY.md", "Phase 1 summary"),
    ]
    
    all_ok = True
    for fname, desc in docs:
        fpath = Path(fname)
        if fpath.exists():
            size = fpath.stat().st_size
            print(f"✅ {fname}: {desc} ({size} bytes)")
        else:
            print(f"❌ {fname}: NOT FOUND")
            all_ok = False
    
    return all_ok

def run_all_tests():
    """Run all tests and report results"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "JARVIS-OS PHASE 1 VALIDATION TEST" + " " * 14 + "║")
    print("╚" + "=" * 58 + "╝")
    
    tests = [
        ("Files", test_files_exist),
        ("Imports", test_imports),
        ("UI Setup", test_dashboard_ui_setup),
        ("Core", test_jarvis_os_core),
        ("API Syntax", test_dashboard_api_syntax),
        ("Documentation", test_documentation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n" + "🎉 " * 15)
        print("✅ ALL TESTS PASSED! Phase 1 is ready to deploy!")
        print("🎉 " * 15)
        print("\nNext steps:")
        print("1. Run: pip install fastapi uvicorn")
        print("2. Run: python dashboard_api.py")
        print("3. Open: http://localhost:8000")
        return True
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
