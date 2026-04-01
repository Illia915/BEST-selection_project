from pymavlink import DFReader

log = DFReader.DFReader_binary('data/00000001.BIN')

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