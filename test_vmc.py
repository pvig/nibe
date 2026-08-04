from nibe_client import NibeClient
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient('192.168.1.13', port=502)
client.connect()

reg104 = client.read_holding_registers(104, 1).registers[0]
reg5391 = client.read_holding_registers(5391, 1).registers[0]

print(f"Register 104 (Mode): {reg104}")
print(f"Register 5391 (Boost 1): {reg5391}")

client.close()
