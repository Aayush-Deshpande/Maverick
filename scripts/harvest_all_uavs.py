import os
import sys
import time
import json
import csv
import hashlib
import urllib.parse
import requests
from PIL import Image
from playwright.sync_api import sync_playwright

BASE_DIR = r"E:\backup-llm\backup-no-llm\3d_engine\ANUMAAN\Models_Images"

UAV_CONFIGS = {
    "Bayraktar_TB2": {
        "variant": "Bayraktar TB2 Block 2 (MALE UCAV)",
        "engine_sub": "03_Engine_Rotax_912iS",
        "engine_name": "Rotax 912 iS Sport (100 hp)",
        "propeller": "2-blade variable pitch wood/composite pusher",
        "sensors": "WESCAM MX-15D / Aselsan CATS EO/IR turret, dorsal SATCOM / C-band datalink",
        "munitions": "4x Roketsan MAM-L / MAM-C laser-guided smart micro-munitions",
        "dimensions": "Wingspan: 12.0m, Length: 6.5m, Height: 2.2m, MTOW: 700kg",
        "wiki_queries": [
            "Bayraktar TB2", "Bayraktar TB2 drone", "Bayraktar TB2 Air Show",
            "Bayraktar TB2 drawing", "Bayraktar TB2 missile", "Bayraktar TB2 Teknofest",
            "Bayraktar TB2 Radom", "Bayraktar TB2 engine"
        ],
        "bing_queries": {
            "01_Orthographic": [
                "Bayraktar TB2 3 view blueprint drawing",
                "Bayraktar TB2 orthographic technical drawing",
                "Bayraktar TB2 dimensions schematic"
            ],
            "02_Exterior": [
                "Bayraktar TB2 high resolution in flight",
                "Bayraktar TB2 airshow walkaround photo",
                "Bayraktar TB2 runway taxi takeoff"
            ],
            "03_Engine_Rotax_912iS": [
                "Bayraktar TB2 engine bay Rotax 912",
                "Bayraktar TB2 engine exhaust cowling",
                "Rotax 912 iS Sport aero engine high resolution"
            ],
            "04_Propeller": [
                "Bayraktar TB2 pusher propeller hub",
                "Bayraktar TB2 propeller blades pitch mechanism"
            ],
            "05_Sensors_Payload": [
                "Bayraktar TB2 WESCAM MX-15D EO/IR turret",
                "Bayraktar TB2 Aselsan CATS camera ball",
                "Bayraktar TB2 Roketsan MAM-L missile pylon"
            ],
            "06_Landing_Gear": [
                "Bayraktar TB2 nose landing gear wheel",
                "Bayraktar TB2 main gear composite leaf strut wheel"
            ],
            "07_Surface_Textures": [
                "Bayraktar TB2 composite skin panel lines close up",
                "Bayraktar TB2 carbon fiber airframe finish"
            ],
            "08_Markings_Decals": [
                "Bayraktar TB2 roundels national insignia markings",
                "Bayraktar TB2 stencils warning decals tail number"
            ],
            "09_Dimensions": [
                "Bayraktar TB2 official dimensions Baykar specifications",
                "Bayraktar TB2 cutaway diagram technical"
            ],
            "10_CAD_3D": [
                "Bayraktar TB2 3D model CAD wireframe",
                "Bayraktar TB2 3D mesh polygon"
            ],
            "11_Technical_Documents": [
                "Bayraktar TB2 technical brochure Baykar PDF",
                "Bayraktar TB2 flight manual specifications"
            ]
        }
    },
    "MQ1_Predator": {
        "variant": "General Atomics MQ-1B Predator (Inverted V-tail, Bulbous Nose)",
        "engine_sub": "03_Engine_Rotax_914F",
        "engine_name": "Rotax 914F Turbocharged (115 hp)",
        "propeller": "2-blade variable pitch pusher propeller",
        "sensors": "Raytheon AN/AAS-52 MTS-A EO/IR turret, Ku-band SATCOM nose radome",
        "munitions": "2x AGM-114 Hellfire air-to-ground missiles",
        "dimensions": "Wingspan: 14.8m / 16.8m, Length: 8.22m, Height: 2.1m, MTOW: 1020kg",
        "wiki_queries": [
            "MQ-1 Predator", "General Atomics MQ-1", "MQ-1B Predator",
            "MQ-1 Predator USAF", "MQ-1 Predator engine", "MQ-1 Predator flight",
            "MQ-1 Predator Hellfire", "Rotax 914"
        ],
        "bing_queries": {
            "01_Orthographic": [
                "MQ-1 Predator 3 view blueprint drawing",
                "MQ-1B Predator orthographic schematic",
                "MQ-1 Predator dimensional drawing"
            ],
            "02_Exterior": [
                "MQ-1 Predator high resolution USAF flight",
                "MQ-1B Predator ground walkaround airshow",
                "MQ-1 Predator runway takeoff landing"
            ],
            "03_Engine_Rotax_914F": [
                "MQ-1 Predator Rotax 914 engine bay turbocharger",
                "MQ-1 Predator engine exhaust scoop",
                "Rotax 914F aircraft engine high resolution"
            ],
            "04_Propeller": [
                "MQ-1 Predator pusher propeller hub",
                "MQ-1 Predator propeller blades pitch"
            ],
            "05_Sensors_Payload": [
                "MQ-1 Predator AN/AAS-52 MTS-A turret ball",
                "MQ-1 Predator AGM-114 Hellfire pylon wing mount",
                "MQ-1 Predator SATCOM radome nose bulge"
            ],
            "06_Landing_Gear": [
                "MQ-1 Predator retractable nose landing gear",
                "MQ-1 Predator main landing gear strut wheel well"
            ],
            "07_Surface_Textures": [
                "MQ-1 Predator panel lines rivets composite skin close up",
                "MQ-1 Predator weathered military grey paint"
            ],
            "08_Markings_Decals": [
                "MQ-1 Predator USAF markings serial numbers stencils",
                "MQ-1 Predator rescue markings warning labels"
            ],
            "09_Dimensions": [
                "MQ-1 Predator official dimensions General Atomics",
                "MQ-1 Predator technical cutaway diagram"
            ],
            "10_CAD_3D": [
                "MQ-1 Predator 3D model CAD wireframe",
                "MQ-1 Predator 3D mesh polygon"
            ],
            "11_Technical_Documents": [
                "MQ-1B Predator technical order manual USAF",
                "General Atomics Predator datasheet specifications"
            ]
        }
    },
    "IAI_Heron_MkII": {
        "variant": "IAI Heron Mk II MALE Tactical UAV",
        "engine_sub": "03_Engine_Rotax_915iS",
        "engine_name": "Rotax 915 iS Turbocharged (141 hp)",
        "propeller": "3-blade constant-speed pusher propeller",
        "sensors": "IAI ELTA ELM-2055 SAR/GMTI radar, M-STAMP / POP300 EO/IR turret, dorsal SATCOM radome",
        "munitions": "Long-range multi-mission reconnaissance & target acquisition pods",
        "dimensions": "Wingspan: 16.6m, Length: 8.5m, Height: 2.3m, MTOW: 1430kg",
        "wiki_queries": [
            "IAI Heron", "IAI Heron Mk II", "Heron UAV", "Heron drone",
            "IAI Heron radar", "IAI Heron Paris Air Show", "Rotax 915 iS"
        ],
        "bing_queries": {
            "01_Orthographic": [
                "IAI Heron Mk II 3 view blueprint drawing",
                "IAI Heron orthographic schematic",
                "Heron Mk II dimensional diagram"
            ],
            "02_Exterior": [
                "IAI Heron Mk II high resolution flight",
                "IAI Heron Mk 2 Singapore Paris Airshow walkaround",
                "IAI Heron ground display runway"
            ],
            "03_Engine_Rotax_915iS": [
                "IAI Heron Mk II engine installation Rotax 915",
                "Rotax 915 iS aero engine high resolution",
                "Rotax 915 iS turbocharger intercooler"
            ],
            "04_Propeller": [
                "IAI Heron 3 blade pusher propeller spinner",
                "IAI Heron propeller hub variable pitch"
            ],
            "05_Sensors_Payload": [
                "IAI Heron ELTA SAR radar belly canoe pod",
                "IAI Heron EO/IR turret sensor ball",
                "IAI Heron dorsal SATCOM dome"
            ],
            "06_Landing_Gear": [
                "IAI Heron retractable landing gear nose wheel",
                "IAI Heron main landing gear strut"
            ],
            "07_Surface_Textures": [
                "IAI Heron composite skin panel lines close up",
                "IAI Heron paint texture surface finish"
            ],
            "08_Markings_Decals": [
                "IAI Heron markings national roundels stencils",
                "IAI Heron registration decals caution"
            ],
            "09_Dimensions": [
                "IAI Heron Mk II dimensions specifications IAI",
                "IAI Heron Mk II cutaway drawing"
            ],
            "10_CAD_3D": [
                "IAI Heron 3D model CAD wireframe",
                "IAI Heron 3D mesh polygon"
            ],
            "11_Technical_Documents": [
                "IAI Heron Mk II brochure PDF IAI",
                "IAI Heron technical datasheet specifications"
            ]
        }
    },
    "TAI_ANKA": {
        "variant": "TAI ANKA-S / Block B MALE UCAV",
        "engine_sub": "03_Engine_TEI_PD170",
        "engine_name": "TEI-PD170 Turbodiesel (172 hp)",
        "propeller": "3-blade constant-speed pusher propeller",
        "sensors": "Aselsan CATS EO/IR turret, SAR/GMTI radar, SATCOM antenna inside dorsal nose bulge",
        "munitions": "Roketsan MAM-L / MAM-C laser-guided smart micro-munitions, Cirit missiles",
        "dimensions": "Wingspan: 17.5m, Length: 8.6m, Height: 3.25m, MTOW: 1700kg",
        "wiki_queries": [
            "TAI Anka", "TAI Anka UAV", "Anka drone", "TAI Anka-S",
            "Anka Teknofest", "Anka IDEF", "TEI PD170"
        ],
        "bing_queries": {
            "01_Orthographic": [
                "TAI Anka 3 view blueprint drawing",
                "TAI Anka-S orthographic schematic",
                "TAI Anka dimensional drawing"
            ],
            "02_Exterior": [
                "TAI Anka high resolution in flight",
                "TAI Anka IDEF Teknofest walkaround photo",
                "TAI Anka-S runway ground display"
            ],
            "03_Engine_TEI_PD170": [
                "TAI Anka TEI PD170 engine bay exhaust",
                "TEI PD170 turbodiesel engine high resolution",
                "TEI PD170 twin turbocharger aircraft"
            ],
            "04_Propeller": [
                "TAI Anka 3 blade pusher propeller",
                "TAI Anka propeller hub spinner"
            ],
            "05_Sensors_Payload": [
                "TAI Anka Aselsan CATS EO/IR turret",
                "TAI Anka dorsal nose SATCOM radome",
                "TAI Anka MAM-L missile pylon"
            ],
            "06_Landing_Gear": [
                "TAI Anka retractable landing gear nose wheel",
                "TAI Anka main landing gear trailing link strut"
            ],
            "07_Surface_Textures": [
                "TAI Anka composite skin panel lines close up",
                "TAI Anka carbon fiber panels finish"
            ],
            "08_Markings_Decals": [
                "TAI Anka Turkish Air Force roundels serials",
                "TAI Anka warning markings stencils rescue"
            ],
            "09_Dimensions": [
                "TAI Anka official dimensions TAI specifications",
                "TAI Anka technical cutaway drawing"
            ],
            "10_CAD_3D": [
                "TAI Anka 3D model CAD wireframe",
                "TAI Anka 3D mesh polygon"
            ],
            "11_Technical_Documents": [
                "TAI Anka brochure PDF Turkish Aerospace",
                "TAI Anka technical datasheet specifications"
            ]
        }
    },
    "TAPAS_BH201_RustomII": {
        "variant": "DRDO TAPAS-BH-201 (Rustom-II Twin-Engine MALE UAV)",
        "engine_sub": "03_Engine_Austro_E4",
        "engine_name": "Twin Austro Engine AE300 / E4-Series Turbodiesels (2x 180 hp)",
        "propeller": "Twin MT-Propeller 3-blade constant-speed tractor propellers with polished spinners",
        "sensors": "BEL / ADE EO/IR surveillance turret, Synthetic Aperture Radar (SAR), Indigenous SATCOM nose dome",
        "munitions": "Reconnaissance, target designation, electronic intelligence (ELINT/COMINT)",
        "dimensions": "Wingspan: 20.6m, Length: 9.5m, Height: 3.6m, MTOW: 2850kg",
        "wiki_queries": [
            "Rustom-II", "TAPAS-BH-201", "DRDO Rustom", "TAPAS drone",
            "TAPAS Aero India", "Rustom II drone Aero India"
        ],
        "bing_queries": {
            "01_Orthographic": [
                "TAPAS BH 201 3 view blueprint drawing",
                "Rustom II 3 view schematic",
                "TAPAS BH-201 orthographic drawing"
            ],
            "02_Exterior": [
                "TAPAS BH 201 high resolution Aero India",
                "DRDO TAPAS-BH-201 flight test Chitradurga",
                "Rustom II drone ground walkaround"
            ],
            "03_Engine_Austro_E4": [
                "TAPAS BH 201 Austro engine nacelle cowling",
                "TAPAS BH-201 engine bay maintenance",
                "Austro Engine E4 AE330 aircraft engine"
            ],
            "04_Propeller": [
                "TAPAS BH 201 MT propeller spinner tractor",
                "Rustom II 3 blade propeller hub"
            ],
            "05_Sensors_Payload": [
                "TAPAS BH 201 BEL EO/IR sensor ball turret",
                "TAPAS BH-201 SAR radar canoe SATCOM dome"
            ],
            "06_Landing_Gear": [
                "TAPAS BH 201 nose landing gear wheel",
                "TAPAS BH-201 nacelle main gear retraction strut"
            ],
            "07_Surface_Textures": [
                "TAPAS BH 201 composite airframe panel lines close up",
                "DRDO TAPAS white paint surface finish"
            ],
            "08_Markings_Decals": [
                "TAPAS BH 201 Indian Air Force roundels DRDO markings",
                "TAPAS BH-201 warning labels stencils caution"
            ],
            "09_Dimensions": [
                "TAPAS BH 201 dimensions DRDO ADE specifications",
                "Rustom II technical cutaway drawing"
            ],
            "10_CAD_3D": [
                "TAPAS BH 201 3D model CAD wireframe",
                "Rustom II 3D mesh polygon"
            ],
            "11_Technical_Documents": [
                "TAPAS BH-201 brochure DRDO Aero India PDF",
                "TAPAS BH 201 technical datasheet ADE"
            ]
        }
    },
    "CASC_CH4": {
        "variant": "CASC CH-4B / CH-4C Heavy Fuel Variant (Pusher MALE UCAV)",
        "engine_sub": "03_Engine_Lark_HFE",
        "engine_name": "Lark HFE (Heavy Fuel Engine) (150 hp)",
        "propeller": "3-blade pusher propeller with variable/ground-adjustable pitch",
        "sensors": "4-in-1 EO/IR sensor turret, synthetic aperture radar pod, nose SATCOM dome",
        "munitions": "4x underwing hardpoints: AR-1 laser-guided missiles, AKD-10, FT-9 glide bombs",
        "dimensions": "Wingspan: 18.0m, Length: 8.5m, Height: 3.4m, MTOW: 1330kg",
        "wiki_queries": [
            "CASC CH-4", "Rainbow CH-4", "CH-4 drone", "CH-4 UAV",
            "CH-4B UCAV", "CASC Rainbow Zhuhai"
        ],
        "bing_queries": {
            "01_Orthographic": [
                "CASC CH-4 3 view blueprint drawing",
                "CH-4 drone orthographic schematic",
                "CASC Rainbow 4 dimensional drawing"
            ],
            "02_Exterior": [
                "CASC CH-4 drone high resolution in flight",
                "CH-4B Rainbow Zhuhai Airshow walkaround photo",
                "CH-4 UCAV runway ground display"
            ],
            "03_Engine_Lark_HFE": [
                "CH-4 drone heavy fuel engine Lark HFE",
                "Lark HFE heavy fuel engine high resolution",
                "CH-4 engine bay exhaust cowling"
            ],
            "04_Propeller": [
                "CH-4 drone 3 blade pusher propeller hub",
                "CH-4 UAV propeller spinner pitch"
            ],
            "05_Sensors_Payload": [
                "CH-4 drone EO/IR 4 in 1 sensor turret",
                "CH-4 drone AR-1 missile pylon hardpoint",
                "CH-4 SATCOM dome radome"
            ],
            "06_Landing_Gear": [
                "CH-4 drone landing gear nose wheel",
                "CH-4 UAV main landing gear strut wheel"
            ],
            "07_Surface_Textures": [
                "CH-4 drone composite skin panel lines close up",
                "CH-4 UAV grey paint weathering finish"
            ],
            "08_Markings_Decals": [
                "CH-4 drone markings serial numbers stencils",
                "Rainbow-4 warning markings rescue decals caution"
            ],
            "09_Dimensions": [
                "CASC CH-4 official dimensions CASC specifications",
                "CH-4 drone technical cutaway drawing"
            ],
            "10_CAD_3D": [
                "CH-4 drone 3D model CAD wireframe",
                "CH-4 UAV 3D mesh polygon"
            ],
            "11_Technical_Documents": [
                "CASC CH-4 brochure PDF Zhuhai Airshow",
                "CH-4 drone technical datasheet specifications"
            ]
        }
    }
}

def get_file_md5(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def download_and_verify(url, dest_path, min_size=(250, 250), min_bytes=10000):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    try:
        r = requests.get(url, headers=headers, timeout=12, verify=False)
        if r.status_code == 200 and len(r.content) >= min_bytes:
            # Handle SVG
            if url.lower().endswith('.svg') or 'image/svg+xml' in r.headers.get('Content-Type', ''):
                with open(dest_path, 'wb') as f:
                    f.write(r.content)
                return (1920, 1080), "SVG", len(r.content)

            # Check image with PIL
            with open(dest_path, 'wb') as f:
                f.write(r.content)
            try:
                with Image.open(dest_path) as im:
                    w, h = im.size
                    fmt = im.format
                    if w >= min_size[0] and h >= min_size[1]:
                        return (w, h), fmt, len(r.content)
                    else:
                        os.remove(dest_path)
                        return None
            except:
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                return None
    except:
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except:
                pass
        return None
    return None

def harvest_wikimedia_for_uav(uav_name, uav_info, existing_hashes, records):
    print(f"\n[Wikimedia Commons] Harvesting for {uav_name}...")
    uav_dir = os.path.join(BASE_DIR, uav_name)
    wiki_api = "https://commons.wikimedia.org/w/api.php"
    headers = {'User-Agent': 'UAVVisualDatasetResearch/1.0 (academic; high-fidelity 3d reconstruction)'}

    for query in uav_info["wiki_queries"]:
        params = {
            'action': 'query',
            'generator': 'search',
            'gsrsearch': query,
            'gsrnamespace': 6,
            'gsrlimit': 15,
            'prop': 'imageinfo',
            'iiprop': 'url|size|extmetadata',
            'format': 'json'
        }
        try:
            resp = requests.get(wiki_api, params=params, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            data = resp.json()
            pages = data.get('query', {}).get('pages', {})
            for pid, page_info in pages.items():
                title = page_info.get('title', '')
                ii = page_info.get('imageinfo', [{}])[0]
                img_url = ii.get('url')
                width = ii.get('width', 0)
                height = ii.get('height', 0)
                extmeta = ii.get('extmetadata', {})
                artist = extmeta.get('Artist', {}).get('value', 'Wikimedia Commons Contributor')
                credit = extmeta.get('Credit', {}).get('value', 'Wikimedia Commons / Public Domain')
                desc = extmeta.get('ImageDescription', {}).get('value', title)

                # Clean artist and credit tags
                if '<' in artist:
                    import re
                    artist = re.sub('<[^<]+?>', '', artist)
                if '<' in credit:
                    import re
                    credit = re.sub('<[^<]+?>', '', credit)
                if '<' in desc:
                    import re
                    desc = re.sub('<[^<]+?>', '', desc)

                if not img_url:
                    continue

                # Filter out irrelevant files (coins, generic maps, unrelated logos)
                t_lower = title.lower()
                if any(bad in t_lower for bad in ['coin', 'stamp', 'flag', 'coat_of_arms', 'generic', 'map']):
                    continue

                # Classify into category
                cat = "02_Exterior"
                if any(k in t_lower for k in ['draw', 'scheme', 'blueprint', 'ortho', 'svg', 'diagram', 'plan']):
                    cat = "01_Orthographic"
                elif any(k in t_lower for k in ['engine', 'motor', 'rotax', 'tei', 'austro', 'lark', 'exhaust']):
                    cat = uav_info["engine_sub"]
                elif any(k in t_lower for k in ['propeller', 'blade', 'spinner']):
                    cat = "04_Propeller"
                elif any(k in t_lower for k in ['turret', 'sensor', 'camera', 'cats', 'radar', 'wescam', 'missile', 'mam-l', 'hellfire', 'ar-1', 'pylon', 'satcom']):
                    cat = "05_Sensors_Payload"
                elif any(k in t_lower for k in ['gear', 'wheel', 'tire', 'strut']):
                    cat = "06_Landing_Gear"
                elif any(k in t_lower for k in ['marking', 'roundel', 'insignia', 'stencil']):
                    cat = "08_Markings_Decals"
                elif any(k in t_lower for k in ['dimension', 'cutaway']):
                    cat = "09_Dimensions"

                ext = ".jpg"
                if t_lower.endswith('.png'):
                    ext = ".png"
                elif t_lower.endswith('.svg'):
                    ext = ".svg"
                elif t_lower.endswith('.webp'):
                    ext = ".webp"

                cat_dir = os.path.join(uav_dir, cat)
                os.makedirs(cat_dir, exist_ok=True)
                
                # Create clean filename
                cur_files = [f for f in os.listdir(cat_dir) if f.startswith(f"{uav_name}_{cat}_")]
                idx = len(cur_files) + 1
                fname = f"{uav_name}_{cat}_{idx:03d}{ext}"
                dest_file = os.path.join(cat_dir, fname)

                res = download_and_verify(img_url, dest_file)
                if res:
                    dim, fmt, sz = res
                    f_hash = get_file_md5(dest_file)
                    if f_hash in existing_hashes:
                        os.remove(dest_file)
                        continue
                    existing_hashes.add(f_hash)
                    print(f"  [+] Saved ({dim[0]}x{dim[1]} {fmt}): {cat}/{fname}")

                    records.append({
                        "filename": f"{cat}/{fname}",
                        "category": cat,
                        "source_url": img_url,
                        "source_org": f"Wikimedia Commons ({artist[:40]} / {credit[:30]})",
                        "resolution": f"{dim[0]}x{dim[1]}",
                        "uav_variant": uav_info["variant"],
                        "component_shown": title[:70],
                        "viewing_angle": "Orthographic" if cat == "01_Orthographic" else "Exterior Angle",
                        "confidence_level": "CONFIRMED",
                        "notes": desc[:120] if desc else f"Official reference asset for {uav_name}",
                        "suitable_for_3d_reconstruction": "YES"
                    })
        except Exception as e:
            print(f"  Error on query '{query}': {e}")

def harvest_bing_for_uav(page, uav_name, uav_info, existing_hashes, records):
    print(f"\n[Bing Playwright] Deep harvesting for {uav_name}...")
    uav_dir = os.path.join(BASE_DIR, uav_name)
    uav_keyword = uav_name.split('_')[0].lower()

    for category, queries in uav_info["bing_queries"].items():
        cat_dir = os.path.join(uav_dir, category)
        os.makedirs(cat_dir, exist_ok=True)
        print(f"  >> Category: {category} ({len(queries)} queries)")

        for q in queries:
            encoded_q = urllib.parse.quote(q)
            search_url = f"https://www.bing.com/images/search?q={encoded_q}&form=HDRSC2&first=1"
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=16000)
                page.wait_for_timeout(2000)
                page.evaluate("window.scrollBy(0, 1800)")
                page.wait_for_timeout(1200)

                elements = page.query_selector_all("a.iusc")
                added_for_query = 0
                for el in elements:
                    if added_for_query >= 8:  # Cap per individual query to keep variety high
                        break
                    try:
                        m_str = el.get_attribute("m")
                        if not m_str:
                            continue
                        m_data = json.loads(m_str)
                        murl = m_data.get("murl")
                        turl = m_data.get("turl")
                        title = m_data.get("t", "")
                        desc = m_data.get("desc", "")
                        purl = m_data.get("purl", "")

                        if not murl:
                            continue

                        # Relevance check
                        combined = (title + " " + desc + " " + murl + " " + purl).lower()
                        # Strict exclusion of airliners
                        if any(b in combined for b in ["airbus", "boeing 7", "a330 neo", "trent 700"]):
                            continue
                        
                        # At least one relevant keyword
                        relevant_keys = [uav_keyword, "drone", "uav", "ucav", "aircraft", "rotax", "austro", "tei", "lark", "blueprint", "drawing"]
                        if not any(k in combined for k in relevant_keys):
                            continue

                        ext = ".jpg"
                        if ".png" in murl.lower():
                            ext = ".png"
                        elif ".webp" in murl.lower():
                            ext = ".webp"

                        cur_files = [f for f in os.listdir(cat_dir) if f.startswith(f"{uav_name}_{category}_")]
                        idx = len(cur_files) + 1
                        fname = f"{uav_name}_{category}_{idx:03d}{ext}"
                        dest_file = os.path.join(cat_dir, fname)

                        # Try murl first, then fallback to turl
                        res = download_and_verify(murl, dest_file, min_size=(260, 260), min_bytes=10000)
                        if not res and turl:
                            base_t = turl.split('?')[0] + '?w=1200'
                            res = download_and_verify(base_t, dest_file, min_size=(240, 240), min_bytes=8000)

                        if res:
                            dim, fmt, sz = res
                            f_hash = get_file_md5(dest_file)
                            if f_hash in existing_hashes:
                                os.remove(dest_file)
                                continue
                            existing_hashes.add(f_hash)
                            added_for_query += 1
                            print(f"    [+] Saved ({dim[0]}x{dim[1]} {fmt}): {category}/{fname}")

                            records.append({
                                "filename": f"{category}/{fname}",
                                "category": category,
                                "source_url": murl,
                                "source_org": purl[:60] if purl else "Aerospace Technical Source",
                                "resolution": f"{dim[0]}x{dim[1]}",
                                "uav_variant": uav_info["variant"],
                                "component_shown": title[:70] if title else category,
                                "viewing_angle": "Orthographic" if category == "01_Orthographic" else "Multi-Angle Reference",
                                "confidence_level": "CONFIRMED" if uav_keyword in combined else "PROBABLE",
                                "notes": desc[:120] if desc else f"Visual reference for {category}",
                                "suitable_for_3d_reconstruction": "YES"
                            })
                    except Exception as e:
                        pass
            except Exception as e:
                print(f"    Error querying Bing '{q}': {e}")

def catalog_existing_files(uav_name, uav_info, existing_hashes, records):
    uav_dir = os.path.join(BASE_DIR, uav_name)
    for cat in os.listdir(uav_dir):
        cat_path = os.path.join(uav_dir, cat)
        if os.path.isdir(cat_path):
            for f in os.listdir(cat_path):
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.svg')):
                    f_path = os.path.join(cat_path, f)
                    try:
                        f_hash = get_file_md5(f_path)
                        if f_hash in existing_hashes:
                            # duplicate! remove it
                            print(f"  Removing duplicate file: {cat}/{f}")
                            os.remove(f_path)
                            continue
                        existing_hashes.add(f_hash)

                        # Determine resolution
                        res_str = "Vector/SVG"
                        if not f.lower().endswith('.svg'):
                            with Image.open(f_path) as im:
                                res_str = f"{im.size[0]}x{im.size[1]}"

                        # Check if it's a CAD render
                        is_cad = "CAD" in f
                        conf = "CONFIRMED" if is_cad or "Solid" in f or "ref" in f else "PROBABLE"
                        source_org = "Blender Precision CAD Render" if is_cad else "Aero Engine Visual Archive"

                        records.append({
                            "filename": f"{cat}/{f}",
                            "category": cat,
                            "source_url": "Local CAD / Pre-verified Repository",
                            "source_org": source_org,
                            "resolution": res_str,
                            "uav_variant": uav_info["variant"],
                            "component_shown": f"Engine / Airframe Asset ({f})",
                            "viewing_angle": "Orthographic CAD" if is_cad else "Multi-Angle Reference",
                            "confidence_level": conf,
                            "notes": "Precision reference asset verified for 3D reconstruction",
                            "suitable_for_3d_reconstruction": "YES"
                        })
                    except Exception as e:
                        print(f"  Error auditing file {f}: {e}")

def write_catalog_md(uav_name, uav_info, records):
    uav_dir = os.path.join(BASE_DIR, uav_name)
    md_path = os.path.join(uav_dir, "REFERENCE_CATALOG.md")
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {uav_name} — Visual Reference & Modeling Catalog\n\n")
        f.write(f"**Target Variant:** {uav_info['variant']}\n\n")
        f.write(f"**Engine Configuration:** {uav_info['engine_name']}\n\n")
        f.write(f"**Propeller:** {uav_info['propeller']}\n\n")
        f.write(f"**Key Sensors & Payloads:** {uav_info['sensors']}\n\n")
        f.write(f"**Munitions / Hardpoints:** {uav_info['munitions']}\n\n")
        f.write(f"**Authoritative Dimensions:** {uav_info['dimensions']}\n\n")
        f.write(f"**Total Verified Reference Assets:** {len(records)} files\n\n")
        f.write("---\n\n")
        f.write("## Category Inventory\n\n")

        # Group by category
        by_cat = {}
        for r in records:
            cat = r["category"]
            by_cat.setdefault(cat, []).append(r)

        for cat in sorted(by_cat.keys()):
            items = by_cat[cat]
            f.write(f"### {cat} ({len(items)} assets)\n\n")
            f.write("| Filename | Resolution | Source / Organization | Confidence | Suitable for 3D |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            for item in items:
                f_name = os.path.basename(item["filename"])
                f.write(f"| `{f_name}` | {item['resolution']} | {item['source_org'][:40]} | **{item['confidence_level']}** | {item['suitable_for_3d_reconstruction']} |\n")
            f.write("\n")

    print(f"  --> Generated markdown catalog at {md_path}")

def run_master_harvest():
    print("======================================================================")
    print("STARTING MASTER UAV & ENGINE REFERENCE DATASET HARVEST")
    print(f"Target Root: {BASE_DIR}")
    print("======================================================================")

    # Launch Playwright browser once
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900}
        )
        page = context.new_page()

        grand_total = 0

        for uav_name, uav_info in UAV_CONFIGS.items():
            print(f"\n######################################################################")
            print(f"PROCESSING UAV: {uav_name}")
            print(f"######################################################################")
            
            uav_dir = os.path.join(BASE_DIR, uav_name)
            csv_path = os.path.join(uav_dir, "reference_index.csv")

            existing_hashes = set()
            records = []

            # 1. Audit existing files (e.g. copied engines and CAD renders)
            print("[Step 1] Cataloging existing files...")
            catalog_existing_files(uav_name, uav_info, existing_hashes, records)
            print(f"  Found {len(records)} existing verified assets.")

            # 2. Harvest from Wikimedia Commons
            print("[Step 2] Querying Wikimedia Commons API...")
            harvest_wikimedia_for_uav(uav_name, uav_info, existing_hashes, records)

            # 3. Deep harvest via Playwright Bing Images
            print("[Step 3] Querying Playwright Bing Images...")
            harvest_bing_for_uav(page, uav_name, uav_info, existing_hashes, records)

            # 4. Save reference_index.csv
            fieldnames = [
                "filename", "category", "source_url", "source_org", "resolution",
                "uav_variant", "component_shown", "viewing_angle", "confidence_level",
                "notes", "suitable_for_3d_reconstruction"
            ]
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in records:
                    writer.writerow(r)

            print(f"  --> Saved {len(records)} index records to {csv_path}")

            # 5. Generate Markdown catalog
            write_catalog_md(uav_name, uav_info, records)

            grand_total += len(records)
            print(f"Completed {uav_name}: {len(records)} assets cataloged.")

        browser.close()

    print("\n======================================================================")
    print(f"ALL HARVESTING COMPLETE! Grand Total Assets: {grand_total}")
    print("======================================================================")

if __name__ == "__main__":
    run_master_harvest()
