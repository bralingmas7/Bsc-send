from web3 import Web3
from web3.exceptions import TimeExhausted
from datetime import datetime
from decimal import Decimal, InvalidOperation
import csv
import os
import subprocess

# ====================== KONFIG ======================

RPC_LIST = [
    "https://bsc-dataseed1.binance.org/",
    "https://bsc.publicnode.com",
    "https://rpc-bsc.blockmachine.io",
    "https://bsc.drpc.org",
    "https://1rpc.io/bnb",
]

TOKENS = {
    "1": {
        "name": "USDT",
        "address": "0x55d398326f99059fF775485246999027B3197955"
    },
    "2": {
        "name": "USDC",
        "address": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
    },
    "3": {
        "name": "BNB",
        "address": None
    },
}

ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [
            {"name": "", "type": "bool"}
        ],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [
            {"name": "", "type": "uint8"}
        ],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "account", "type": "address"}
        ],
        "name": "balanceOf",
        "outputs": [
            {"name": "", "type": "uint256"}
        ],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [
            {"name": "", "type": "string"}
        ],
        "type": "function"
    },
]

HISTORY_FILE = "history.csv"

# ====================== UTIL ======================

def mask_addr(addr: str) -> str:
    a = addr.strip()
    if len(a) < 12:
        return a
    return f"{a[:6]}***{a[-4:]}"


def copy_text(text):
    """
    Copy ke clipboard Android menggunakan Termux:API.
    Jika termux-clipboard-set tidak tersedia,
    tampilkan teks saja.
    """
    try:
        subprocess.run(
            ["termux-clipboard-set"],
            input=text,
            text=True,
            check=True
        )
        print("📋 Berhasil di-copy ke clipboard.")
    except Exception:
        print("⚠️ termux-clipboard-set tidak tersedia.")
        print("Teks:")
        print(text)


def copy_menu(tx_hash=None, tx_link=None, address=None):

    while True:

        print("\n📋 COPY MENU")

        if tx_hash:
            print("  [1] Copy TX Hash")

        if tx_link:
            print("  [2] Copy BscScan Link")

        if address:
            print("  [3] Copy Address Penerima")

        print("  [0] Selesai")

        pilih = input("Pilih: ").strip()

        if pilih == "1" and tx_hash:
            copy_text(tx_hash)

        elif pilih == "2" and tx_link:
            copy_text(tx_link)

        elif pilih == "3" and address:
            copy_text(address)

        elif pilih == "0":
            break

        else:
            print("Pilihan tidak valid.")


def get_web3():

    for rpc in RPC_LIST:

        try:

            print(f"🔌 Coba RPC: {rpc}")

            w3 = Web3(
                Web3.HTTPProvider(
                    rpc,
                    request_kwargs={"timeout": 12}
                )
            )

            if w3.is_connected():

                print(
                    f"✅ RPC terhubung | "
                    f"Block: {w3.eth.block_number}"
                )

                return w3

        except Exception:
            continue

    raise Exception("Semua RPC gagal")


def load_list(path: str):

    try:

        with open(path, "r") as f:

            return [
                x.strip()
                for x in f
                if x.strip()
                and not x.startswith("#")
            ]

    except FileNotFoundError:

        print(f"❌ File {path} tidak ditemukan")

        return []


def pilih_dari_list(items, judul):

    print(f"\n{judul}")

    for i, item in enumerate(items, 1):
        print(
            f"  [{i}] {mask_addr(item)}"
        )

    if len(items) == 1:

        print(
            f"→ Dipilih otomatis: "
            f"{mask_addr(items[0])}"
        )

        return items[0]

    while True:

        p = input(
            f"Pilih nomor (1-{len(items)}): "
        ).strip()

        if p.isdigit():

            nomor = int(p)

            if 1 <= nomor <= len(items):

                return items[nomor - 1]

        print("Pilihan tidak valid")


def get_balance(w3, wallet, token_addr):

    wallet = w3.to_checksum_address(wallet)

    if token_addr is None:

        bal = w3.eth.get_balance(wallet)

        return bal, 18, "BNB"

    contract = w3.eth.contract(
        address=w3.to_checksum_address(token_addr),
        abi=ERC20_ABI
    )

    bal = contract.functions.balanceOf(
        wallet
    ).call()

    dec = contract.functions.decimals().call()

    try:
        sym = contract.functions.symbol().call()

    except Exception:
        sym = "TOKEN"

    return bal, dec, sym


def append_history(row: dict):

    file_exists = os.path.isfile(
        HISTORY_FILE
    )

    with open(
        HISTORY_FILE,
        "a",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "waktu",
                "dari",
                "ke",
                "token",
                "jumlah",
                "tx_hash",
                "gas_bnb",
                "status"
            ]
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)


# ====================== MAIN ======================

def main():

    print("=" * 52)
    print("             BSC SEND TOKEN")
    print("          SAFE TRANSACTION MODE")
    print("=" * 52)

    # --------------------------------------------------
    # RPC
    # --------------------------------------------------

    try:

        w3 = get_web3()

    except Exception as e:

        print(f"❌ {e}")
        return

    # --------------------------------------------------
    # PENGIRIM
    # --------------------------------------------------

    wallets = load_list("wallet.txt")

    if not wallets:
        return

    try:

        from_addr = w3.to_checksum_address(
            pilih_dari_list(
                wallets,
                "👤 Wallet pengirim (wallet.txt):"
            )
        )

    except Exception as e:

        print(
            f"❌ Address pengirim tidak valid: {e}"
        )

        return

    # --------------------------------------------------
    # TOKEN
    # --------------------------------------------------

    print("\n🪙 Pilih token:")

    for k, v in TOKENS.items():

        print(
            f"  [{k}] {v['name']}"
        )

    while True:

        t = input("Pilih: ").strip()

        if t in TOKENS:

            token = TOKENS[t]

            break

        print("Tidak valid")

    token_name = token["name"]
    token_addr = token["address"]

    # --------------------------------------------------
    # BALANCE
    # --------------------------------------------------

    try:

        bal_wei, decimals, symbol = get_balance(
            w3,
            from_addr,
            token_addr
        )

        balance = (
            Decimal(bal_wei)
            / (Decimal(10) ** decimals)
        )

        print(
            f"\n💰 Balance {symbol}: "
            f"{balance:,.8f}"
        )

    except Exception as e:

        print(
            f"❌ Gagal baca balance: {e}"
        )

        return

    if bal_wei == 0:

        print(
            "❌ Balance kosong, tidak bisa kirim."
        )

        return

    # --------------------------------------------------
    # PENERIMA
    # --------------------------------------------------

    recipients = load_list("address.txt")

    if not recipients:
        return

    try:

        to_addr = w3.to_checksum_address(
            pilih_dari_list(
                recipients,
                "📍 Wallet penerima (address.txt):"
            )
        )

    except Exception as e:

        print(
            f"❌ Address penerima tidak valid: {e}"
        )

        return

    # --------------------------------------------------
    # NOMINAL
    # --------------------------------------------------

    print("\nPilih nominal:")

    print(
        "  [1] Ketik manual"
    )

    print(
        "  [2] Max (semua)"
    )

    mode = input(
        "Pilih: "
    ).strip()

    amount = None
    amount_wei = None

    if mode == "1":

        while True:

            try:

                raw = input(
                    f"Masukkan jumlah {symbol}: "
                ).strip()

                amount = Decimal(raw)

                if amount <= 0:

                    print(
                        "Jumlah harus lebih besar dari 0"
                    )

                    continue

                amount_wei = int(
                    amount
                    * (Decimal(10) ** decimals)
                )

                if amount_wei > bal_wei:

                    print(
                        "Melebihi balance"
                    )

                    continue

                break

            except (
                InvalidOperation,
                ValueError
            ):

                print(
                    "Jumlah tidak valid"
                )

    elif mode == "2":

        amount_wei = bal_wei

        amount = (
            Decimal(amount_wei)
            / (Decimal(10) ** decimals)
        )

    else:

        print(
            "Pilihan tidak valid"
        )

        return

    # --------------------------------------------------
    # GAS PRICE
    # --------------------------------------------------

    try:

        gas_price = w3.eth.gas_price

    except Exception as e:

        print(
            f"❌ Gagal membaca gas price: {e}"
        )

        return

    gas_gwei = (
        Decimal(gas_price)
        / Decimal(10 ** 9)
    )

    print(
        f"\n⛽ Gas price: "
        f"{gas_gwei:.3f} Gwei"
    )

    # --------------------------------------------------
    # PRIVATE KEY
    # --------------------------------------------------

    pk = input(
        "\nMasukkan private key: "
    ).strip()

    if not pk.startswith("0x"):

        if len(pk) == 64:
            pk = "0x" + pk

    try:

        acc = w3.eth.account.from_key(pk)

    except Exception as e:

        print(
            f"❌ Private key invalid: {e}"
        )

        return

    if acc.address.lower() != from_addr.lower():

        print(
            "❌ Private key tidak cocok "
            "dengan wallet pengirim!"
        )

        print(
            f"   PK     → "
            f"{mask_addr(acc.address)}"
        )

        print(
            f"   Pilih  → "
            f"{mask_addr(from_addr)}"
        )

        return

    # --------------------------------------------------
    # NONCE
    # --------------------------------------------------

    try:

        nonce_latest = (
            w3.eth.get_transaction_count(
                from_addr,
                "latest"
            )
        )

        nonce_pending = (
            w3.eth.get_transaction_count(
                from_addr,
                "pending"
            )
        )

        print(
            f"\n🔢 Nonce confirmed : "
            f"{nonce_latest}"
        )

        print(
            f"🔢 Nonce pending   : "
            f"{nonce_pending}"
        )

        if nonce_pending > nonce_latest:

            print(
                "\n⚠️ Ada transaksi "
                "yang masih pending."
            )

            print(
                "Script akan menggunakan "
                "nonce pending."
            )

        nonce = nonce_pending

    except Exception as e:

        print(
            f"❌ Gagal mendapatkan nonce: {e}"
        )

        return

    # --------------------------------------------------
    # BUILD TRANSACTION
    # --------------------------------------------------

    try:

        if token_addr is None:

            # ==========================================
            # BNB
            # ==========================================

            # Untuk BNB, gas normal 21000
            gas_limit = 21000

            fee = (
                gas_limit
                * gas_price
            )

            if mode == "2":

                if bal_wei <= fee:

                    print(
                        "❌ BNB tidak cukup "
                        "untuk gas."
                    )

                    return

                amount_wei = (
                    bal_wei - fee
                )

                amount = (
                    Decimal(amount_wei)
                    / Decimal(10 ** 18)
                )

            else:

                if (
                    amount_wei + fee
                    > bal_wei
                ):

                    print(
                        "❌ BNB tidak cukup "
                        "untuk jumlah + gas."
                    )

                    return

            # Estimate gas
            estimate_tx = {
                "from": from_addr,
                "to": to_addr,
                "value": amount_wei,
            }

            try:

                estimated = (
                    w3.eth.estimate_gas(
                        estimate_tx
                    )
                )

                gas_limit = max(
                    21000,
                    int(
                        estimated * 1.10
                    )
                )

            except Exception:

                gas_limit = 21000

            fee = (
                gas_limit
                * gas_price
            )

            if (
                amount_wei + fee
                > bal_wei
            ):

                print(
                    "❌ BNB tidak cukup "
                    "untuk jumlah + gas."
                )

                return

            tx = {

                "nonce": nonce,

                "to": to_addr,

                "value": amount_wei,

                "gas": gas_limit,

                "gasPrice": gas_price,

                "chainId": 56
            }

        else:

            # ==========================================
            # ERC20
            # ==========================================

            contract = w3.eth.contract(

                address=w3.to_checksum_address(
                    token_addr
                ),

                abi=ERC20_ABI
            )

            # Build tanpa gas dahulu
            test_tx = (
                contract.functions.transfer(
                    to_addr,
                    amount_wei
                ).build_transaction({

                    "from": from_addr,

                    "nonce": nonce,

                    "gasPrice": gas_price,

                    "chainId": 56
                })
            )

            # Estimate gas sebenarnya
            estimated = (
                w3.eth.estimate_gas(
                    test_tx
                )
            )

            # Margin 15%
            gas_limit = max(
                21000,
                int(
                    estimated * 1.15
                )
            )

            fee = (
                gas_limit
                * gas_price
            )

            bnb_balance = (
                w3.eth.get_balance(
                    from_addr
                )
            )

            if bnb_balance < fee:

                print(
                    "\n❌ BNB untuk gas "
                    "tidak cukup."
                )

                print(
                    f"Saldo BNB : "
                    f"{Decimal(bnb_balance) / Decimal(10**18):.8f}"
                )

                print(
                    f"Max gas   : "
                    f"{Decimal(fee) / Decimal(10**18):.8f}"
                )

                return

            tx = (
                contract.functions.transfer(
                    to_addr,
                    amount_wei
                ).build_transaction({

                    "from": from_addr,

                    "nonce": nonce,

                    "gas": gas_limit,

                    "gasPrice": gas_price,

                    "chainId": 56
                })
            )

        max_gas_bnb = (
            Decimal(gas_limit)
            * Decimal(gas_price)
            / Decimal(10 ** 18)
        )

    except Exception as e:

        print(
            "\n❌ TRANSAKSI GAGAL DI-ESTIMATE"
        )

        print(e)

        print(
            "\n⚠️ Transaksi BELUM dikirim."
        )

        return

    # --------------------------------------------------
    # PREVIEW
    # --------------------------------------------------

    print(
        "\n" + "=" * 52
    )

    print(
        "PREVIEW"
    )

    print(
        "=" * 52
    )

    print(
        f"Dari     : "
        f"{mask_addr(from_addr)}"
    )

    print(
        f"Ke       : "
        f"{mask_addr(to_addr)}"
    )

    print(
        f"Token    : "
        f"{symbol}"
    )

    print(
        f"Jumlah   : "
        f"{amount:,.8f} {symbol}"
    )

    print(
        f"Nonce    : "
        f"{nonce}"
    )

    print(
        f"Gas limit: "
        f"{gas_limit}"
    )

    print(
        f"Gas price: "
        f"{gas_gwei:.3f} Gwei"
    )

    print(
        f"Max gas  : "
        f"{max_gas_bnb:.8f} BNB"
    )

    print(
        "=" * 52
    )

    confirm = input(
        "\nLanjut? (ok/y): "
    ).strip().lower()

    if confirm not in (
        "ok",
        "y",
        "yes"
    ):

        print(
            "Dibatalkan."
        )

        return

    # --------------------------------------------------
    # SIGN
    # --------------------------------------------------

    try:

        signed = (
            w3.eth.account.sign_transaction(
                tx,
                pk
            )
        )

    except Exception as e:

        print(
            f"❌ Gagal signing: {e}"
        )

        return

    # --------------------------------------------------
    # BROADCAST
    # --------------------------------------------------

    try:

        print(
            "\n📡 Broadcast transaksi..."
        )

        tx_hash = (
            w3.eth.send_raw_transaction(
                signed.raw_transaction
            )
        )

        tx_hex = tx_hash.hex()

        tx_link = (
            f"https://bscscan.com/tx/{tx_hex}"
        )

        print(
            "\n📨 TRANSAKSI DITERIMA RPC"
        )

        print(
            f"TX   : {tx_hex}"
        )

        print(
            f"Link : {tx_link}"
        )

        print(
            "\n⏳ Menunggu receipt..."
        )

    except Exception as e:

        print(
            "\n❌ BROADCAST GAGAL"
        )

        print(e)

        append_history({

            "waktu":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "dari":
                from_addr,

            "ke":
                to_addr,

            "token":
                symbol,

            "jumlah":
                f"{amount:.8f}",

            "tx_hash":
                "",

            "gas_bnb":
                f"{max_gas_bnb:.8f}",

            "status":
                f"broadcast_failed: {e}"
        })

        return

    # --------------------------------------------------
    # WAIT RECEIPT
    # --------------------------------------------------

    try:

        receipt = (
            w3.eth.wait_for_transaction_receipt(
                tx_hash,
                timeout=180,
                poll_latency=2
            )
        )

    except TimeExhausted:

        print(
            "\n⚠️ TRANSAKSI MASIH PENDING"
        )

        print(
            "Belum masuk block dalam "
            "180 detik."
        )

        print(
            "\n⚠️ JANGAN langsung kirim ulang."
        )

        append_history({

            "waktu":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "dari":
                from_addr,

            "ke":
                to_addr,

            "token":
                symbol,

            "jumlah":
                f"{amount:.8f}",

            "tx_hash":
                tx_hex,

            "gas_bnb":
                "",

            "status":
                "pending"
        })

        copy_menu(
            tx_hash=tx_hex,
            tx_link=tx_link,
            address=to_addr
        )

        return

    except Exception as e:

        print(
            f"\n❌ Gagal membaca receipt: {e}"
        )

        return

    # --------------------------------------------------
    # HASIL RECEIPT
    # --------------------------------------------------

    gas_used = receipt["gasUsed"]

    actual_gas_bnb = (
        Decimal(gas_used)
        * Decimal(gas_price)
        / Decimal(10 ** 18)
    )

    print(
        "\n" + "=" * 52
    )

    # ==================================================
    # SUCCESS
    # ==================================================

    if receipt["status"] == 1:

        print(
            "✅ TRANSAKSI SUCCESS"
        )

        print(
            "=" * 52
        )

        print(
            f"TX        : {tx_hex}"
        )

        print(
            f"Block     : {receipt['blockNumber']}"
        )

        print(
            f"Nonce     : {nonce}"
        )

        print(
            f"Gas used  : {gas_used}"
        )

        print(
            f"Gas aktual: "
            f"{actual_gas_bnb:.8f} BNB"
        )

        # ----------------------------------------------
        # Cek Transfer event untuk token
        # ----------------------------------------------

        if token_addr is not None:

            try:

                logs = (
                    contract.events.Transfer()
                    .process_receipt(
                        receipt
                    )
                )

                found = False

                for event in logs:

                    args = event["args"]

                    event_from = args["from"]
                    event_to = args["to"]
                    event_value = args["value"]

                    if (
                        event_from.lower()
                        == from_addr.lower()
                        and
                        event_to.lower()
                        == to_addr.lower()
                        and
                        event_value
                        == amount_wei
                    ):

                        found = True
                        break

                if found:

                    print(
                        "\n🟢 Transfer token "
                        "terdeteksi."
                    )

                else:

                    print(
                        "\n⚠️ TX sukses, "
                        "tetapi Transfer event "
                        "tidak ditemukan."
                    )

            except Exception as e:

                print(
                    "\n⚠️ Gagal membaca "
                    f"Transfer event: {e}"
                )

        append_history({

            "waktu":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "dari":
                from_addr,

            "ke":
                to_addr,

            "token":
                symbol,

            "jumlah":
                f"{amount:.8f}",

            "tx_hash":
                tx_hex,

            "gas_bnb":
                f"{actual_gas_bnb:.8f}",

            "status":
                "success"
        })

        print(
            "\n📝 Disimpan ke history.csv"
        )

        # COPY MENU
        copy_menu(
            tx_hash=tx_hex,
            tx_link=tx_link,
            address=to_addr
        )

    # ==================================================
    # REVERTED
    # ==================================================

    else:

        print(
            "❌ TRANSAKSI REVERTED"
        )

        print(
            "=" * 52
        )

        print(
            f"TX        : {tx_hex}"
        )

        print(
            f"Block     : {receipt['blockNumber']}"
        )

        print(
            f"Nonce     : {nonce}"
        )

        print(
            f"Gas used  : {gas_used}"
        )

        print(
            f"Gas aktual: "
            f"{actual_gas_bnb:.8f} BNB"
        )

        print(
            "\n⚠️ Transaksi masuk blockchain "
            "tetapi eksekusinya gagal."
        )

        print(
            "Gas tetap terpakai."
        )

        append_history({

            "waktu":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "dari":
                from_addr,

            "ke":
                to_addr,

            "token":
                symbol,

            "jumlah":
                f"{amount:.8f}",

            "tx_hash":
                tx_hex,

            "gas_bnb":
                f"{actual_gas_bnb:.8f}",

            "status":
                "reverted"
        })

        print(
            "\n📝 Disimpan ke history.csv"
        )

        copy_menu(
            tx_hash=tx_hex,
            tx_link=tx_link,
            address=to_addr
        )


if __name__ == "__main__":
    main()
