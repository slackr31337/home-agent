"""CANbus logger"""

import time

import usb
import can

##########################################
def log_packets():
    """Log packets from CANbus adapter"""
    print("Starting log_packets()")
    dev = usb.core.find(idVendor=0x1D50, idProduct=0x606F)

    with can.Bus(  # pylint:disable=abstract-class-instantiated
        bustype="gs_usb",
        channel=dev.product,
        bus=dev.bus,
        address=dev.address,
        bitrate=250000,
    ) as _bus:
        print(f"Device channel: {dev.product} bus: {dev.bus} address: {dev.address}")

        while True:
            msg = _bus.recv(1)
            if msg is not None:
                print_packet(msg)
            else:
                print(f"[{time.time():.6f}] No packets")


##########################################
def print_packet(_msg: can.Message):
    """Format data in readable output"""
    _msg_id = "0x{0:0{1}X}".format(  # pylint: disable=consider-using-f-string
        _msg.arbitration_id,
        8 if _msg.is_extended_id else 3,
    )
    _id = str(_msg.arbitration_id).rjust(4, "0")

    data = f"[{time.time():.6f}] Packet:    [{_id}] {_msg_id}"
    for idx, _byte in enumerate(_msg.data):  # pylint: disable=unused-variable
        data += f" {_byte:02X}"

    print(data)


##########################################
if __name__ == "__main__":
    log_packets()
