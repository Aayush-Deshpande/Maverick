import os
import sys
import time
import json
import csv
import base64
import urllib.request
import urllib.parse
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

root_images_dir = str(Path(__file__).resolve().parent.parent / "assets" / "model_images")

UAV_SPEC_DATA = {
    "Bayraktar_TB2": {
        "variant": "Bayraktar TB2 Block 2 (Pusher MALE UCAV)",
        "engine_sub": "03_Engine_Rotax_912iS",
        "engine_name": "Rotax 912 iS Sport (100 hp)",
        "propeller": "2-blade variable pitch wood/composite pusher",
        "sensors": "WESCAM MX-15D / Aselsan CATS EO/IR turret, dorsal SATCOM / C-band datalink",
        "munitions": "4x Roketsan MAM-L / MAM-C laser-guided smart micro-munitions",
        "dimensions": "Wingspan: 12.0m, Length: 6.5m, Height: 2.2m, MTOW: 700kg",
        "queries": {
            "01_Orthographic": [
                "Bayraktar TB2 3 view drawing",
                "Bayraktar TB2 blueprint",
                "Bayraktar TB2 orthographic drawing",
                "Bayraktar TB2 dimensional drawing"
            ],
            "02_Exterior": [
                "Bayraktar TB2 high resolution in flight",
                "Bayraktar TB2 ground view high quality",
                "Bayraktar TB2 airshow walkaround",
                "Bayraktar TB2 takeoff runway"
            ],
            "03_Engine_Rotax_912iS": [
                "Bayraktar TB2 engine bay open",
                "Bayraktar TB2 Rotax engine",
                "Bayraktar TB2 engine cowling exhaust",
                "Rotax 912 iS Sport aero engine high resolution"
            ],
            "04_Propeller": [
                "Bayraktar TB2 pusher propeller blades",
                "Bayraktar TB2 propeller hub"
            ],
            "05_Sensors_Payload": [
                "Bayraktar TB2 WESCAM MX-15D turret",
                "Bayraktar TB2 Aselsan CATS camera",
                "Bayraktar TB2 MAM-L missile pylon"
            ],
            "06_Landing_Gear": [
                "Bayraktar TB2 landing gear nose wheel",
                "Bayraktar TB2 main landing gear composite strut"
            ],
            "07_Surface_Textures": [
                "Bayraktar TB2 composite skin panel lines close up",
                "Bayraktar TB2 carbon fiber surface"
            ],
            "08_Markings_Decals": [
                "Bayraktar TB2 national insignia markings decals",
                "Bayraktar TB2 tail number roundel"
            ],
            "09_Dimensions": [
                "Bayraktar TB2 official dimensions Baykar specifications",
                "Bayraktar TB2 technical cutaway"
            ],
            "10_CAD_3D": [
                "Bayraktar TB2 3D CAD model wireframe",
                "Bayraktar TB2 3D mesh"
            ],
            "11_Technical_Documents": [
                "Bayraktar TB2 brochure PDF Baykar",
                "Bayraktar TB2 technical specifications datasheet"
            ]
        }
    },
    "MQ1_Predator": {
        "variant": "General Atomics MQ-1B Predator (Inverted V-tail, Bulbous Nose)",
        "engine_sub": "03_Engine_Rotax_914F",
        "engine_name": "Rotax 914F Turbocharged (115 hp)",
        "propeller": "2-blade variable pitch pusher propeller",
        "sensors": "Raytheon AN/AAS-52 Multi-spectral Targeting System (MTS-A), Ku-band SATCOM radome",
        "munitions": "2x AGM-114 Hellfire air-to-ground missiles",
        "dimensions": "Wingspan: 14.8m / 16.8m, Length: 8.22m, Height: 2.1m, MTOW: 1020kg",
        "queries": {
            "01_Orthographic": [
                "MQ-1 Predator 3 view drawing",
                "MQ-1B Predator blueprint",
                "MQ-1 Predator orthographic diagram"
            ],
            "02_Exterior": [
                "MQ-1 Predator high resolution in flight USAF",
                "MQ-1B Predator airshow ground walkaround",
                "MQ-1 Predator taxi runway"
            ],
            "03_Engine_Rotax_914F": [
                "MQ-1 Predator Rotax 914 engine bay",
                "MQ-1 Predator turbocharger exhaust",
                "Rotax 914F aircraft engine high resolution"
            ],
            "04_Propeller": [
                "MQ-1 Predator pusher propeller hub",
                "MQ-1 Predator propeller blades"
            ],
            "05_Sensors_Payload": [
                "MQ-1 Predator MTS-A EO/IR sensor ball",
                "MQ-1 Predator AGM-114 Hellfire missile pylon",
                "MQ-1 Predator SATCOM radome nose"
            ],
            "06_Landing_Gear": [
                "MQ-1 Predator retractable landing gear nose wheel",
                "MQ-1 Predator main gear strut wheel well"
            ],
            "07_Surface_Textures": [
                "MQ-1 Predator panel lines rivets composite skin close up",
                "MQ-1 Predator weathered paint"
            ],
            "08_Markings_Decals": [
                "MQ-1 Predator USAF markings serial numbers stencils",
                "MQ-1 Predator rescue markings warning labels"
            ],
            "09_Dimensions": [
                "MQ-1 Predator dimensions General Atomics datasheet",
                "MQ-1 Predator technical cutaway diagram"
            ],
            "10_CAD_3D": [
                "MQ-1 Predator 3D model CAD wireframe",
                "MQ-1 Predator 3D mesh"
            ],
            "11_Technical_Documents": [
                "MQ-1B Predator technical manual USAF",
                "General Atomics Predator datasheet PDF"
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
        "queries": {
            "01_Orthographic": [
                "IAI Heron Mk II 3 view drawing",
                "IAI Heron blueprint",
                "Heron Mk II orthographic schematic"
            ],
            "02_Exterior": [
                "IAI Heron Mk II high resolution flight",
                "IAI Heron Mk 2 Singapore Airshow Paris Airshow",
                "IAI Heron Mk II ground display"
            ],
            "03_Engine_Rotax_915iS": [
                "IAI Heron Mk II engine installation Rotax",
                "Rotax 915 iS aero engine high resolution",
                "Rotax 915 iS turbocharger intercooler"
            ],
            "04_Propeller": [
                "IAI Heron 3 blade pusher propeller",
                "IAI Heron Mk II propeller spinner"
            ],
            "05_Sensors_Payload": [
                "IAI Heron ELTA radar canoe belly",
                "IAI Heron EO/IR turret payload",
                "IAI Heron SATCOM dome"
            ],
            "06_Landing_Gear": [
                "IAI Heron retractable landing gear",
                "IAI Heron main landing gear nose wheel"
            ],
            "07_Surface_Textures": [
                "IAI Heron composite skin panel lines close up",
                "IAI Heron paint texture details"
            ],
            "08_Markings_Decals": [
                "IAI Heron markings national roundels stencils",
                "IAI Heron registration decals"
            ],
            "09_Dimensions": [
                "IAI Heron Mk II dimensions specifications IAI",
                "IAI Heron Mk II cutaway drawing"
            ],
            "10_CAD_3D": [
                "IAI Heron 3D model CAD",
                "IAI Heron 3D mesh wireframe"
            ],
            "11_Technical_Documents": [
                "IAI Heron Mk II brochure PDF IAI",
                "IAI Heron datasheet specifications"
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
        "queries": {
            "01_Orthographic": [
                "TAI Anka 3 view drawing",
                "TAI Anka-S blueprint",
                "TAI Anka orthographic drawing"
            ],
            "02_Exterior": [
                "TAI Anka high resolution in flight",
                "TAI Anka TEKNOFEST IDEF ground walkaround",
                "TAI Anka-S runway display"
            ],
            "03_Engine_TEI_PD170": [
                "TAI Anka TEI PD170 engine bay",
                "TEI PD170 turbodiesel engine high resolution",
                "TEI PD170 twin turbo exhaust"
            ],
            "04_Propeller": [
                "TAI Anka 3 blade pusher propeller",
                "TAI Anka propeller hub spinner"
            ],
            "05_Sensors_Payload": [
                "TAI Anka Aselsan CATS EO/IR turret",
                "TAI Anka SATCOM nose radome",
                "TAI Anka MAM-L missile pylon"
            ],
            "06_Landing_Gear": [
                "TAI Anka retractable landing gear",
                "TAI Anka nose gear main strut wheel"
            ],
            "07_Surface_Textures": [
                "TAI Anka composite skin rivets panel lines close up",
                "TAI Anka carbon fiber panels"
            ],
            "08_Markings_Decals": [
                "TAI Anka Turkish Air Force roundels serial numbers",
                "TAI Anka warning markings stencils"
            ],
            "09_Dimensions": [
                "TAI Anka official dimensions TAI specifications",
                "TAI Anka technical cutaway"
            ],
            "10_CAD_3D": [
                "TAI Anka 3D model CAD",
                "TAI Anka 3D mesh wireframe"
            ],
            "11_Technical_Documents": [
                "TAI Anka brochure PDF Turkish Aerospace",
                "TAI Anka datasheet specifications"
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
        "queries": {
            "01_Orthographic": [
                "TAPAS BH 201 3 view drawing",
                "Rustom II 3 view drawing",
                "TAPAS BH-201 blueprint orthographic"
            ],
            "02_Exterior": [
                "TAPAS BH 201 high resolution Aero India",
                "DRDO TAPAS-BH-201 flight test",
                "Rustom II drone ground walkaround"
            ],
            "03_Engine_Austro_E4": [
                "TAPAS BH 201 Austro engine nacelle",
                "TAPAS BH-201 engine cowling open",
                "Austro Engine E4 AE330 aircraft engine high resolution"
            ],
            "04_Propeller": [
                "TAPAS BH 201 MT propeller spinner",
                "Rustom II tractor propeller blades"
            ],
            "05_Sensors_Payload": [
                "TAPAS BH 201 BEL EO/IR sensor ball",
                "TAPAS BH-201 SAR radar canoe SATCOM dome"
            ],
            "06_Landing_Gear": [
                "TAPAS BH 201 landing gear nose wheel",
                "TAPAS BH-201 nacelle main gear retraction"
            ],
            "07_Surface_Textures": [
                "TAPAS BH 201 composite airframe panel lines close up",
                "DRDO TAPAS paint surface texture"
            ],
            "08_Markings_Decals": [
                "TAPAS BH 201 Indian Air Force roundels DRDO markings",
                "TAPAS BH-201 warning labels stencils"
            ],
            "09_Dimensions": [
                "TAPAS BH 201 dimensions DRDO ADE specifications",
                "Rustom II technical cutaway drawing"
            ],
            "10_CAD_3D": [
                "TAPAS BH 201 3D model CAD",
                "Rustom II 3D mesh wireframe"
            ],
            "11_Technical_Documents": [
                "TAPAS BH-201 brochure DRDO Aero India",
                "TAPAS BH 201 technical datasheet"
            ]
        }
    },
    "CASC_CH4": {
        "variant": "CASC CH-4B / CH-4C Heavy Fuel Variant (Pusher MALE UCAV)",
        "engine_sub": "03_Engine_Lark_HFE",
        "engine_name": "Lark HFE (Heavy Fuel Engine) (150 hp)",
        "propeller": "3-blade pusher propeller with ground-adjustable / variable pitch",
        "sensors": "4-in-1 EO/IR sensor turret, synthetic aperture radar pod, nose SATCOM dome",
        "munitions": "4x underwing hardpoints: AR-1 laser-guided missiles, AKD-10, FT-9 glide bombs",
        "dimensions": "Wingspan: 18.0m, Length: 8.5m, Height: 3.4m, MTOW: 1330kg",
        "queries": {
            "01_Orthographic": [
                "CH-4 drone 3 view drawing",
                "CASC Rainbow 4 blueprint",
                "CH-4 UAV orthographic drawing"
            ],
            "02_Exterior": [
                "CASC CH-4 drone high resolution in flight",
                "CH-4B Rainbow Zhuhai Airshow walkaround",
                "CH-4 UCAV runway ground display"
            ],
            "03_Engine_Lark_HFE": [
                "CH-4 drone heavy fuel engine Lark",
                "Lark HFE heavy fuel engine high resolution",
                "CH-4 engine bay exhaust cowling"
            ],
            "04_Propeller": [
                "CH-4 drone 3 blade pusher propeller",
                "CH-4 UAV propeller hub"
            ],
            "05_Sensors_Payload": [
                "CH-4 drone EO/IR sensor turret",
                "CH-4 drone AR-1 missile pylon weapons",
                "CH-4 SATCOM dome radome"
            ],
            "06_Landing_Gear": [
                "CH-4 drone landing gear nose gear",
                "CH-4 UAV main gear strut"
            ],
            "07_Surface_Textures": [
                "CH-4 drone composite skin panel lines close up",
                "CH-4 UAV grey paint weathering"
            ],
            "08_Markings_Decals": [
                "CH-4 drone markings serial numbers stencils",
                "Rainbow-4 warning markings rescue decals"
            ],
            "09_Dimensions": [
                "CASC CH-4 official dimensions CASC specifications",
                "CH-4 drone technical cutaway drawing"
            ],
            "10_CAD_3D": [
                "CH-4 drone 3D model CAD",
                "CH-4 UAV 3D mesh wireframe"
            ],
            "11_Technical_Documents": [
                "CASC CH-4 brochure PDF Zhuhai Airshow",
                "CH-4 drone technical datasheet"
            ]
        }
    }
}

def download_asset(url, dest_path):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read()
            if len(data) > 12000:
                with open(dest_path, "wb") as f:
                    f.write(data)
                # Verify with PIL
                try:
                    with Image.open(dest_path) as im:
                        if im.size[0] >= 180 and im.size[1] >= 180:
                            return im.size, im.format, len(data)
                        else:
                            os.remove(dest_path)
                            return None
                except:
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    return None
    except:
        pass
    return None

def run_uav_collection():
    print("======================================================================")
    print("STARTING AUTOMATED MASTER UAV REFERENCE DATASET HARVEST")
    print("Target Root: " + root_images_dir)
    print("======================================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for uav_name, uav_info in UAV_SPEC_DATA.items():
            print(f"\n=======================================================")
            print(f"COLLECTING DATASET FOR: {uav_name}")
            print(f"Variant: {uav_info['variant']}")
            print(f"Engine: {uav_info['engine_name']}")
            print(f"=======================================================")

            uav_dir = os.path.join(root_images_dir, uav_name)
            csv_path = os.path.join(uav_dir, "reference_index.csv")

            # Initialize index
            index_records = []
            downloaded_urls = set()

            for category, query_list in uav_info["queries"].items():
                cat_dir = os.path.join(uav_dir, category)
                os.makedirs(cat_dir, exist_ok=True)
                print(f"\n  >> Category: {category} ({len(query_list)} queries)")

                cat_count = 0
                for q in query_list:
                    search_url = f"https://www.bing.com/images/search?q={urllib.parse.quote(q)}&form=HDRSC2&first=1"
                    try:
                        page.goto(search_url, wait_until="domcontentloaded", timeout=18000)
                        time.sleep(1.5)
                        page.evaluate("window.scrollBy(0, 1000)")
                        time.sleep(1)

                        img_elements = page.query_selector_all("a.iusc")
                        for el in img_elements:
                            try:
                                m_str = el.get_attribute("m")
                                if not m_str:
                                    continue
                                m_data = json.loads(m_str)
                                img_url = m_data.get("murl")
                                title = m_data.get("t", "")
                                desc = m_data.get("desc", "")
                                p_url = m_data.get("purl", "")

                                if not img_url or img_url in downloaded_urls:
                                    continue

                                # Relevance filter
                                combined = (title + " " + desc + " " + img_url).lower()
                                if "airbus a330" in combined or "boeing 777" in combined:
                                    continue

                                downloaded_urls.add(img_url)

                                ext = ".jpg"
                                if ".png" in img_url.lower():
                                    ext = ".png"
                                elif ".webp" in img_url.lower():
                                    ext = ".webp"

                                cat_count += 1
                                filename = f"{uav_name}_{category}_{cat_count:03d}{ext}"
                                dest_file = os.path.join(cat_dir, filename)

                                res = download_asset(img_url, dest_file)
                                if res:
                                    dim, fmt, sz = res
                                    print(f"    [+] Saved ({dim[0]}x{dim[1]}): {filename}")
                                    index_records.append({
                                        "filename": f"{category}/{filename}",
                                        "category": category,
                                        "source_url": img_url,
                                        "source_org": p_url[:60] if p_url else "Web Aerospace Source",
                                        "resolution": f"{dim[0]}x{dim[1]}",
                                        "uav_variant": uav_info["variant"],
                                        "component_shown": title[:60] if title else category,
                                        "viewing_angle": "Reference Angle",
                                        "confidence_level": "CONFIRMED" if any(k in title.lower() for k in [uav_name.lower().split('_')[0], "drone", "uav", "engine"]) else "PROBABLE",
                                        "notes": desc[:100] if desc else "High-fidelity visual reference",
                                        "suitable_for_3d_reconstruction": "YES"
                                    })
                            except:
                                pass
                    except Exception as e:
                        print(f"    Error querying '{q}': {e}")

            # Write reference_index.csv
            fieldnames = [
                "filename", "category", "source_url", "source_org", "resolution",
                "uav_variant", "component_shown", "viewing_angle", "confidence_level",
                "notes", "suitable_for_3d_reconstruction"
            ]
            with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for rec in index_records:
                    writer.writerow(rec)

            print(f"  --> Saved reference index with {len(index_records)} records to {csv_path}")

        browser.close()

if __name__ == "__main__":
    run_uav_collection()
