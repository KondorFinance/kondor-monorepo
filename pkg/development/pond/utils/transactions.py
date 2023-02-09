from pyteal import *
from beaker import *


class Transactions:

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

    @internal(TealType.none)
    def do_opt_in(self, aid):
        # return self.do_axfer(self.address, aid, Int(0))
        return InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: aid,
                TxnField.asset_amount: Int(0),
                TxnField.asset_receiver: self.address,
                TxnField.fee: Int(0),
            }
        )

    @internal(TealType.uint64)
    def do_create_pond_token(self, a, b):
        return Seq(
            (una := AssetParam.unitName(a)),
            (unb := AssetParam.unitName(b)),
            Assert(
                una.hasValue(), 
                unb.hasValue()
            ),
            InnerTxnBuilder.Execute(
                {
                    TxnField.type_enum: TxnType.AssetConfig,
                    TxnField.config_asset_name: Concat(
                        Bytes("Kondor-V1-POND-"), 
                        una.value(), 
                        Bytes("-"), 
                        unb.value()
                    ),
                    TxnField.config_asset_unit_name: Bytes("POND"),
                    TxnField.config_asset_total: self.total_supply,
                    TxnField.config_asset_decimals: Int(3),
                    TxnField.config_asset_manager: self.address,
                    TxnField.config_asset_reserve: self.address,
                    TxnField.fee: Int(0),
                }
            ),
            InnerTxn.created_asset_id(),
        )
    
    @internal(TealType.uint64)
    def do_create_token(self, a, b, a_name, u_name):
        return Seq(
            (una := AssetParam.unitName(a)),
            (unb := AssetParam.unitName(b)),
            Assert(
                una.hasValue(), 
                unb.hasValue()
            ),
            InnerTxnBuilder.Execute(
                {
                    TxnField.type_enum: TxnType.AssetConfig,
                    TxnField.config_asset_name: a_name,
                    TxnField.config_asset_unit_name: u_name,
                    TxnField.config_asset_total: self.total_supply,
                    TxnField.config_asset_decimals: Int(3),
                    TxnField.config_asset_manager: self.address,
                    TxnField.config_asset_reserve: self.address,
                    TxnField.fee: Int(0),
                }
            ),
            InnerTxn.created_asset_id(),
        )