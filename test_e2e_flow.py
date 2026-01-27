import httpx
import asyncio
import os

# Configuration
BACKEND_URL = "http://localhost:8000"
TEST_USER = "e2e_test_user_final"
TEST_PASS = "testpassword123"
IMAGE_PATH = "/app/uploads/users/test_image.jpg"

async def run_e2e_test():
    print(f"🚀 Starting E2E Test on {BACKEND_URL}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Register
        print(f"\n1. Registering user '{TEST_USER}'...")
        reg_resp = await client.post(f"{BACKEND_URL}/auth/register", json={
            "username": TEST_USER,
            "password": TEST_PASS,
            "full_name": "Test User",
            "age": 25,
            "gender": "male"
        })
        if reg_resp.status_code in [200, 201]:
            print("   ✅ Registered")
        elif reg_resp.status_code == 400 and "already registered" in reg_resp.text:
             print("   ⚠️ User already exists (continuing)")
        else:
            print(f"   ❌ Registration Failed: {reg_resp.status_code} {reg_resp.text}")
            # Try to continue to login anyway, just in case


        # 2. Login
        print(f"\n2. Logging in...")
        login_resp = await client.post(f"{BACKEND_URL}/auth/login", data={
            "username": TEST_USER,
            "password": TEST_PASS
        })
        
        if login_resp.status_code != 200:
            print(f"   ❌ Login Failed: {login_resp.text}")
            return
            
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("   ✅ Logged in")

        # 3. Upload Photo
        print(f"\n3. Uploading photo...")
        if not os.path.exists(IMAGE_PATH):
            print(f"   ❌ Image not found at {IMAGE_PATH}. Run 'curl -L -o {IMAGE_PATH} https://picsum.photos/400/600' first.")
            return

        files = {"file": ("test_outfit.jpg", open(IMAGE_PATH, "rb"), "image/jpeg")}
        upload_resp = await client.post(f"{BACKEND_URL}/api/v1/user/photos", headers=headers, files=files)
        
        # Note: Depending on implementation, endpoint might be /user/photos or /api/v1/user/photos
        # Let's try the router prefix path.
        if upload_resp.status_code == 404:
             # retry with /user/photos (sometimes mounted directly)
             upload_resp = await client.post(f"{BACKEND_URL}/user/photos", headers=headers, files=files)

        if upload_resp.status_code != 200:
             print(f"   ❌ Upload Failed: {upload_resp.status_code} {upload_resp.text}")
             return
        
        photo_info = upload_resp.json()
        photo_url = photo_info["url"]
        photo_filename = photo_info.get("filename") 
        if not photo_filename and "url" in photo_info:
             photo_filename = photo_info["url"].split("/")[-1]
             
        print(f"   ✅ Uploaded: {photo_url} (Filename: {photo_filename})")

        # 4. Analyze Photo
        print(f"\n4. Requesting AI Analysis (via GPU)...")
        analyze_payload = {
            "filename": photo_filename 
        }
        
        # Checking endpoint path logic from user.py
        # It seems to be /user/ai/analyze based on recent edits? Or /ai/analyze mounted under user?
        # Let's try /user/ai/analyze
        analyze_resp = await client.post(f"{BACKEND_URL}/user/ai/analyze", headers=headers, json=analyze_payload)
        
        if analyze_resp.status_code == 200:
            result = analyze_resp.json()
            print(f"   RAW RESPONSE: {result}")
            print("   ✅ Analysis Request Completed")
            print(f"   🎨 Personal Color: {result.get('user_analysis', {}).get('personal_color')}")
            print(f"   🚨 Fashion Terrorist: {result.get('fashion_terrorist_check', {}).get('is_terrorist')}")
            print(f"   🛍️ Recommendations: {len(result.get('recommendations', []))} items")
        else:
            print(f"   ❌ Analysis Failed: {analyze_resp.status_code}")
            print(f"   Response: {analyze_resp.text}")
            print("\n   👉 If 404/500 from GPU, it means the GPU server hasn't updated the code yet.")

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
