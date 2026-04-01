import os
from pymavlink import DFReader

LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', '00000001.BIN')

log = DFReader.DFReader_binary(LOG_FILE)

msg_types = {}
while True:
    msg = log.recv_msg()
    if msg is None:
        break
    t = msg.get_type()
    msg_types[t] = msg_types.get(t, 0) + 1

print("Знайдені типи повідомлень:")
for name, cnt in sorted(msg_types.items(), key=lambda x: -x[1]):
    print(f"  {name:10s} — {cnt} записів")
