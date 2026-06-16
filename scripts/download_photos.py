import os
import time
from io import BytesIO
from urllib.parse import quote_plus

import requests
from PIL import Image

PHOTOS_DIR = os.path.join(os.path.dirname(__file__), "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)

# Dikey foto query'leri. Her dosya icin farkli lock kullanilir; boylece onceki
# yatay set tekrar edilmeden yeni kompozisyonlar indirilir.
PHOTOS = {
    "k1_sol.jpg":  ("turquoise beach portrait aerial coast", 101),
    "k1_sag.jpg":  ("alpine lake mountains portrait trail", 102),
    "k2_sol.jpg":  ("old stone street historic town portrait", 103),
    "k2_sag.jpg":  ("ski slope snowy mountain portrait", 104),

    "tur1_sol.jpg": ("surf beach waves lively shore portrait", 201),
    "tur1_sag.jpg": ("quiet cove clear water vertical beach", 202),

    "tur2_sol.jpg": ("night street music crowd travel portrait", 203),
    "tur2_sag.jpg": ("quiet village evening warm lights portrait", 204),

    "tur3_sol.jpg": ("hot air balloons landscape portrait", 205),
    "tur3_sag.jpg": ("forest hiking trail vertical", 206),

    "tur4_sol.jpg": ("mountain hiking adventure ridge portrait", 207),
    "tur4_sag.jpg": ("calm mountain lake reflection portrait", 208),

    "tur5_sol.jpg": ("ancient ruins stone columns portrait", 209),
    "tur5_sag.jpg": ("cultural festival dance crowd portrait", 210),

    "tur6_sol.jpg": ("local food market street travel portrait", 211),
    "tur6_sag.jpg": ("luxury resort pool tropical portrait", 212),

    "tur7_sol.jpg": ("busy city street lights pedestrian portrait", 213),
    "tur7_sag.jpg": ("misty mountains quiet valley portrait", 214),

    "tur8_sol.jpg": ("snorkeling coral reef underwater portrait", 215),
    "tur8_sag.jpg": ("sunset beach walk calm portrait", 216),
}

PHOTO_SOURCE_URL = "https://loremflickr.com/{width}/{height}/{query}?lock={sig}"
TARGET_SIZE = (720, 960)


def kirp_ve_kaydet(content: bytes, hedef: str) -> None:
    img = Image.open(BytesIO(content)).convert("RGB")
    hedef_oran = TARGET_SIZE[0] / TARGET_SIZE[1]
    oran = img.width / img.height

    if oran > hedef_oran:
        yeni_genislik = int(img.height * hedef_oran)
        left = (img.width - yeni_genislik) // 2
        img = img.crop((left, 0, left + yeni_genislik, img.height))
    elif oran < hedef_oran:
        yeni_yukseklik = int(img.width / hedef_oran)
        top = (img.height - yeni_yukseklik) // 2
        img = img.crop((0, top, img.width, top + yeni_yukseklik))

    img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    img.save(hedef, "JPEG", quality=88, optimize=True, progressive=True)


def indir(dosya: str, photo_spec: tuple[str, int]) -> bool:
    hedef = os.path.join(PHOTOS_DIR, dosya)
    query, sig = photo_spec
    tags = quote_plus(",".join(query.split()[:4]))
    url = PHOTO_SOURCE_URL.format(
        width=TARGET_SIZE[0],
        height=TARGET_SIZE[1],
        query=tags,
        sig=sig,
    )
    try:
        r = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; travel-recommender/1.0)"
        }, allow_redirects=True)
        if r.status_code == 200:
            kirp_ve_kaydet(r.content, hedef)
            boyut = os.path.getsize(hedef) // 1024
            print(f"  ↓ Yenilendi: {dosya} ({boyut} KB)")
            return True
        else:
            print(f"  ✗ Hata {r.status_code}: {dosya}")
            return False
    except Exception as e:
        print(f"  ✗ İstisna: {dosya} — {e}")
        return False

def main():
    print(f"[Fotoğraf] {len(PHOTOS)} fotoğraf yenileniyor → {PHOTOS_DIR}\n")
    basarili = 0
    for dosya, photo_id in PHOTOS.items():
        if indir(dosya, photo_id):
            basarili += 1
        time.sleep(0.3)  # rate limit

    print(f"\n[Fotoğraf] {basarili}/{len(PHOTOS)} başarılı")

if __name__ == "__main__":
    main()
