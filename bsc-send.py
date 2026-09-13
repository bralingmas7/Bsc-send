from web3 import Web3
from datetime import datetime
import csv
import os

# ====================== KONFIG ======================
RPC_LIST = [
    "https://bsc-dataseed1.binance.org/",
    "https://bsc.publicnode.com",
    "https://rpc-bsc.blockmachine.io",
    "https://bsc.drpc.org",
    "https://1rpc.io/bnb",
]

TOKENS = {
    "1": {"name": "USDT", "address": "0x55d398326f99059fF775485246999027B3197955"},
    "2": {"name": "USDC", "address": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"},
    "3": {"name": "BNB",  "address": None},
}

ERC20_ABI = [
    {"constant": False, "inputs": [{"name": "to", "type": "address"}, {"name": "value", "type": "uint256"}],
     "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals",
     "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "account", "type": "address"}],
     "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol",
     "outputs": [{"name": "", "type": "string"}], "type": "function"},
]

HISTORY_FILE = "history.csv"

# ====================== UTIL ======================
def mask_addr(addr: str) -> str:
    a = addr.strip()
    if len(a) < 12:
        return a
    return f"{a[:6]}***{a[-4:]}"

def get_web3():
    for rpc in RPC_LIST:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 12}))
            if w3.is_connected():
                print(f"✅ RPC terhubung")
                return w3
        except:
            continue
    raise Exception("Semua RPC gagal")

def load_list(path: str):
    try:
        with open(path, "r") as f:
            return [x.strip() for x in f if x.strip() and not x.startswith("#")]
    except FileNotFoundError:
        print(f"❌ File {path} tidak ditemukan")
        return []

def pilih_dari_list(items, judul):
    print(f"\n{judul}")
    for i, item in enumerate(items, 1):
        print(f"  [{i}] {mask_addr(item)}")
    if len(items) == 1:
        print(f"→ Dipilih otomatis: {mask_addr(items[0])}")
        return items[0]
    while True:
        p = input(f"Pilih nomor (1-{len(items)}): ").strip()
        if p.isdigit() and 1 <= int(p) <= len(items):
            return items[int(p) - 1]
        print("Pilihan tidak valid")

def get_balance(w3, wallet, token_addr):
    wallet = w3.to_checksum_address(wallet)
    if token_addr is None:
        bal = w3.eth.get_balance(wallet)
        return bal, 18, "BNB"
    contract = w3.eth.contract(address=w3.to_checksum_address(token_addr), abi=ERC20_ABI)
    bal = contract.functions.balanceOf(wallet).call()
    dec = contract.functions.decimals().call()
    try:
        sym = contract.functions.symbol().call()
    except:
        sym = "TOKEN"
    return bal, dec, sym

def append_history(row: dict):
    file_exists = os.path.isfile(HISTORY_FILE)
    with open(HISTORY_FILE, "a", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["waktu", "dari", "ke", "token", "jumlah", "tx_hash", "gas_bnb", "status"]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

# ====================== MAIN ======================
def main():
    print("=" * 52)
    print("           BSC SEND TOKEN")
    print("=" * 52)

    w3 = get_web3()

    # 1. Pengirim dari wallet.txt
    wallets = load_list("wallet.txt")
    if not wallets:
        return
    from_addr = w3.to_checksum_address(pilih_dari_list(wallets, "👤 Wallet pengirim (wallet.txt):"))

    # 2. Pilih token
    print("\n🪙 Pilih token:")
    for k, v in TOKENS.items():
        print(f"  [{k}] {v['name']}")
    while True:
        t = input("Pilih: ").strip()
        if t in TOKENS:
            token = TOKENS[t]
            break
        print("Tidak valid")

    token_name = token["name"]
    token_addr = token["address"]

    # 3. Tampilkan balance (tanpa private key)
    try:
        bal_wei, decimals, symbol = get_balance(w3, from_addr, token_addr)
        balance = bal_wei / (10 ** decimals)
        print(f"\n💰 Balance {symbol}: {balance:,.6f}")
    except Exception as e:
        print(f"❌ Gagal baca balance: {e}")
        return

    if bal_wei == 0:
        print("Balance kosong, tidak bisa kirim.")
        return

    # 4. Penerima dari address.txt
    recipients = load_list("address.txt")
    if not recipients:
        return
    to_addr = w3.to_checksum_address(pilih_dari_list(recipients, "📍 Wallet penerima (address.txt):"))

    # 5. Nominal
    print("\nPilih nominal:")
    print("  [1] Ketik manual")
    print("  [2] Max (semua)")
    mode = input("Pilih: ").strip()

    amount = None
    amount_wei = None

    if mode == "1":
        while True:
            try:
                amount = float(input("Masukkan jumlah: ").strip())
                if amount > 0:
                    amount_wei = int(amount * (10 ** decimals))
                    if amount_wei > bal_wei:
                        print("Melebihi balance")
                        continue
                    break
            except:
                print("Jumlah tidak valid")
    elif mode == "2":
        amount_wei = bal_wei
        amount = balance
    else:
        print("Pilihan tidak valid")
        return

    # Estimasi gas
    gas_limit = 21000 if token_addr is None else 100000
    gas_price = w3.eth.gas_price
    est_gas_bnb = (gas_limit * gas_price) / 1e18

    # Jika BNB max, sisakan gas
    if mode == "2" and token_addr is None:
        fee = gas_limit * gas_price
        if bal_wei <= fee:
            print("❌ BNB tidak cukup untuk gas")
            return
        amount_wei = bal_wei - fee
        amount = amount_wei / 1e18

    # 6. Preview
    print("\n" + "=" * 52)
    print("PREVIEW")
    print("=" * 52)
    print(f"Dari     : {mask_addr(from_addr)}")
    print(f"Ke       : {mask_addr(to_addr)}")
    print(f"Token    : {symbol}")
    print(f"Jumlah   : {amount:,.6f} {symbol}")
    print(f"Est. Gas : \~{est_gas_bnb:.6f} BNB")
    print("=" * 52)

    if input("\nLanjut? (ok/y): ").strip().lower() not in ("ok", "y", "yes"):
        print("Dibatalkan.")
        return

    # 7. Private key
    pk = input("\nMasukkan private key: ").strip()
    if not pk.startswith("0x") and len(pk) == 64:
        pk = "0x" + pk

    try:
        acc = w3.eth.account.from_key(pk)
    except Exception as e:
        print(f"❌ Private key invalid: {e}")
        return

    if acc.address.lower() != from_addr.lower():
        print("❌ Private key tidak cocok dengan wallet pengirim yang dipilih!")
        print(f"   PK → {mask_addr(acc.address)}")
        print(f"   Pilih → {mask_addr(from_addr)}")
        return

    # 8. Kirim
    try:
        nonce = w3.eth.get_transaction_count(from_addr)

        if token_addr is None:
            tx = {
                "nonce": nonce,
                "to": to_addr,
                "value": amount_wei,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "chainId": 56,
            }
        else:
            contract = w3.eth.contract(
                address=w3.to_checksum_address(token_addr), abi=ERC20_ABI
            )
            tx = contract.functions.transfer(to_addr, amount_wei).build_transaction({
                "from": from_addr,
                "nonce": nonce,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "chainId": 56,
            })

        signed = w3.eth.account.sign_transaction(tx, pk)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hex = tx_hash.hex()

        print(f"\n✅ BERHASIL")
        print(f"TX   : {tx_hex}")
        print(f"Link : https://bscscan.com/tx/{tx_hex}")

        append_history({
            "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dari": from_addr,
            "ke": to_addr,
            "token": symbol,
            "jumlah": f"{amount:.6f}",
            "tx_hash": tx_hex,
            "gas_bnb": f"{est_gas_bnb:.6f}",
            "status": "success",
        })
        print("📝 Disimpan ke history.csv")

    except Exception as e:
        print(f"❌ Gagal kirim: {e}")
        append_history({
            "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dari": from_addr,
            "ke": to_addr,
            "token": symbol,
            "jumlah": f"{amount:.6f}",
            "tx_hash": "",
            "gas_bnb": f"{est_gas_bnb:.6f}",
            "status": f"failed: {e}",
        })

if __name__ == "__main__":
    main()
