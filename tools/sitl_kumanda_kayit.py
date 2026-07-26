#!/usr/bin/env python3
"""ArduSub SITL icin kolay komut, hareket kaydi ve tekrar oynatma araci."""

import json
import math
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from sitl_gorev_20sn import SitlMission, wrap_degrees


RECORD_DIR = Path(__file__).with_name("kayitlar")
GUIDED_BODY_NED_FRAME = 8
GUIDED_LOCAL_NED_FRAME = 1
# ArduSub, VX/VY/VZ alanlarinin ucunu de birlikte bekler. Rover orneklerindeki
# Z-hizini yok sayan 2535/1511 maskeleri Sub tarafinda vel_ignore olur.
GUIDED_VELOCITY_YAW_MASK = 2503
GUIDED_VELOCITY_YAW_RATE_MASK = 1479
# Konum + hiz + yaw kullan, ivme ve yaw-rate alanlarini yok say.
GUIDED_POSITION_VELOCITY_YAW_MASK = 2496
GUIDED_SEND_PERIOD = 0.10
TURN_TOLERANCE_DEG = 1.5
TURN_RATE_TOLERANCE_DPS = 2.0
CIRCLE_RADIUS_M = 0.5
MAV_CMD_SET_MESSAGE_INTERVAL = 511
ATTITUDE_MESSAGE_ID = 30
LOCAL_POSITION_NED_MESSAGE_ID = 32
AUTONOMOUS_LEG_LENGTH_M = 4.0
AUTONOMOUS_SPEED_MPS = 0.20
POSITION_TOLERANCE_M = 0.10


def pwm_to_velocity(pwm):
    """Alisik olunan 1000..2000 PWM degerini -1..+1 m/s hiza cevirir."""
    pwm = int(pwm)
    if not 1000 <= pwm <= 2000:
        raise ValueError("PWM 1000 ile 2000 arasinda olmali")
    return (pwm - 1500) / 500.0


def safe_name(name):
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip())
    return cleaned or datetime.now().strftime("parkur_%Y%m%d_%H%M%S")


def print_help():
    print(
        """
Komutlar:
  ileri 20 1600       20 saniye, 1600 PWM karsiligi duz ileri
  sag 90              GUIDED kontrolcuyle mevcut yonden tam 90 derece saga don
  daire 450 1575      1575 ileri PWM ile saga toplam 450 derece daire
  otonom               Düzeltilmiş yarışma parkurunu tek seferde uygula
  liste                Kaydedilen hareketleri goster
  geri                 Son kaydedilen hareketi sil
  temizle              Hareket listesini temizle
  kaydet parkur1       Listeyi tools/kayitlar/parkur1.json dosyasina yaz
  yukle parkur1        Kayitli JSON listesini yukle
  oynat                Listedeki hareketleri tek seferde uygula
  dur                  Kanallari hemen notrle
  yardim               Bu komutlari tekrar goster
  cikis                Notrle, disarm et ve kapat
""".strip()
    )


def show_actions(actions):
    if not actions:
        print("Hareket listesi bos")
        return
    for index, action in enumerate(actions, start=1):
        print("  {}. {}".format(index, action))


def send_guided_target(mission, forward_mps, target_yaw=None, yaw_rate_rps=None):
    if (target_yaw is None) == (yaw_rate_rps is None):
        raise ValueError("Yaw hedefi veya yaw hizi alanlarindan yalniz biri verilmeli")
    if target_yaw is not None:
        type_mask = GUIDED_VELOCITY_YAW_MASK
        yaw_rad = math.radians(target_yaw % 360.0)
        yaw_rate = 0.0
    else:
        type_mask = GUIDED_VELOCITY_YAW_RATE_MASK
        yaw_rad = 0.0
        yaw_rate = float(yaw_rate_rps)

    mission.master.mav.set_position_target_local_ned_send(
        int(time.monotonic() * 1000.0) & 0xFFFFFFFF,
        mission.master.target_system,
        mission.master.target_component,
        GUIDED_BODY_NED_FRAME,
        type_mask,
        0.0,
        0.0,
        0.0,
        float(forward_mps),
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        yaw_rad,
        yaw_rate,
    )


def request_attitude_10hz(mission):
    mission.master.mav.command_long_send(
        mission.master.target_system,
        mission.master.target_component,
        MAV_CMD_SET_MESSAGE_INTERVAL,
        0,
        ATTITUDE_MESSAGE_ID,
        100000,
        0,
        0,
        0,
        0,
        0,
    )
    time.sleep(0.3)


def request_local_position_10hz(mission):
    mission.master.mav.command_long_send(
        mission.master.target_system,
        mission.master.target_component,
        MAV_CMD_SET_MESSAGE_INTERVAL,
        0,
        LOCAL_POSITION_NED_MESSAGE_ID,
        100000,
        0,
        0,
        0,
        0,
        0,
    )
    time.sleep(0.3)


def read_local_position(mission, timeout=1.0):
    """Kuyruktaki en guncel LOCAL_POSITION_NED ornegini dondur."""
    message = None
    while True:
        queued = mission.master.recv_match(type="LOCAL_POSITION_NED", blocking=False)
        if queued is None:
            break
        message = queued
    if message is None:
        message = mission.master.recv_match(
            type="LOCAL_POSITION_NED", blocking=True, timeout=timeout
        )
        while True:
            queued = mission.master.recv_match(
                type="LOCAL_POSITION_NED", blocking=False
            )
            if queued is None:
                break
            message = queued
    if message is None:
        raise RuntimeError("LOCAL_POSITION_NED verisi alinamadi")
    return float(message.x), float(message.y), float(message.z)


def send_guided_position_velocity_target(
    mission, target_position, velocity_ne, target_yaw
):
    target_x, target_y, target_z = target_position
    velocity_n, velocity_e = velocity_ne
    mission.master.mav.set_position_target_local_ned_send(
        int(time.monotonic() * 1000.0) & 0xFFFFFFFF,
        mission.master.target_system,
        mission.master.target_component,
        GUIDED_LOCAL_NED_FRAME,
        GUIDED_POSITION_VELOCITY_YAW_MASK,
        float(target_x),
        float(target_y),
        float(target_z),
        float(velocity_n),
        float(velocity_e),
        0.0,
        0.0,
        0.0,
        0.0,
        math.radians(target_yaw % 360.0),
        0.0,
    )


def guided_goto_position(
    mission,
    target_position,
    target_yaw,
    label,
    max_speed=AUTONOMOUS_SPEED_MPS,
    minimum_duration=0.0,
    timeout=60.0,
):
    """Yerel NED konum geri bildirimiyle hedef noktaya duz ilerle."""
    target_x, target_y, target_z = target_position
    start_x, start_y, _ = read_local_position(mission)
    path_x = target_x - start_x
    path_y = target_y - start_y
    planned_distance = math.hypot(path_x, path_y)
    if planned_distance <= POSITION_TOLERANCE_M:
        guided_stop(mission, target_yaw=target_yaw)
        print("{}: hedef zaten {:.2f} m yakinlikta".format(label, planned_distance))
        return
    unit_x = path_x / planned_distance
    unit_y = path_y / planned_distance
    print(
        "{}: hedef N/E {:.2f}/{:.2f} m, mesafe {:.2f} m, yaw {:.1f}".format(
            label, target_x, target_y, planned_distance, target_yaw % 360.0
        )
    )
    max_speed = float(max_speed)
    if max_speed <= 0.0:
        raise ValueError("Konum hedefi hizi sifirdan buyuk olmali")
    start_time = time.monotonic()
    minimum_travel_time = max(
        planned_distance / max_speed,
        float(minimum_duration),
    )
    trajectory_speed = planned_distance / minimum_travel_time
    deadline = start_time + max(float(timeout), minimum_travel_time + 30.0)
    stable_samples = 0
    next_report = time.monotonic()
    while time.monotonic() < deadline:
        current_x, current_y, _ = read_local_position(mission)
        delta_x = target_x - current_x
        delta_y = target_y - current_y
        distance = math.hypot(delta_x, delta_y)
        elapsed = time.monotonic() - start_time
        commanded_progress = min(planned_distance, trajectory_speed * elapsed)
        command_x = start_x + unit_x * commanded_progress
        command_y = start_y + unit_y * commanded_progress
        trajectory_finished = commanded_progress >= planned_distance
        if trajectory_finished and distance <= POSITION_TOLERANCE_M:
            stable_samples += 1
            velocity_n = 0.0
            velocity_e = 0.0
        else:
            stable_samples = 0
            if trajectory_finished:
                velocity_n = 0.0
                velocity_e = 0.0
            else:
                velocity_n = trajectory_speed * unit_x
                velocity_e = trajectory_speed * unit_y
        send_guided_position_velocity_target(
            mission,
            (command_x, command_y, target_z),
            (velocity_n, velocity_e),
            target_yaw,
        )
        now = time.monotonic()
        if now >= next_report:
            print(
                "  hedefe kalan {:.2f} m | sure {:.1f}/{:.1f} sn".format(
                    distance, elapsed, minimum_travel_time
                )
            )
            next_report += 2.0
        if stable_samples >= 5:
            guided_stop(mission, target_yaw=target_yaw)
            print("  konuma oturdu; hata {:.2f} m".format(distance))
            return
        time.sleep(GUIDED_SEND_PERIOD)
    raise RuntimeError("{}: konum hedefi zaman asimina ugradi".format(label))


def read_attitude(mission, timeout=0.5):
    try:
        message = mission.get_attitude_message(timeout=timeout)
    except RuntimeError:
        return None
    return (
        math.degrees(message.yaw) % 360.0,
        math.degrees(message.yawspeed),
    )


def guided_stop(mission, target_yaw=None, duration=0.8):
    if target_yaw is None:
        target_yaw = mission.get_yaw_degrees()
    end_time = time.monotonic() + duration
    while time.monotonic() < end_time:
        send_guided_target(mission, 0.0, target_yaw=target_yaw)
        time.sleep(GUIDED_SEND_PERIOD)


def guided_straight(mission, seconds, pwm, label, target_yaw=None):
    seconds = float(seconds)
    if seconds <= 0.0:
        raise ValueError("Sure sifirdan buyuk olmali")
    forward_mps = pwm_to_velocity(pwm)
    if target_yaw is None:
        target_yaw = mission.get_yaw_degrees()
    target_yaw %= 360.0
    print(
        "{}: {:.1f} saniye {:.2f} m/s ileri, sabit HUD yaw {:.1f}".format(
            label, seconds, forward_mps, target_yaw
        )
    )
    start_time = time.monotonic()
    next_report = start_time
    while True:
        now = time.monotonic()
        elapsed = now - start_time
        if elapsed >= seconds:
            break
        send_guided_target(mission, forward_mps, target_yaw=target_yaw)
        if now >= next_report:
            current_yaw = mission.get_yaw_degrees(timeout=1.0)
            print(
                "  kalan {:4.1f} sn | HUD yaw {:6.1f}".format(
                    max(0.0, seconds - elapsed), current_yaw
                )
            )
            next_report += 5.0
        time.sleep(GUIDED_SEND_PERIOD)
    guided_stop(mission, target_yaw=target_yaw)


def guided_turn_to_target(mission, target_yaw, label):
    target_yaw %= 360.0
    print("{}: GUIDED HUD yaw hedefi {:.1f}".format(label, target_yaw))
    deadline = time.monotonic() + 45.0
    stable_samples = 0
    next_report = time.monotonic()
    while time.monotonic() < deadline:
        send_guided_target(mission, 0.0, target_yaw=target_yaw)
        attitude = read_attitude(mission)
        if attitude is None:
            time.sleep(GUIDED_SEND_PERIOD)
            continue
        current_yaw, yaw_rate = attitude
        error = wrap_degrees(target_yaw - current_yaw)
        if (
            abs(error) <= TURN_TOLERANCE_DEG
            and abs(yaw_rate) <= TURN_RATE_TOLERANCE_DPS
        ):
            stable_samples += 1
        else:
            stable_samples = 0
        now = time.monotonic()
        if now >= next_report:
            print(
                "  HUD yaw {:6.1f} | hata {:+5.1f} | yaw hizi {:+5.1f} d/s".format(
                    current_yaw, error, yaw_rate
                )
            )
            next_report += 1.0
        if stable_samples >= 3:
            guided_stop(mission, target_yaw=target_yaw)
            print("  hedefe oturdu: HUD yaw {:.1f}".format(current_yaw))
            return
        time.sleep(GUIDED_SEND_PERIOD)
    raise RuntimeError("GUIDED yaw hedefi 45 saniye icinde yakalanamadi")


def guided_turn_right(mission, degrees, label, start_yaw=None):
    degrees = float(degrees)
    if not 0.0 < degrees <= 180.0:
        raise ValueError("sag komutunda derece 0 ile 180 arasinda olmali")
    if start_yaw is None:
        start_yaw = mission.get_yaw_degrees()
    start_yaw %= 360.0
    target_yaw = (start_yaw + degrees) % 360.0
    print(
        "{}: baslangic {:.1f} + {:.1f} = hedef {:.1f}".format(
            label, start_yaw, degrees, target_yaw
        )
    )
    guided_turn_to_target(mission, target_yaw, label)
    return target_yaw


def guided_circle(mission, degrees, pwm, label, start_heading=None):
    degrees = float(degrees)
    if degrees <= 0.0:
        raise ValueError("Daire derecesi sifirdan buyuk olmali")
    forward_mps = pwm_to_velocity(pwm)
    if forward_mps <= 0.0:
        raise ValueError("Daire icin ileri PWM 1500'den buyuk olmali")
    yaw_rate_rps = forward_mps / CIRCLE_RADIUS_M
    measured_start_yaw = mission.get_yaw_degrees()
    if start_heading is None:
        start_heading = measured_start_yaw
    start_heading %= 360.0
    last_yaw = measured_start_yaw
    accumulated = 0.0
    next_report = time.monotonic()
    deadline = time.monotonic() + max(60.0, math.radians(degrees) / yaw_rate_rps * 3.0)
    print(
        "{}: hedef {:.0f} derece, cap {:.1f} m, hiz {:.2f} m/s".format(
            label, degrees, CIRCLE_RADIUS_M * 2.0, forward_mps
        )
    )
    while accumulated < degrees and time.monotonic() < deadline:
        send_guided_target(
            mission,
            forward_mps,
            yaw_rate_rps=yaw_rate_rps,
        )
        attitude = read_attitude(mission)
        if attitude is not None:
            current_yaw, _ = attitude
            accumulated += wrap_degrees(current_yaw - last_yaw)
            last_yaw = current_yaw
        now = time.monotonic()
        if now >= next_report:
            print("  donulen {:6.1f}/{:.0f} derece".format(accumulated, degrees))
            next_report += 2.0
        time.sleep(GUIDED_SEND_PERIOD)
    if accumulated < degrees:
        raise RuntimeError("GUIDED daire zaman asimina ugradi")
    target_yaw = (start_heading + degrees) % 360.0
    guided_turn_to_target(mission, target_yaw, "{} cikis hizasi".format(label))
    return target_yaw


def run_action(mission, action, heading_target, label_prefix="Komut"):
    action_type = action["type"]
    if action_type == "straight":
        guided_straight(
            mission,
            float(action["seconds"]),
            int(action["pwm"]),
            "{}: duz ileri".format(label_prefix),
            target_yaw=heading_target,
        )
        return heading_target
    elif action_type == "right":
        return guided_turn_right(
            mission,
            float(action["degrees"]),
            "{}: saga donus".format(label_prefix),
            start_yaw=heading_target,
        )
    elif action_type == "circle":
        return guided_circle(
            mission,
            float(action["degrees"]),
            int(action["forward_pwm"]),
            "{}: daire".format(label_prefix),
            start_heading=heading_target,
        )
    else:
        raise ValueError("Bilinmeyen hareket tipi: {}".format(action_type))


def competition_actions():
    """20 saniyelik düzlüklere sahip yarışma parkurunu döndür."""
    return [
        {"type": "straight", "seconds": 20.0, "pwm": 1600},
        {"type": "right", "degrees": 90.0},
        {"type": "straight", "seconds": 20.0, "pwm": 1600},
        {"type": "circle", "degrees": 450.0, "forward_pwm": 1575},
        {"type": "straight", "seconds": 20.0, "pwm": 1600},
        {"type": "right", "degrees": 90.0},
        {"type": "straight", "seconds": 20.0, "pwm": 1600},
    ]


def run_competition_autonomous(mission):
    """SITL yerel konumuyla kapali parkuru baslangic noktasinda bitir."""
    request_local_position_10hz(mission)
    start_x, start_y, start_z = read_local_position(mission)
    start_yaw = mission.get_yaw_degrees()
    leg = AUTONOMOUS_LEG_LENGTH_M

    heading_1 = start_yaw % 360.0
    heading_2 = (start_yaw + 90.0) % 360.0
    heading_3 = (start_yaw + 180.0) % 360.0
    heading_4 = (start_yaw + 270.0) % 360.0

    def offset(position, distance, heading):
        x, y, z = position
        angle = math.radians(heading)
        return (
            x + distance * math.cos(angle),
            y + distance * math.sin(angle),
            z,
        )

    start = (start_x, start_y, start_z)
    corner_1 = offset(start, leg, heading_1)
    corner_2 = offset(corner_1, leg, heading_2)
    corner_3 = offset(corner_2, leg, heading_3)

    print(
        "Otonom baslangici kaydedildi: N/E {:.2f}/{:.2f} m, yaw {:.1f}".format(
            start_x, start_y, start_yaw
        )
    )
    guided_goto_position(
        mission,
        corner_1,
        heading_1,
        "Otonom 1/8: ilk duzluk",
        minimum_duration=20.0,
    )
    guided_turn_to_target(mission, heading_2, "Otonom 2/8: ilk sag 90")
    guided_goto_position(
        mission,
        corner_2,
        heading_2,
        "Otonom 3/8: ikinci duzluk",
        minimum_duration=20.0,
    )

    # Tam daire ayni konum ve yon civarinda kapanir. Ardindan kesin 90 derece
    # yerinde donus yapilir; 450 dereceyi hareketli donmek konum ofseti uretiyordu.
    guided_circle(
        mission,
        360.0,
        1575,
        "Otonom 4/8: bir tam daire",
        start_heading=heading_2,
    )
    guided_goto_position(
        mission,
        corner_2,
        heading_2,
        "Otonom 4/8: daire kapanis duzeltmesi",
        max_speed=0.12,
        timeout=30.0,
    )
    guided_turn_to_target(mission, heading_3, "Otonom 5/8: daire cikisi sag 90")
    guided_goto_position(
        mission,
        corner_3,
        heading_3,
        "Otonom 6/8: ucuncu duzluk",
        minimum_duration=20.0,
    )
    guided_turn_to_target(mission, heading_4, "Otonom 7/8: ikinci sag 90")
    guided_goto_position(
        mission,
        start,
        heading_4,
        "Otonom 8/8: baslangica donus",
        minimum_duration=20.0,
    )

    final_x, final_y, _ = read_local_position(mission)
    final_error = math.hypot(final_x - start_x, final_y - start_y)
    guided_stop(mission, target_yaw=heading_4)
    print("Otonom parkuru tamamlandi; baslangic hatasi {:.2f} m".format(final_error))


def play_actions(mission, actions, heading_target, label="Otonom"):
    print("{}: {} hareket basliyor".format(label, len(actions)))
    for index, action in enumerate(actions, start=1):
        heading_target = run_action(
            mission,
            action,
            heading_target,
            label_prefix="{} {}/{}".format(label, index, len(actions)),
        )
    guided_stop(mission)
    print("{} parkuru tamamlandi".format(label))
    return heading_target


def save_actions(actions, name):
    RECORD_DIR.mkdir(parents=True, exist_ok=True)
    path = RECORD_DIR / "{}.json".format(safe_name(name))
    payload = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "actions": actions,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Kaydedildi: {}".format(path))


def load_actions(name):
    path = RECORD_DIR / "{}.json".format(safe_name(name))
    payload = json.loads(path.read_text(encoding="utf-8"))
    actions = payload.get("actions")
    if not isinstance(actions, list):
        raise ValueError("Kayit dosyasinda actions listesi yok")
    print("Yuklendi: {}".format(path))
    return actions


def command_loop(mission):
    actions = []
    heading_target = mission.get_yaw_degrees()
    print("GUIDED kontrol hazir; RC yaw darbesi ve yon kalibrasyonu kullanilmiyor")
    print_help()
    while True:
        raw = input("\nKUMANDA> ").strip()
        if not raw:
            continue
        parts = raw.split()
        command = parts[0].lower()
        try:
            if command in {"ileri", "i"}:
                if len(parts) not in {2, 3}:
                    raise ValueError("Kullanim: ileri SANIYE [PWM]")
                action = {
                    "type": "straight",
                    "seconds": float(parts[1]),
                    "pwm": int(parts[2]) if len(parts) == 3 else 1600,
                }
                heading_target = run_action(mission, action, heading_target)
                actions.append(action)
            elif command in {"sag", "s"}:
                if len(parts) != 2:
                    raise ValueError("Kullanim: sag DERECE")
                action = {"type": "right", "degrees": float(parts[1])}
                heading_target = run_action(mission, action, heading_target)
                actions.append(action)
            elif command in {"daire", "d"}:
                if len(parts) not in {2, 3}:
                    raise ValueError("Kullanim: daire DERECE [ILERI_PWM]")
                action = {
                    "type": "circle",
                    "degrees": float(parts[1]),
                    "forward_pwm": int(parts[2]) if len(parts) == 3 else 1575,
                }
                heading_target = run_action(mission, action, heading_target)
                actions.append(action)
            elif command == "otonom":
                run_competition_autonomous(mission)
                heading_target = mission.get_yaw_degrees()
            elif command == "liste":
                show_actions(actions)
            elif command == "geri":
                if actions:
                    print("Silindi: {}".format(actions.pop()))
                else:
                    print("Liste zaten bos")
            elif command == "temizle":
                actions.clear()
                print("Hareket listesi temizlendi")
            elif command == "kaydet":
                save_actions(
                    actions,
                    parts[1] if len(parts) > 1 else "",
                )
            elif command == "yukle":
                if len(parts) != 2:
                    raise ValueError("Kullanim: yukle KAYIT_ADI")
                actions = load_actions(parts[1])
                show_actions(actions)
            elif command == "oynat":
                if not actions:
                    print("Once hareket ekle veya kayit yukle")
                    continue
                heading_target = mission.get_yaw_degrees()
                heading_target = play_actions(
                    mission,
                    actions,
                    heading_target,
                    label="Oynat",
                )
            elif command == "dur":
                guided_stop(mission)
                print("GUIDED hiz sifirlandi ve mevcut yaw tutuluyor")
            elif command == "yardim":
                print_help()
            elif command in {"cikis", "q", "quit", "exit"}:
                return
            else:
                print("Bilinmeyen komut. 'yardim' yazabilirsin.")
        except Exception as exc:
            guided_stop(mission)
            print("HATA: {}".format(exc))


def main():
    mission = SitlMission()
    return_code = 0
    try:
        mission.connect()
        request_attitude_10hz(mission)
        mission.set_guided_mode()
        mission.arm()
        guided_stop(mission)
        command_loop(mission)
    except KeyboardInterrupt:
        print("\nKullanici tarafindan durduruldu")
        return_code = 130
    except Exception as exc:
        print("HATA: {}".format(exc), file=sys.stderr)
        return_code = 1
    finally:
        try:
            # Baglanti kapanmadan once GUIDED hiz hedefini birkac kez sifirla.
            # Bu, son hareket komutunun MAVLink hattinda kalmasini engeller.
            for _ in range(10):
                guided_stop(mission)
                time.sleep(0.05)
        except Exception as exc:
            print("Hiz sifirlama sirasinda hata: {}".format(exc), file=sys.stderr)
        try:
            mission.disarm()
        except Exception as exc:
            print("Disarm sirasinda hata: {}".format(exc), file=sys.stderr)
    return return_code


if __name__ == "__main__":
    sys.exit(main())
