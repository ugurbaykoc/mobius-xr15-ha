"""
EcoTech Marine XR15w G5 Pro — BLE HTTP Bridge
Kullanım:
    python3 test.py          # server modu (HA için)
    python3 test.py on       # manuel aç
    python3 test.py off      # manuel kapat
"""
import asyncio
import os
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
ATTR_CURRENT_SCENE       = 401
ATTR_OPERATION_STATE     = 104
ATTR_ERROR_STATE         = 107
ATTR_PHYSICAL_VALUES     = 101
ATTR_PUCK_TEMPERATURE    = 1511
ATTR_FIRMWARE_VERSION    = 1
ATTR_MINUTE_OF_DAY       = 203
ATTR_IS_CLOCK_SET        = 200
ATTR_ACCLIMATION_ENABLED = 902
ATTR_ACCLIMATION_PERIOD  = 903
ATTR_ACCLIMATION_START_I = 904
ATTR_LUNAR_ENABLED       = 907

# M$SceneID - uygulamanın kendi enum'undan (PROTOCOL.md)
SCENES = {"empty": 0, "feed": 1, "battery_backup": 2, "all_off": 3,
          "color_cycle": 4, "disco": 5, "thunderstorm": 6,
          "cloud_cover": 7, "all_on": 8, "all_50": 9}

# M$PhysicalValues - attr 101 dizisindeki indeksler
PHYSICAL_VALUE_NAMES = {
    1: "driver_temperature", 2: "motor_temperature", 3: "cluster_temperature",
    4: "motor_power", 5: "motor_rpm", 6: "battery_voltage", 7: "input_voltage",
    8: "internal_temperature", 9: "fan_speed", 11: "gallons_per_hour",
    12: "supply_current", 13: "fan_voltage", 14: "module_temperature",
    16: "cluster2_temperature",
}

OPERATION_STATES = {0: "OOB", 1: "LiveDemo", 2: "Scene", 3: "Schedule"}
ERROR_STATES = {0: "NoError", 1: "Disconnect", 2: "Temperature", 7: "SchedulePlayback",
                15: "FanFault", 16: "DriverTemp", 17: "LEDChannelShortCircuit",
                18: "LEDChannelCurrentLeak", 19: "LEDChannelOpenCircuit",
                20: "LEDClusterThermistor", 21: "LEDClusterOverTemp", 23: "RTC"}
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

async def _run_cmd(*args, timeout=20):
    """Harici komutu çalıştır; çıktıyı döndür, asla exception fırlatma."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
        return proc.returncode, (out or b"").decode(errors="replace").strip()
    except BaseException as e:
        return None, str(e)


async def _bluez_reset():
    """BlueZ'de asılı kalmış bağlanma girişimini iptal et.

    Python tarafında iptal edilen (timeout) bir connect, BlueZ
    seviyesinde devam eder: bleak'te bunu durduracak bir yol yok, çünkü
    yarım kalmış client'ın disconnect'i de temizleyemiyor. Sonuç olarak
    sonraki her denemeye org.bluez.Error.InProgress dönüyor ve bu durum
    servis yeniden başlatılana kadar sürüyor. bluetoothctl disconnect
    bunu dışarıdan temizler.
    """
    rc, out = await _run_cmd("bluetoothctl", "disconnect", ADDRESS)
    if rc == 0:
        print("  BlueZ durumu temizlendi (bluetoothctl disconnect)")
    else:
        print(f"  BlueZ temizleme sonucu (rc={rc}): {out}")
    await asyncio.sleep(2)  # BlueZ'in oturması için


async def _adapter_power_cycle():
    """Bluetooth adaptörünü kapatıp aç - elle 'systemctl restart bluetooth'
    yapmanın root gerektirmeyen karşılığı.

    Arka arkaya başarısız olan işlerden sonra adaptörün kendisi takılmış
    olabiliyor (cihaz taramada bile görünmez oluyor). bluetoothctl power
    off/on adaptörü sıfırlar ve bunu normal kullanıcı olarak yapabiliriz;
    servis restart'ı ise root ister - üstelik xr15.service PartOf=
    bluetooth.service olduğu için köprünün kendisini de öldürürdü.
    """
    print("  Adaptör sıfırlanıyor (bluetoothctl power off/on)...")
    await _run_cmd("bluetoothctl", "power", "off")
    await asyncio.sleep(3)
    rc, out = await _run_cmd("bluetoothctl", "power", "on")
    if rc == 0:
        print("  Adaptör tekrar açıldı")
    else:
        print(f"  Adaptör açılamadı (rc={rc}): {out}")
    await asyncio.sleep(5)  # adaptörün taramaya hazır olması için


async def _safe_connect(timeout=30, retries=3):
    for attempt in range(1, retries + 1):
        client = BleakClient(ADDRESS, timeout=timeout)
        try:
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
        except BaseException as e:
            # BaseException, çünkü asyncio.CancelledError (iş zaman aşımına
            # uğradığında gelir) Exception'dan türemiyor: sadece Exception
            # yakalanırsa timeout'ta bu temizlik hiç çalışmaz ve BlueZ'de
            # yarım kalmış bir bağlanma girişimi kalır.
            # Tipi de yazıyoruz: bazı bleak hataları boş mesajla geliyor ve
            # log'da "başarısız:" diye sessiz bir satır bırakıyordu.
            print(f"  Bağlantı denemesi {attempt} başarısız: "
                  f"{type(e).__name__}: {e}")
            try:
                await asyncio.wait_for(client.disconnect(), 10)
            except BaseException:
                pass
            if isinstance(e, asyncio.CancelledError):
                raise
            if "InProgress" in str(e):
                await _bluez_reset()
            elif attempt < retries:
                # "not found" = cihaz o an yayın yapmıyor. Bağlantı
                # kapandıktan sonra yeniden reklama başlaması birkaç saniye
                # sürüyor, o yüzden bu durumda daha uzun bekliyoruz.
                await asyncio.sleep(8 if "not found" in str(e).lower() else 3)
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
            await asyncio.wait_for(client.disconnect(), 10)
        except Exception:
            pass

async def turn_off():
    await write_schedule([bytes(42)] * 25, intensity=500, label="IŞIĞI SÖNDÜR")
    print("  → Işık söndürüldü!")

async def turn_on():
    await write_schedule(build_original_schedule(), intensity=500, label="IŞIĞI AÇ")
    print("  → Işık açıldı!")

# Orijinal schedule'ın 11 zaman noktası (dakika cinsinden) ve bunlara
# karşılık gelen gün içi parlaklık eğrisi. Eğri, orijinal schedule'ın
# brightness (kanal 1) profilinden alındı: şafak → öğle tepesi → gün batımı.
SCHEDULE_TIMES = [0, 360, 480, 600, 720, 840, 960, 1080, 1200, 1320, 1410]
DAY_CURVE      = [0.2, 0.4, 0.6, 0.8, 1.0, 1.0, 0.8, 0.6, 0.4, 0.2, 0.1]

# Kanal 1 schedule'ın kendi master dimmer'ı: 0 olduğunda diğer kanallar
# ne olursa olsun ışık kapalı kalıyor (deneyle doğrulandı). Bu yüzden gün
# eğrisini sadece bu kanala uyguluyoruz - renk kanalları sabit kalınca
# renk dengesi her saatte aynı, sadece parlaklık değişiyor.
MASTER_CHANNEL = 1


def build_flat_schedule(ch_vals, curve=True):
    """Renk tarifini gün boyu 11 zaman noktasına yazar.

    curve=True: renk kanalları sabit kalır, master dimmer DAY_CURVE ile
    ölçeklenir. Cihaz ardışık slotlar arasında geçiş yaptığı için sonuç,
    Mobius uygulamasındaki gibi sabah yumuşak açılan, öğlen tepe yapan ve
    akşam sönen bir gün profilidir.

    curve=False: eski davranış, her slotta birebir aynı değerler (gün
    boyu sabit çıkış).
    """
    master = int(ch_vals.get(MASTER_CHANNEL, 0))
    slots = []
    for time_min, factor in zip(SCHEDULE_TIMES, DAY_CURVE):
        vals = dict(ch_vals)
        if curve:
            vals[MASTER_CHANNEL] = max(0, min(1000, round(master * factor)))
        slots.append(make_item_42(time_min, 0x01, vals))
    slots += [bytes(42)] * (25 - len(slots))
    return slots

async def apply_recipe(ch_vals, intensity, curve=True):
    sekil = "gün eğrisi" if curve else "sabit"
    await write_schedule(build_flat_schedule(ch_vals, curve), intensity=intensity,
                         label=f"RENK TARİFİ UYGULA ({sekil}, intensity={intensity})")
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
            await asyncio.wait_for(client.disconnect(), 10)
        except Exception:
            pass

# ── HTTP server ───────────────────────────────────────────────────
_state = "unknown"
_last_result = {"ok": None, "label": None, "error": None, "at": None}
_ble_lock = asyncio.Lock()

# Arka arkaya kaç hatadan sonra adaptör sıfırlansın.
_consecutive_failures = 0
ESCALATE_AFTER = 2

# Bir iş bittikten sonra cihazın yeniden reklam yayınına dönmesi için
# beklenen süre. Log'da net görülüyor: başarılı bir işin hemen ardından
# gelen iş "Device not found" ile düşüyordu, çünkü henüz yayında değil.
POST_JOB_SETTLE = 6

# Telemetri önbelleği: BLE pahalı, HA 30 saniyede bir /status çekiyor.
# Bu yüzden cihazı arka planda seyrek okuyup sonucu önbellekten servis
# ediyoruz - HA tarafında ekstra bir yoklama mantığı gerekmiyor.
_telemetry = {}
_telemetry_at = None
TELEMETRY_INTERVAL = 1800
# Telemetri okuması cihazda doğrulanmadığı ve BLE hattı kırılgan olduğu
# için varsayılan kapalı. Açmak için: XR15_TELEMETRY=1
TELEMETRY_ENABLED = os.environ.get("XR15_TELEMETRY") == "1"

# Bir BLE işinin alabileceği azami süre. Bleak/BlueZ nadiren de olsa
# süresiz asılı kalabiliyor - kilidi sonsuza dek tutup arkasındaki her
# komutu bloklamasın diye işi iptal edip FAILED olarak kaydediyoruz.
BLE_JOB_TIMEOUT = 120

async def _run_ble(coro, label="", background=False):
    """BLE işini sıraya alıp çalıştır.

    background=True (telemetri gibi kendi başlattığımız işler):
    kullanıcının komut geçmişini (_last_result) ezmez ve hata sayacını
    artırmaz. Aksi halde arka planda sessizce başarısız olan bir okuma,
    adaptörü durduk yere power-cycle ettirip asıl komutları bozabiliyor.
    """
    global _last_result, _consecutive_failures
    if background and _consecutive_failures:
        print("  sistem zaten hatalı durumda - arka plan işi atlandı")
        coro.close()  # çalıştırmayacaksak coroutine'i düzgün kapat
        return
    async with _ble_lock:
        # Arka arkaya başarısızlıklarda adaptörün kendisi takılmış
        # olabilir; bir sonraki işi denemeden önce sıfırla. Her
        # başarısızlıkta değil, ESCALATE_AFTER'ın katlarında yapıyoruz ki
        # üst üste hata alırken her komut power cycle beklemesin.
        if _consecutive_failures and _consecutive_failures % ESCALATE_AFTER == 0:
            print(f"  {_consecutive_failures} ardışık hata - adaptör sıfırlanıyor")
            await _adapter_power_cycle()

        if not background:
            _last_result = {"ok": None, "label": label, "error": None,
                            "at": datetime.now().isoformat(timespec="seconds")}
        try:
            await asyncio.wait_for(coro, timeout=BLE_JOB_TIMEOUT)
            if not background:
                _consecutive_failures = 0
                _last_result = {"ok": True, "label": label, "error": None,
                                "at": datetime.now().isoformat(timespec="seconds")}
        except asyncio.TimeoutError:
            if not background:
                _consecutive_failures += 1
            print(f"BLE zaman aşımı ({BLE_JOB_TIMEOUT}s): {label}")
            # İptal edilen coroutine'in dışındayız, burada await güvenli:
            # BlueZ'de yarım kalan bağlanma girişimini hemen temizle ki
            # sonraki komutlar InProgress'e takılmasın.
            await _bluez_reset()
            if not background:
                _last_result = {"ok": False, "label": label,
                                "error": f"timed out after {BLE_JOB_TIMEOUT}s",
                                "at": datetime.now().isoformat(timespec="seconds")}
        except Exception as e:
            print(f"BLE hata: {type(e).__name__}: {e}")
            if not background:
                _consecutive_failures += 1
                _last_result = {"ok": False, "label": label,
                                "error": f"{type(e).__name__}: {e}",
                                "at": datetime.now().isoformat(timespec="seconds")}
        finally:
            # Kilidi bırakmadan önce bekle ki sıradaki komut cihaz henüz
            # yayına dönmemişken bağlanmaya çalışmasın.
            await asyncio.sleep(POST_JOB_SETTLE)

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
    return web.json_response({"state": _state, "last_result": _last_result,
                              "consecutive_failures": _consecutive_failures,
                              "telemetry": _telemetry, "telemetry_at": _telemetry_at})


async def handle_reset(request):
    """POST /reset — Bluetooth'u elle onar (asılı bağlantı + adaptör sıfırla).

    'systemctl restart bluetooth' için SSH'a girmeye gerek kalmasın diye:
    HA'daki Reset Bluetooth düğmesi burayı çağırır.
    """
    global _consecutive_failures
    async with _ble_lock:
        await _bluez_reset()
        await _adapter_power_cycle()
        _consecutive_failures = 0
    return web.json_response({"reset": "ok"})

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
            await asyncio.wait_for(client.disconnect(), 10)
        except Exception:
            pass
    return received

# ── C2 cevap çözümleme + genel attribute okuma/yazma ──────────────

def parse_c2_response(packets):
    """0xDF cevabını çöz.

    Çerçeve: 02 DF op msgid(2) 00 00 len(2) | status(1) attr(2) sub(1)
             count(1) elem_len(1) data | crc(2)
    Gerçek cihaz cevabıyla doğrulandı (attr 511 -> 777).

    Paketler birleştirilerek okunuyor: uzun cevaplar (örn. PhysicalValues
    dizisi) birden fazla notification'a bölünebiliyor ve tek pakete
    bakmak gövdeyi yarıda kesiyordu.
    """
    buf = b"".join(packets)
    start = -1
    for i in range(len(buf) - 1):
        if buf[i] == 0x02 and buf[i + 1] == 0xDF:
            start = i
            break
    if start < 0 or len(buf) - start < 15:
        return None
    frame = buf[start:]
    plen = int.from_bytes(frame[7:9], "little")
    body = frame[9:9 + plen]
    if len(body) < 6:
        return None
    status, sub, count, elem = body[0], body[3], body[4], body[5]
    attr = int.from_bytes(body[1:3], "little")
    data = body[6:6 + count * elem]
    vals = []
    if elem:
        for i in range(count):
            chunk = data[i * elem:(i + 1) * elem]
            if len(chunk) == elem:
                vals.append(int.from_bytes(chunk, "little"))
    return {"status": status, "attr": attr, "sub": sub, "count": count,
            "elem_len": elem, "values": vals, "raw": data.hex(),
            "truncated": len(body) < 6 + count * elem}


async def with_connection(fn):
    """Tek BLE bağlantısı aç, fn(client, tx, received) çalıştır, kapat."""
    client = await _safe_connect(timeout=30)
    received = []
    try:
        def on_note(_char, data):
            received.append(bytes(data))
        try:
            await client.start_notify(RX_DATA, on_note)
            await client.start_notify(RX_FINAL, on_note)
        except Exception as e:
            print(f"  notify warning: {e}")
        tx = client.services.get_characteristic(TX_FINAL)
        return await fn(client, tx, received)
    finally:
        try:
            await asyncio.wait_for(client.disconnect(), 10)
        except BaseException:
            pass


async def _send_raw(client, tx, pkt):
    await client._backend.write_gatt_char(tx, bytearray(pkt), False)


async def _read_on(client, tx, received, specs, wait=1.5):
    """specs: [(attr, sub, count)] - aynı bağlantıda sırayla oku."""
    out = {}
    for idx, (attr, sub, count) in enumerate(specs, 1):
        received.clear()
        await _send_raw(client, tx, mk_get(attr, idx, bytes([sub, count])))
        await asyncio.sleep(wait)
        r = parse_c2_response(list(received))
        out[attr] = r
        print(f"  GET {attr}: {r['values'] if r else 'cevap yok'}")
    return out


async def read_attributes(specs):
    return await with_connection(lambda c, t, r: _read_on(c, t, r, specs))


async def write_attribute(attr, value, sub=0):
    """Attribute'u yaz.

    Eleman boyutunu tahmin etmek yerine önce okuyup cihazın bildirdiği
    elem_len ile yazıyoruz - böylece boyutunu bilmediğimiz attribute'lar
    da (sahne, acclimation, lunar...) doğru formatta gidiyor.
    """
    async def job(client, tx, received):
        info = await _read_on(client, tx, received, [(attr, sub, 1)])
        r = info.get(attr)
        size = (r or {}).get("elem_len")
        if not size:
            # Tahmin etmiyoruz: yanlış boyutta bir yazma cihazın bağlantıyı
            # düşürmesine (ve bir süre ortadan kaybolmasına) yol açıyor -
            # sahne yazarken bu yaşandı. Okuyamıyorsak dokunmuyoruz.
            raise RuntimeError(
                f"attr {attr} okunamadı, boyutu bilinmiyor - yazma iptal edildi")
        data = int(value).to_bytes(size, "little")
        print(f"  SET {attr} = {value} ({size} bayt)")
        await _send_raw(client, tx, mk_simple_set(attr, data, 10))
        await asyncio.sleep(0.5)
        received.clear()
        info2 = await _read_on(client, tx, received, [(attr, sub, 1)])
        return {"written": value, "size": size,
                "readback": (info2.get(attr) or {}).get("values")}
    return await with_connection(job)


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
    """POST /apply — JSON: {"channels": {"21": 800, ...}, "intensity": 1000,
                            "curve": "ramp"|"flat"}

    curve varsayılan olarak "ramp": gün boyu yumuşak geçiş (bkz.
    build_flat_schedule). "flat" gönderilirse eski sabit davranış.
    """
    global _state
    try:
        data = await request.json()
        ch_vals = {int(k): int(v) for k, v in data.get("channels", {}).items()}
        intensity = int(data.get("intensity", 500))
    except (ValueError, TypeError):
        return web.json_response({"error": "bad request"}, status=400)
    curve = str(data.get("curve", "ramp")).lower() != "flat"
    _state = "on" if intensity > 0 else "off"
    asyncio.create_task(_run_ble(apply_recipe(ch_vals, intensity, curve),
                                 f"apply (intensity {intensity})"))
    return web.json_response({"state": _state, "channels": ch_vals,
                              "intensity": intensity,
                              "curve": "ramp" if curve else "flat"})

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

async def handle_read(request):
    """GET /read?attr=511&sub=0&count=1 — herhangi bir attribute'u oku."""
    try:
        attr = int(request.query.get("attr"))
        sub = int(request.query.get("sub", 0))
        count = int(request.query.get("count", 1))
    except (TypeError, ValueError):
        return web.json_response({"error": "attr gerekli"}, status=400)
    # HTTP isteğini sonsuza kadar bekletme: köprü meşgulse hemen 503 dön,
    # çünkü HA tarafındaki istemcinin zaman aşımı 10 saniye.
    try:
        await asyncio.wait_for(_ble_lock.acquire(), 5)
    except asyncio.TimeoutError:
        return web.json_response({"error": "köprü meşgul"}, status=503)
    try:
        res = await asyncio.wait_for(read_attributes([(attr, sub, count)]), 60)
    except BaseException as e:
        return web.json_response({"error": str(e)}, status=500)
    finally:
        _ble_lock.release()
    return web.json_response({"attr": attr, "result": res.get(attr)})


async def handle_scene(request):
    """POST /scene {"scene": "feed"} — anlık sahne (FeedMode, Thunderstorm...)."""
    global _state
    try:
        data = await request.json()
        raw = data.get("scene")
        scene = SCENES[raw] if isinstance(raw, str) else int(raw)
    except (ValueError, TypeError, KeyError):
        return web.json_response({"error": f"geçersiz sahne; {list(SCENES)}"},
                                 status=400)
    if scene == SCENES["all_off"]:
        _state = "off"
    elif scene in (SCENES["all_on"], SCENES["all_50"]):
        _state = "on"
    asyncio.create_task(_run_ble(write_attribute(ATTR_CURRENT_SCENE, scene),
                                 f"scene {raw}"))
    return web.json_response({"scene": raw, "id": scene, "state": _state})


async def handle_attr_write(request):
    """POST /attr {"attr": 902, "value": 1} — genel attribute yazma."""
    try:
        data = await request.json()
        attr = int(data["attr"])
        value = int(data["value"])
    except (ValueError, TypeError, KeyError):
        return web.json_response({"error": "attr ve value gerekli"}, status=400)
    asyncio.create_task(_run_ble(write_attribute(attr, value),
                                 f"attr {attr} = {value}"))
    return web.json_response({"attr": attr, "value": value})


def _decode_telemetry(res):
    """Ham okuma sonucunu HA'nın kullanacağı isimli alanlara çevir."""
    out = {}

    def first(attr):
        r = res.get(attr)
        return r["values"][0] if r and r.get("values") else None

    fw = first(ATTR_FIRMWARE_VERSION)
    if fw is not None:
        out["firmware_version"] = fw
    op = first(ATTR_OPERATION_STATE)
    if op is not None:
        out["operation_state"] = OPERATION_STATES.get(op, f"Unknown({op})")
    err = first(ATTR_ERROR_STATE)
    if err is not None:
        out["error_state"] = ERROR_STATES.get(err, f"Unknown({err})")
    puck = first(ATTR_PUCK_TEMPERATURE)
    if puck is not None:
        out["puck_temperature"] = puck
    mod = first(ATTR_MINUTE_OF_DAY)
    if mod is not None:
        out["device_minute_of_day"] = mod
        out["device_time"] = f"{mod // 60:02d}:{mod % 60:02d}"
    clk = first(ATTR_IS_CLOCK_SET)
    if clk is not None:
        out["clock_set"] = bool(clk)
    acc = first(ATTR_ACCLIMATION_ENABLED)
    if acc is not None:
        out["acclimation_enabled"] = bool(acc)
    lun = first(ATTR_LUNAR_ENABLED)
    if lun is not None:
        out["lunar_enabled"] = bool(lun)
    pv = res.get(ATTR_PHYSICAL_VALUES)
    if pv and pv.get("values"):
        for idx, val in enumerate(pv["values"]):
            name = PHYSICAL_VALUE_NAMES.get(idx)
            if name:
                out[name] = val
    return out


async def refresh_telemetry():
    global _telemetry, _telemetry_at
    specs = [(ATTR_FIRMWARE_VERSION, 0, 1), (ATTR_OPERATION_STATE, 0, 1),
             (ATTR_ERROR_STATE, 0, 1), (ATTR_PUCK_TEMPERATURE, 0, 1),
             (ATTR_MINUTE_OF_DAY, 0, 1), (ATTR_IS_CLOCK_SET, 0, 1),
             (ATTR_ACCLIMATION_ENABLED, 0, 1), (ATTR_LUNAR_ENABLED, 0, 1),
             (ATTR_PHYSICAL_VALUES, 0, 17)]
    print(f"\n{'='*50}\nTELEMETRİ OKUNUYOR\n{'='*50}")
    res = await read_attributes(specs)
    _telemetry = _decode_telemetry(res)
    _telemetry_at = datetime.now().isoformat(timespec="seconds")
    print(f"  telemetri: {_telemetry}")


async def handle_telemetry(request):
    """GET /telemetry — önbellek; ?refresh=1 ile cihazdan tazele."""
    if request.query.get("refresh") == "1":
        # Arka planda çalıştır: cevabı bekletirsek HA istemcisi zaman aşımına
        # uğrar. Sonuç bir sonraki /status yoklamasında görünür.
        asyncio.create_task(_run_ble(refresh_telemetry(), "telemetry",
                                     background=True))
        return web.json_response({"refreshing": True, "telemetry": _telemetry,
                                  "at": _telemetry_at})
    return web.json_response({"telemetry": _telemetry, "at": _telemetry_at})


async def telemetry_loop():
    """Arka planda seyrek telemetri yenileme (varsayılan kapalı)."""
    if not TELEMETRY_ENABLED:
        print("Telemetri devre dışı (açmak için XR15_TELEMETRY=1)")
        return
    await asyncio.sleep(60)
    while True:
        try:
            await _run_ble(refresh_telemetry(), "telemetry", background=True)
        except Exception as e:
            print(f"telemetri hatası: {e}")
        await asyncio.sleep(TELEMETRY_INTERVAL)


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
        app.router.add_post("/reset", handle_reset)
        app.router.add_get("/read", handle_read)
        app.router.add_post("/scene", handle_scene)
        app.router.add_post("/attr", handle_attr_write)
        app.router.add_get("/telemetry", handle_telemetry)
        print("XR15 server başlıyor: http://0.0.0.0:8765")
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8765)
        await site.start()
        asyncio.create_task(telemetry_loop())
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
