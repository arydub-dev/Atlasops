"""Strict file contracts. Blank is missing, never implicit zero or approval."""
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class Source(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    record_id: str=Field(min_length=1,max_length=160)
    source: str=Field(min_length=1,max_length=255)
    source_updated_at: datetime | None=None
    @field_validator('source_updated_at',mode='after')
    @classmethod
    def utc(cls,v):
        if v is not None and v.tzinfo is None: raise ValueError('Timestamp must include timezone')
        return v.astimezone(timezone.utc) if v else v

class Requirement(Source):
    work_order: str=Field(min_length=1,max_length=160)
    sku: str=Field(min_length=1,max_length=100)
    site: str=Field(min_length=1,max_length=255)
    quantity: int | None=Field(default=None,ge=0,le=1000000000)
    required_by: datetime | None=None
    status: Literal['planned','in_progress','completed','cancelled']='planned'
    asset: str | None=None
    priority: int=Field(default=3,ge=1,le=5)
    @field_validator('required_by')
    @classmethod
    def date_utc(cls,v): return cls.utc(v)

class Stock(Source):
    sku: str=Field(min_length=1,max_length=100)
    site: str=Field(min_length=1,max_length=255)
    observed_quantity: int | None=Field(default=None,ge=0,le=1000000000)
    reserved_quantity: int | None=Field(default=None,ge=0,le=1000000000)
    usability: Literal['usable','quarantined','unknown']='unknown'
    criticality: str | None=None

class Inbound(Source):
    po: str=Field(min_length=1,max_length=160)
    line: str=Field(min_length=1,max_length=160)
    sku: str=Field(min_length=1,max_length=100)
    site: str=Field(min_length=1,max_length=255)
    supplier: str | None=None
    ordered_quantity: int | None=Field(default=None,ge=0,le=1000000000)
    open_quantity: int | None=Field(default=None,ge=0,le=1000000000)
    promised_at: datetime | None=None
    expected_at: datetime | None=None
    received_at: datetime | None=None
    date_source: str | None=None
    confirmed: bool | None=None
    shipment_reference: str | None=None
    @field_validator('promised_at','expected_at','received_at')
    @classmethod
    def date_utc(cls,v): return cls.utc(v)
    @model_validator(mode='after')
    def quantities(self):
        if self.ordered_quantity is not None and self.open_quantity is not None and self.open_quantity>self.ordered_quantity:
            raise ValueError('Open quantity exceeds ordered quantity')
        if self.received_at and self.open_quantity:
            raise ValueError('A receipt timestamp with remaining open units is ambiguous; split the line')
        return self

class Rule(Source):
    action: Literal['transfer','expedite','substitute','repair','reschedule','alias']
    sku: str=Field(min_length=1,max_length=100)
    site: str=Field(min_length=1,max_length=255)
    donor_site: str | None=None
    substitute_sku: str | None=None
    quantity: int | None=Field(default=None,ge=0,le=1000000000)
    lead_days: float | None=Field(default=None,ge=0,le=3650,allow_inf_nan=False)
    direct_cost: float | None=Field(default=None,ge=0,allow_inf_nan=False)
    currency: str | None=Field(default=None,min_length=3,max_length=3)
    approval_reference: str | None=None
    inbound_record_id: str | None=None
    owner: str | None=None
    repair_reference: str | None=None
    permitted: bool=False

class Policy(Source):
    max_age_days: int=Field(default=7,ge=1,le=365)
    ranking: Literal['arrival','known_cost']='arrival'

CONTRACTS={'requirement':Requirement,'stock':Stock,'inbound':Inbound,'rule':Rule,'policy':Policy}

def validate(kind,raw):
    if kind not in CONTRACTS: raise ValueError('Unknown recovery record type')
    # File parsers produce empty strings for blank cells.
    row={k:(None if v=='' else v) for k,v in raw.items()}
    return CONTRACTS[kind].model_validate(row).model_dump(mode='json')
