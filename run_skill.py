import sys
import os

# 添加skill目录到路径
sys.path.insert(0, r"e:\AI\skill")

import requests
import time

API_KEY = "sk-WNp6MYkparZaiZQQ8QgtpJbTAkxIH3uIfQXtbsz2DjuEgkSf"
BASE_URL = "https://api.bltcy.ai"

log_file = r"e:\AI\skill\final_result.txt"

with open(log_file, "w", encoding="utf-8") as log:
    log.write("Generating image...\n")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = """Beautiful elegant woman in traditional Chinese garden. 
Black top, grey skirt, black stockings, black heels. 
Chinese architecture, green trees, natural daylight.
Elegant fashion portrait, photorealistic, high quality."""
    
    payload = {
        "model": "nano-banana-pro",
        "prompt": prompt,
        "size": "1024x1024"
    }
    
    log.write("Calling API...\n")
    log.flush()
    
    response = requests.post(
        f"{BASE_URL}/v1/images/generations",
        headers=headers,
        json=payload,
        timeout=180
    )
    
    if response.status_code == 200:
        result = response.json()
        url = result["data"][0]["url"]
        log.write(f"SUCCESS! URL: {url}\n")
        
        with open(r"e:\AI\skill\final_image_url.txt", "w") as f:
            f.write(url)
        
        try:
            img = requests.get(url, timeout=60)
            with open(r"e:\AI\skill\uploads\final_generated.png", "wb") as f:
                f.write(img.content)
            log.write("Image saved\n")
        except:
            pass
    else:
        log.write(f"Error: {response.text}\n")

print("Done! Check e:\\AI\\skill\\final_result.txt")
