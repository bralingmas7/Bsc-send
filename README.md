# Bsc-send

Script Python untuk mengirim token di **BNB Smart Chain (BSC)** lewat terminal / Termux.

Mendukung **USDT**, **USDC**, dan **BNB** dengan alur interaktif: pilih pengirim, cek balance, pilih penerima, preview, baru input private key.

## Fitur

- Multi RPC BSC (otomatis ganti jika satu gagal)
- Baca pengirim dari `wallet.txt`
- Baca penerima dari `address.txt`
- Address ditampilkan ter-mask (`0x1234***abcd`)
- Cek balance **tanpa** private key
- Nominal manual atau max
- Preview transaksi + estimasi gas
- Validasi private key cocok dengan wallet pengirim
- Log transaksi ke `history.csv`

## Persyaratan

- Python 3.9+
- `web3`
- Koneksi internet
- Wallet pengirim punya **BNB** untuk gas

## Instalasi

### Termux (Android)

```bash
pkg update
pkg install python git
pip install web3

git clone https://github.com/bralingmas7/Bsc-send.git
cd Bsc-send
