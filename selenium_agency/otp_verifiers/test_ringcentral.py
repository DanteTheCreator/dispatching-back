#!/usr/bin/env python3
"""
Test script for RingCentral SMS extraction
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from ringcentral_sms_extract import get_central_dispatch_code, ringcentral_sms_extract

def test_extraction():
    print("=" * 50)
    print("Testing RingCentral SMS Code Extraction")
    print("=" * 50)
    
    # Test with Central Dispatch specific function
    print("\n1. Testing Central Dispatch code extraction...")
    code = get_central_dispatch_code()
    if code:
        print(f"✅ Successfully extracted Central Dispatch code: {code}")
    else:
        print("❌ No Central Dispatch code found")
    
    # Test with general extraction
    print("\n2. Testing general SMS extraction...")
    code = ringcentral_sms_extract()
    if code:
        print(f"✅ Successfully extracted code: {code}")
    else:
        print("❌ No code found")
    
    print("\n" + "=" * 50)
    print("Test completed")
    print("=" * 50)

if __name__ == "__main__":
    test_extraction()
