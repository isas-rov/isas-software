#!/usr/bin/env python3
"""ArduSub SITL icin TEKNOFEST hareket parkuru provasi.

Bu betik yalnizca yerel ArduSub SITL portuna (127.0.0.1:5762) baglanir.
Gercek aracta kullanilmak uzere hazirlanmamistir. Daire capi, yalnizca PWM ve
IMU ile garanti edilemez; gercek aracta kamera/konum geri bildirimi gerekir.
"""

import math
import sys
import time

from pymavlink import mavutil


SITL_ENDPOINT = "tcp:127.0.0.1:5762"
STRAIGHT_SECONDS = 20.0

NEUTRAL_FORWARD = 0
NEUTRAL_YAW = 0
NEUTRAL_VERTICAL = 500
FORWARD_CONTROL = 200
CIRCLE_FORWARD_CONTROL = 150
YAW_TEST_CONTROL = 200

CONTROL_PERIOD = 0.10
TURN_ACTIVE_CONTROL = 200
YAW_ALIGN_TOLERANCE = 2.0


def wrap_degrees(angle):
    """Acıyı -180 ile +180 derece araligina getirir."""
    return (angle + 180.0) % 360.0 - 180.0


class SitlMission:
    def __init__(self, endpoint=SITL_ENDPOINT):
        self.master = None
        self.endpoint = endpoint
        self.right_yaw_control = YAW_TEST_CONTROL

    def connect(self):
        print("[1/8] ArduSub SITL bekleniyor: {}".format(self.endpoint))
        self.master = mavutil.mavlink_connection(
            self.endpoint,
            source_system=255,
            autoreconnect=False,
        )
        heartbeat = self.master.wait_heartbeat(timeout=15)
        if heartbeat is None:
            raise RuntimeError("15 saniye icinde SITL heartbeat alinmadi")
        if heartbeat.type != mavutil.mavlink.MAV_TYPE_SUBMARINE:
            raise RuntimeError(
                "Baglanan arac SUBMARINE degil (MAV_TYPE={})".format(
                    heartbeat.type
                )
            )
        print(
            "Baglandi: system={}, component={}".format(
                self.master.target_system,
                self.master.target_component,
            )
        )

    def send_controls(
        self,
        yaw_control=NEUTRAL_YAW,
        forward_control=NEUTRAL_FORWARD,
    ):
        """ArduSub'a dogrudan MAVLink MANUAL_CONTROL mesaji gonderir."""
        self.master.mav.manual_control_send(
            self.master.target_system,
            int(forward_control),  # x: ileri/geri
            0,  # y: yanal
            NEUTRAL_VERTICAL,  # z: ArduSub'ta 500 dikey notr
            int(yaw_control),  # r: yaw
            0,  # buttons
        )

    def neutral(self, duration=0.8):
        end_time = time.monotonic() + duration
        while time.monotonic() < end_time:
            self.send_controls()
            time.sleep(CONTROL_PERIOD)

    def set_stabilize_mode(self):
        mapping = self.master.mode_mapping() or {}
        mode_id = mapping.get("STABILIZE")
        if mode_id is None:
            raise RuntimeError("ArduSub STABILIZE modu bulunamadi")

        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id,
        )
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            heartbeat = self.master.recv_match(
                type="HEARTBEAT", blocking=True, timeout=1
            )
            if heartbeat is not None and heartbeat.custom_mode == mode_id:
                print("Mod: STABILIZE")
                return
        raise RuntimeError("STABILIZE moda gecis dogrulanamadi")

    def set_guided_mode(self):
        mapping = self.master.mode_mapping() or {}
        mode_id = mapping.get("GUIDED")
        if mode_id is None:
            raise RuntimeError("ArduSub GUIDED modu bulunamadi")

        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id,
        )
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            heartbeat = self.master.recv_match(
                type="HEARTBEAT", blocking=True, timeout=1
            )
            if heartbeat is not None and heartbeat.custom_mode == mode_id:
                print("Mod: GUIDED")
                return
        raise RuntimeError("GUIDED moda gecis dogrulanamadi")

    def arm(self):
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
        )
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            heartbeat = self.master.recv_match(
                type="HEARTBEAT", blocking=True, timeout=1
            )
            if heartbeat is not None and (
                heartbeat.base_mode
                & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
            ):
                print("Sanal arac ARMED")
                return
        raise RuntimeError("Arm islemi 10 saniye icinde dogrulanamadi")

    def disarm(self):
        if self.master is None:
            return
        self.neutral()
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        )
        print("Sanal arac DISARM komutu aldi")

    def get_attitude_message(self, timeout=3.0):
        """Kuyruktaki eski ornekleri atip en guncel ATTITUDE mesajini dondurur."""
        message = None
        while True:
            queued = self.master.recv_match(type="ATTITUDE", blocking=False)
            if queued is None:
                break
            message = queued
        if message is None:
            message = self.master.recv_match(
                type="ATTITUDE", blocking=True, timeout=timeout
            )
            while True:
                queued = self.master.recv_match(type="ATTITUDE", blocking=False)
                if queued is None:
                    break
                message = queued
        if message is None:
            raise RuntimeError("ATTITUDE/yaw verisi alinamadi")
        return message

    def get_yaw_degrees(self, timeout=3.0):
        message = self.get_attitude_message(timeout=timeout)
        return math.degrees(message.yaw) % 360.0

    def calibrate_right_direction(self):
        """Pozitif MANUAL_CONTROL yaw komutunun donus yonunu SITL'de olcer."""
        print("Yaw yonu olculuyor (kisa bir yerinde donus olacak)")
        last_yaw = self.get_yaw_degrees()
        initial_yaw = last_yaw
        accumulated = 0.0
        end_time = time.monotonic() + 1.5
        while time.monotonic() < end_time:
            self.send_controls(yaw_control=YAW_TEST_CONTROL)
            current_yaw = self.get_yaw_degrees(timeout=1.0)
            accumulated += wrap_degrees(current_yaw - last_yaw)
            last_yaw = current_yaw
            time.sleep(CONTROL_PERIOD)
        self.neutral(duration=1.0)

        if abs(accumulated) < 2.0:
            raise RuntimeError("Yaw yon testi icin yeterli donus olusmadi")
        if accumulated > 0.0:
            self.right_yaw_control = YAW_TEST_CONTROL
        else:
            self.right_yaw_control = -YAW_TEST_CONTROL
        print(
            "Sag yaw komutu: {:+d} (test degisimi {:+.1f} derece)".format(
                self.right_yaw_control,
                accumulated,
            )
        )
        print("Yaw testi sonrasi ilk yone geri donuluyor")
        self.align_yaw(initial_yaw)

    def straight(
        self,
        seconds,
        target_yaw,
        label,
        forward_control=FORWARD_CONTROL,
    ):
        self.align_yaw(target_yaw)
        print(
            "{}: {:.0f} saniye ileri, hedef yaw {:.1f} derece".format(
                label, seconds, target_yaw
            )
        )
        start_time = time.monotonic()
        next_report = start_time
        while True:
            now = time.monotonic()
            elapsed = now - start_time
            if elapsed >= seconds:
                break

            current_yaw = self.get_yaw_degrees(timeout=1.0)
            error = wrap_degrees(target_yaw - current_yaw)
            right_sign = 1 if self.right_yaw_control > 0 else -1
            direction = 1 if error > 0.0 else -1
            cycle = int(elapsed / CONTROL_PERIOD)
            if abs(error) > 15.0:
                active = cycle % 2 == 0
            elif abs(error) > 5.0:
                active = cycle % 4 == 0
            elif abs(error) > YAW_ALIGN_TOLERANCE:
                active = cycle % 8 == 0
            else:
                active = False
            self.send_controls(
                yaw_control=(
                    right_sign * direction * TURN_ACTIVE_CONTROL
                    if active
                    else NEUTRAL_YAW
                ),
                forward_control=forward_control,
            )

            if now >= next_report:
                remaining = max(0.0, seconds - elapsed)
                print(
                    "  kalan {:4.1f} sn | yaw {:6.1f} | hata {:+5.1f}".format(
                        remaining, current_yaw, error
                    )
                )
                next_report += 5.0
            time.sleep(CONTROL_PERIOD)
        self.neutral()

    def align_yaw(self, target_yaw):
        """Donus sonrasi araci dusuk yaw hiziyla hedef aciya hizalar."""
        print("  son yaw hedefi: {:.1f} derece".format(target_yaw))
        deadline = time.monotonic() + 25.0
        stable_samples = 0
        right_sign = 1 if self.right_yaw_control > 0 else -1

        while time.monotonic() < deadline:
            current_yaw = self.get_yaw_degrees(timeout=1.0)
            error = wrap_degrees(target_yaw - current_yaw)
            if abs(error) <= YAW_ALIGN_TOLERANCE:
                stable_samples += 1
                self.send_controls()
                if stable_samples >= 1:
                    self.neutral(duration=0.3)
                    print(
                        "  yaw hizalandi: {:.1f} derece (hata {:+.1f})".format(
                            current_yaw, error
                        )
                    )
                    return
            else:
                stable_samples = 0
                direction = 1 if error > 0.0 else -1
                cycle = int(time.monotonic() / CONTROL_PERIOD)
                if abs(error) > 15.0:
                    active = True
                elif abs(error) > 5.0:
                    active = cycle % 2 == 0
                else:
                    active = cycle % 4 == 0
                self.send_controls(
                    yaw_control=(
                        right_sign * direction * TURN_ACTIVE_CONTROL
                        if active
                        else NEUTRAL_YAW
                    ),
                )
            time.sleep(CONTROL_PERIOD)
        raise RuntimeError("Son yaw acisi zamaninda hizalanamadi")

    def turn_right(self, degrees, target_yaw, forward_control, label):
        print("{}: saga toplam {:.0f} derece".format(label, degrees))
        last_yaw = self.get_yaw_degrees()
        accumulated = 0.0
        start_time = time.monotonic()
        next_report = start_time
        right_sign = 1 if self.right_yaw_control > 0 else -1

        while accumulated < degrees:
            remaining = max(0.0, degrees - accumulated)
            cycle = int((time.monotonic() - start_time) / CONTROL_PERIOD)
            if remaining > 25.0:
                active = True
            elif remaining > 10.0:
                active = cycle % 2 == 0
            else:
                active = cycle % 4 == 0
            self.send_controls(
                yaw_control=(
                    right_sign * TURN_ACTIVE_CONTROL
                    if active
                    else NEUTRAL_YAW
                ),
                forward_control=forward_control,
            )
            current_yaw = self.get_yaw_degrees(timeout=1.0)
            delta = wrap_degrees(current_yaw - last_yaw)
            last_yaw = current_yaw
            accumulated += delta

            if accumulated < -10.0:
                raise RuntimeError(
                    "Sag donus ters yone gidiyor; yaw yon testi kontrol edilmeli"
                )
            if time.monotonic() - start_time > max(90.0, degrees * 1.5):
                raise RuntimeError("Donus zaman asimina ugradi")

            now = time.monotonic()
            if now >= next_report:
                print(
                    "  donulen {:6.1f}/{:.0f} derece | yaw {:6.1f}".format(
                        accumulated, degrees, current_yaw
                    )
                )
                next_report += 5.0
            time.sleep(CONTROL_PERIOD)
        self.neutral(duration=1.5)
        self.align_yaw(target_yaw)

    def run(self):
        self.connect()
        self.set_stabilize_mode()
        self.neutral()
        print("Parkur 5 saniye sonra otomatik baslayacak")
        for remaining in range(5, 0, -1):
            print("  {}...".format(remaining))
            self.send_controls()
            time.sleep(1.0)
        self.arm()
        self.calibrate_right_direction()
        base_yaw = self.get_yaw_degrees()
        yaw_0 = base_yaw
        yaw_90 = (base_yaw + 90.0) % 360.0
        yaw_180 = (base_yaw + 180.0) % 360.0
        yaw_270 = (base_yaw + 270.0) % 360.0
        print(
            "Parkur yonleri: {:.1f} / {:.1f} / {:.1f} / {:.1f} derece".format(
                yaw_0, yaw_90, yaw_180, yaw_270
            )
        )

        print("[2/8] Parkur basladi")
        self.straight(STRAIGHT_SECONDS, yaw_0, "[2/8] Birinci duzluk")
        self.turn_right(
            90.0,
            yaw_90,
            NEUTRAL_FORWARD,
            "[3/8] Birinci sag donus",
        )
        self.straight(STRAIGHT_SECONDS, yaw_90, "[4/8] Ikinci duzluk")
        self.turn_right(
            450.0,
            yaw_180,
            CIRCLE_FORWARD_CONTROL,
            "[5/8] Bir tam daire + 90 derece cikis",
        )
        self.straight(STRAIGHT_SECONDS, yaw_180, "[6/8] Ucuncu duzluk")
        self.turn_right(
            90.0,
            yaw_270,
            NEUTRAL_FORWARD,
            "[7/8] Ikinci sag donus",
        )
        self.straight(STRAIGHT_SECONDS, yaw_270, "[8/8] Dorduncu duzluk")
        print("Parkur tamamlandi")


def main():
    mission = SitlMission()
    try:
        mission.run()
    except KeyboardInterrupt:
        print("\nKullanici tarafindan durduruldu")
        return_code = 130
    except Exception as exc:
        print("HATA: {}".format(exc), file=sys.stderr)
        return_code = 1
    else:
        return_code = 0
    finally:
        try:
            mission.disarm()
        except Exception as exc:
            print("Disarm sirasinda hata: {}".format(exc), file=sys.stderr)
    return return_code


if __name__ == "__main__":
    sys.exit(main())
