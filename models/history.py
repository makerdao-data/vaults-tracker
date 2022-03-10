from sqlalchemy import Column, String, DateTime, Float
from database import Base


class History(Base):

    __tablename__ = 'vaults'

    day = Column(DateTime)
    vault = Column(String)
    ilk = Column(String)
    collateral_eod = Column(Float)
    principal_eod = Column(Float)
    debt_eod = Column(Float)
    fees_eod = Column(Float)
    withdraw = Column(Float)
    deposit = Column(Float)
    principal_generate = Column(Float)
    principal_payback = Column(Float)
    debt_generate = Column(Float)
    debt_payback = Column(Float)
    fees = Column(Float)

    def to_dict(self):
        return {
            'day' : self.day,
            'vault' : self.vault, 
            'ilk' : self.ilk,
            'collateral_eod' : self.collateral_eod,
            'principal_eod' : self.principal_eod,
            'debt_eod' : self.debt_eod,
            'fees_eod' : self.fees_eod,
            'withdraw' : self.withdraw,
            'deposit' : self.deposit,
            'principal_generate' : self.principal_generate,
            'principal_payback' : self.principal_payback,
            'debt_generate' : self.debt_generate,
            'debt_payback' : self.debt_payback,
            'fees' : self.fees,
        }
    
    def to_list(self):
        return [
            self.day.__str__(),
            self.vault, 
            self.ilk,
            self.collateral_eod,
            self.principal_eod,
            self.debt_eod,
            self.fees_eod,
            self.withdraw,
            self.deposit,
            self.principal_generate,
            self.principal_payback,
            self.debt_generate,
            self.debt_payback,
            self.fees
        ]
    
    __table_args__ = {"schema": "maker.history"}
    __mapper_args__ = {
        "primary_key": [
            day,
            vault,
            ilk
        ]
    }
