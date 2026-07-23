"""
EcoTech Marine XR15w G5 Pro — BLE HTTP Bridge
Kullanım:
    python3 test.py          # server modu (HA için)
    python3 test.py on       # manuel aç
    python3 test.py off      # manuel kapat
"""
import asyncio
import struct
import sys
from datetime import datetime
from bleak import BleakClient
from aiohttp import web

ADDRESS  = "84:25:3F:76:67:4C"
TX_FINAL = "01ff0104-ba5e-f4ee-5ca1-eb1e5e4b1ce0"
RX_DATA  = "01ff0101-ba5e-f4ee-5ca1-eb1e5e4b1ce0"
RX_FINAL = "01ff0102-ba5e-f4ee-5ca1-eb1e5e4b1ce0"

ATTR_SCHEDULE1           = 500
ATTR_SCHEDULE1_INTENSITY = 511
ATTR_SCHEDULE_PLAYBACK   = 510
SCHED_RESUME = bytes([1, 0])
CHANNELS_42 = [21, 23, 18, 17, 19, 20, 31, 32, 22, 16, 1, 101, 100]

CRC16_TABLE = [
    0, 4129, 8258, 12387, 16516, 20645, 24774, 28903,
    -32504, -28375, -24246, -20117, -15988, -11859, -7730, -3601,
    4657, 528, 12915, 8786, 21173, 17044, 29431, 25302,
    -27847, -31976, -19589, -23718, -11331, -15460, -3073, -7202,
    9314, 13379, 1056, 5121, 25830, 29895, 17572, 21637,
    -23190, -19125, -31448, -27383, -6674, -2609, -14932, -10867,
    13907, 9842, 5649, 1584, 30423, 26358, 22165, 18100,
    -18597, -22662, -26855, -30920, -2081, -6146, -10339, -14404,
    18628, 22757, 26758, 30887, 2112, 6241, 10242, 14371,
    -13876, -9747, -5746, -1617, -30392, -26263, -22262, -18133,
    23285, 19156, 31415, 27286, 6769, 2640, 14899, 10770,
    -9219, -13348, -1089, -5218, -25735, -29864, -17605, -21734,
    27814, 31879, 19684, 23749, 11298, 15363, 3168, 7233,
    -4690, -625, -12820, -8755, -21206, -17141, -29336, -25271,
    32407, 28342, 24277, 20212, 15891, 11826, 7761, 3696,
    -97, -4162, -8227, -12292, -16613, -20678, -24743, -28808,
    -28280, -32343, -20022, -24085, -12020, -16083, -3762, -7825,
    4224, 161, 12482, 8419, 20484, 16421, 28742, 24679,
    -31815, -27752, -23557, -19494, -15555, -11492, -7297, -3234,
    689, 4752, 8947, 13010, 16949, 21012, 25207, 29270,
    -18966, -23093, -27224, -31351, -2706, -6833, -10964, -15091,
    13538, 9411, 5280, 1153, 29798, 25671, 21540, 17413,
    -22565, -18438, -30823, -26696, -6305, -2178, -14563, -10436,
    9939, 14066, 1681, 5808, 26199, 30326, 17941, 22068,
    -9908, -13971, -1778, -5841, -26168, -30231, -18038, -22101,
    22596, 18533, 30726, 26663, 6336, 2273, 14466, 10403,
    -13443, -9380, -5313, -1250, -29703, -25640, -21573, -17510,
    19061, 23124, 27191, 31254, 2801, 6864, 10931, 14994,
    -722, -4849, -8852, -12979, -16982, -21109, -25112, -29239,
    31782, 27655, 23652, 19525, 15522, 11395, 7392, 3265,
    -4321, -194, -12451, -8324, -20581, -16454, -28711, -24584,
    28183, 32310, 20053, 24180, 11923, 16050, 3793, 7920,
]

def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc = ((crc << 8) ^ (CRC16_TABLE[((b ^ (crc >> 8)) & 0xFF)] & 0xFFFF)) & 0xFFFF
    return crc

def make_item_42(time_min, flags, ch_vals=None):
    cv = {v: 0 for v in CHANNELS_42}
    if ch_vals:
        cv.update(ch_vals)
    prim = b"".join(bytes([v]) + struct.pack("<H", cv[v]) for v in CHANNELS_42)
    return struct.pack("<H", time_min) + bytes([flags]) + prim

def mk_set_v24(sub, slots, msg_id):
    d = struct.pack("<H", ATTR_SCHEDULE1) + bytes([sub, len(slots), 42]) + b"".join(slots)
    body = bytes([0xDE, 24]) + struct.pack("<H", msg_id) + b"\x00\x00" + struct.pack("<H", len(d)) + d
    return b"\x02" + body + struct.pack("<H", crc16(body))

def mk_simple_set(attr_id, value, msg_id):
    d = struct.pack("<H", attr_id) + bytes([0, 1, len(value)]) + value
    body = bytes([0xDE, 24]) + struct.pack("<H", msg_id) + b"\x00\x00" + struct.pack("<H", len(d)) + d
    return b"\x02" + body + struct.pack("<H", crc16(body))

def mk_get(attr_id, msg_id, extra=b""):
    """GET (opcode 0x17) — cihazdan attribute değerini oku."""
    d = struct.pack("<H", attr_id) + extra
    body = bytes([0xDE, 0x17]) + struct.pack("<H", msg_id) + b"\x00\x00" + struct.pack("<H", len(d)) + d
    return b"\x02" + body + struct.pack("<H", crc16(body))

def mk_playback(action, msg_id):
    d = struct.pack("<H", ATTR_SCHEDULE_PLAYBACK) + bytes([0, 1, len(action)]) + action
    body = bytes([0xDE, 0x18]) + struct.pack("<H", msg_id) + b"\x00\x00" + struct.pack("<H", len(d)) + d
    return b"\x02" + body + struct.pack("<H", crc16(body))

def build_original_schedule():
    """
    Mercan + balık schedule (UV/mavi ağırlıklı, gün simülasyonu)
    Kanal ID'leri: UV=21, Violet=23, RoyalBlue=18, Blue=17,
                   Green=19, Red=20, WarmWhite=22, CoolWhite=16,
                   MoonlightBlue=32, Brightness=1
    Zaman: dakika cinsinden (örn. 06:00 = 360)
    """
    def S(t, f, channels=None):
        return make_item_42(t, f, channels or {})

    slots = [
        # 00:00 — gece karanlığı (gün başlangıcı)
        S(0,    0x01, {32:150, 17:50, 1:200}),
        # 06:00 — yumuşak uyanış, sadece gece mavisi
        S(360,  0x01, {32:300, 1:400}),
        # 08:00 — kademeli artış
        S(480,  0x01, {21:200, 23:300, 18:400, 17:300,
                       19:100, 20:50,  22:100, 16:100, 32:100, 1:600}),
        # 10:00 — sabah
        S(600,  0x01, {21:600, 23:700, 18:800, 17:600,
                       19:200, 20:100, 22:200, 16:200, 1:800}),
        # 12:00 — tepe (öğle)
        S(720,  0x01, {21:800, 23:900, 18:1000, 17:800,
                       19:300, 20:150, 22:300, 16:300, 1:1000}),
        # 14:00 — tepe devam
        S(840,  0x01, {21:800, 23:900, 18:1000, 17:800,
                       19:300, 20:150, 22:300, 16:300, 1:1000}),
        # 16:00 — öğleden sonra, kademeli azalış
        S(960,  0x01, {21:600, 23:700, 18:800, 17:600,
                       19:200, 20:100, 22:200, 16:200, 1:800}),
        # 18:00 — akşam başlangıcı
        S(1080, 0x01, {21:200, 23:300, 18:400, 17:300,
                       19:100, 20:50,  22:100, 16:100, 32:100, 1:600}),
        # 20:00 — akşam, mavi/gece tonu
        S(1200, 0x01, {18:100, 17:100, 32:300, 1:400}),
        # 22:00 — gece modu
        S(1320, 0x01, {32:150, 1:200}),
        # 23:30 — neredeyse karanlık
        S(1410, 0x01, {32:50, 1:100}),
    ]
    slots += [bytes(42)] * (25 - len(slots))
    return slots

async def _safe_connect(timeout=30, retries=3):
    for attempt in range(1, retries + 1):
        try:
            client = BleakClient(ADDRESS, timeout=timeout)
            await client.connect()
            await asyncio.sleep(1.5)  # BlueZ servis discovery için bekle
            # Servisler hazır mı kontrol et
            tx = client.services.get_characteristic(TX_FINAL)
            if tx is None:
                found = [s.uuid for s in client.services]
                print(f"  Bulunan servisler: {found or 'HİÇBİRİ (boş GATT listesi)'}")
                raise RuntimeError("TX karakteristiği bulunamadı")
            print(f"  Bağlandı (deneme {attempt})")
            return client
        except Exception as e:
            print(f"  Bağlantı denemesi {attempt} başarısız: {e}")
            try:
                await client.disconnect()
            except Exception:
                pass
            if attempt < retries:
                await asyncio.sleep(3)
    raise RuntimeError(f"{retries} denemede bağlantı kurulamadı")

async def write_schedule(slots, intensity=500, label=""):
    BATCH = 8
    print(f"\n{'='*50}")
    print(f"{label}")
    print(f"{'='*50}")
    client = await _safe_connect(timeout=30)
    try:
        def noop(s, d): pass
        try:
            await client.start_notify(RX_DATA,  noop)
            await client.start_notify(RX_FINAL, noop)
        except Exception as e:
            print(f"  notify warning: {e}")
        tx = client.services.get_characteristic(TX_FINAL)
        async def send(p):
            await client._backend.write_gatt_char(tx, bytearray(p), False)
        msg = 1
        for start in range(0, 25, BATCH):
            end   = min(start + BATCH, 25)
            chunk = slots[start:end]
            pkt   = mk_set_v24(start, chunk, msg)
            print(f"  sub={start:2d} count={end-start} ({len(pkt)}B) → yazılıyor...")
            await send(pkt)
            await asyncio.sleep(0.3)
            msg += 1
        await send(mk_simple_set(ATTR_SCHEDULE1_INTENSITY, struct.pack("<H", intensity), msg))
        await asyncio.sleep(0.3); msg += 1
        await send(mk_playback(SCHED_RESUME, msg))
        await asyncio.sleep(1.0)
        print(f"\n  ✓ Tamamlandı!")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

async def turn_off():
    await write_schedule([bytes(42)] * 25, intensity=500, label="IŞIĞI SÖNDÜR")
    print("  → Işık söndürüldü!")

async def turn_on():
    await write_schedule(build_original_schedule(), intensity=500, label="IŞIĞI AÇ")
    print("  → Işık açıldı!")

def build_flat_schedule(ch_vals):
    """Aynı renk karışımını orijinal 11 zaman noktasının hepsine yazar."""
    times = [0, 360, 480, 600, 720, 840, 960, 1080, 1200, 1320, 1410]
    slots = [make_item_42(t, 0x01, ch_vals) for t in times]
    slots += [bytes(42)] * (25 - len(slots))
    return slots

async def apply_recipe(ch_vals, intensity):
    await write_schedule(build_flat_schedule(ch_vals), intensity=intensity,
                         label=f"RENK TARİFİ UYGULA (intensity={intensity})")
    print("  → Tarif uygulandı!")

async def write_intensity(intensity, label=""):
    """Sadece intensity + resume yaz — schedule'a dokunmadan (2 paket)."""
    print(f"\n{'='*50}\n{label}\n{'='*50}")
    client = await _safe_connect(timeout=30)
    try:
        def noop(s, d): pass
        try:
            await client.start_notify(RX_DATA,  noop)
            await client.start_notify(RX_FINAL, noop)
        except Exception as e:
            print(f"  notify warning: {e}")
        tx = client.services.get_characteristic(TX_FINAL)
        async def send(p):
            await client._backend.write_gatt_char(tx, bytearray(p), False)
        await send(mk_simple_set(ATTR_SCHEDULE1_INTENSITY, struct.pack("<H", intensity), 1))
        await asyncio.sleep(0.3)
        await send(mk_playback(SCHED_RESUME, 2))
        await asyncio.sleep(1.0)
        print("  ✓ Tamamlandı!")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

# ── HTTP server ───────────────────────────────────────────────────
_state = "unknown"
_last_result = {"ok": None, "label": None, "error": None, "at": None}
_ble_lock = asyncio.Lock()

async def _run_ble(coro, label=""):
    global _last_result
    async with _ble_lock:
        _last_result = {"ok": None, "label": label, "error": None,
                        "at": datetime.now().isoformat(timespec="seconds")}
        try:
            await coro
            _last_result = {"ok": True, "label": label, "error": None,
                            "at": datetime.now().isoformat(timespec="seconds")}
        except Exception as e:
            print(f"BLE hata: {e}")
            _last_result = {"ok": False, "label": label, "error": str(e),
                            "at": datetime.now().isoformat(timespec="seconds")}

async def handle_on(request):
    global _state
    _state = "on"
    asyncio.create_task(_run_ble(turn_on(), "on"))
    return web.json_response({"state": "on"})

async def handle_off(request):
    global _state
    _state = "off"
    asyncio.create_task(_run_ble(turn_off(), "off"))
    return web.json_response({"state": "off"})

async def handle_status(request):
    return web.json_response({"state": _state, "last_result": _last_result})

async def read_attr(attr_id, extra=b"", wait=8.0):
    """GET gönder, cihazın notification cevaplarını topla, ham bytes döndür."""
    client = await _safe_connect(timeout=30)
    received = []
    try:
        def on_note(char, data):
            uuid = getattr(char, "uuid", str(char))
            tag = "DATA" if str(uuid).startswith("01ff0101") else "FINAL"
            received.append((tag, bytes(data)))
        await client.start_notify(RX_DATA, on_note)
        await client.start_notify(RX_FINAL, on_note)
        tx = client.services.get_characteristic(TX_FINAL)
        pkt = mk_get(attr_id, 1, extra)
        print(f"  GET attr={attr_id} extra={extra.hex() or '-'} gönderiliyor: {pkt.hex()}")
        await client._backend.write_gatt_char(tx, bytearray(pkt), False)
        await asyncio.sleep(wait)
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass
    return received

async def handle_dump(request):
    """GET /dump?attr=511 — cihazdan oku ve ham cevabı JSON olarak döndür."""
    try:
        attr = int(request.query.get("attr", "500"))
        variant = int(request.query.get("variant", "0"))
    except ValueError:
        return web.json_response({"error": "bad params"}, status=400)
    # v0: attr only            v3: sub=0, count=1 (SET'in alan düzeni)
    # v1: attr + 0x00          v4: sub=0, count=25 (tüm slotlar?)
    # v2: attr + 0x0000        v5: sub=0, count=1, len=0
    variants = [b"", b"\x00", b"\x00\x00", b"\x00\x01", b"\x00\x19", b"\x00\x01\x00"]
    extra = variants[variant % len(variants)]
    async with _ble_lock:
        try:
            packets = await read_attr(attr, extra)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    dump = [f"{tag}:{p.hex()}" for tag, p in packets]
    for i, h in enumerate(dump):
        print(f"  RX[{i}]: {h}")
    return web.json_response(
        {"attr": attr, "variant": variant, "count": len(dump), "packets": dump}
    )

async def handle_apply(request):
    """POST /apply — JSON: {"channels": {"21": 800, ...}, "intensity": 1000}"""
    global _state
    try:
        data = await request.json()
        ch_vals = {int(k): int(v) for k, v in data.get("channels", {}).items()}
        intensity = int(data.get("intensity", 500))
    except (ValueError, TypeError):
        return web.json_response({"error": "bad request"}, status=400)
    _state = "on" if intensity > 0 else "off"
    asyncio.create_task(_run_ble(apply_recipe(ch_vals, intensity), f"apply (intensity {intensity})"))
    return web.json_response({"state": _state, "channels": ch_vals, "intensity": intensity})

async def handle_intensity(request):
    """GET /intensity/{value} — schedule'a dokunmadan parlaklık (0 = karanlık)."""
    global _state
    try:
        value = int(request.match_info["value"])
    except ValueError:
        return web.json_response({"error": "bad value"}, status=400)
    value = max(0, min(1000, value))
    _state = "on" if value > 0 else "off"
    asyncio.create_task(_run_ble(write_intensity(value, label=f"INTENSITY → {value}"),
                                 f"intensity {value}"))
    return web.json_response({"state": _state, "intensity": value})

async def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "off":
            await turn_off()
        elif cmd == "on":
            await turn_on()
        else:
            print(f"Kullanım: python3 {sys.argv[0]} [on|off]")
    else:
        app = web.Application()
        app.router.add_get("/on",     handle_on)
        app.router.add_get("/off",    handle_off)
        app.router.add_get("/status", handle_status)
        app.router.add_post("/apply", handle_apply)
        app.router.add_get("/intensity/{value}", handle_intensity)
        app.router.add_get("/dump", handle_dump)
        print("XR15 server başlıyor: http://0.0.0.0:8765")
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8765)
        await site.start()
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
