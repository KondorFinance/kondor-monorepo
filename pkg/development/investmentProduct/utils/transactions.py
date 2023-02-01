from pyteal import *
from beaker import *


class Transactions:

    @internal(TealType.none)
    def do_create_nft(self):
        return Seq(
            InnerTxnBuilder.Execute(
                {
                    TxnField.type_enum: TxnType.AssetConfig,
                    TxnField.config_asset_total: Int(1),
                    TxnField.config_asset_decimals: Int(0),
                    TxnField.config_asset_default_frozen: Int(0),
                    TxnField.config_asset_unit_name: Bytes("KONDOR"),
                    TxnField.config_asset_name: Bytes("kondor.finance NFT"),
                    TxnField.config_asset_url: Bytes("https://kondor.finance/nft"),
                    TxnField.config_asset_manager: self.address,
                    TxnField.config_asset_reserve: self.address,
                    TxnField.fee: Int(0)
                }),
            InnerTxn.created_asset_id(),
        )
        
    @internal(TealType.none)
    def do_axfer(self, rx, aid, amt):
        return InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: aid,
                TxnField.asset_amount: amt,
                TxnField.asset_receiver: rx,
                TxnField.fee: Int(0),
            }
        )