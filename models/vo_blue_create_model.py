# generated by datamodel-codegen:
#   filename:  VO_blue.json
#   timestamp: 2022-10-09T14:16:35+00:00

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field


class Category(Enum):
    field_4G = '4G'
    field_5G = '5G'
    service = 'service'


class Vim(BaseModel):
    name: str = Field(..., description='name of the VIM (as onboarded into the NFVO)')
    tenant: str = Field(
        ..., description='tenant name of the VIM (as onboarded into the NFVO)'
    )
    tacs: List = Field(
        ...,
        description='list of per-tracking area code parameters to instantiate the Blueprint',
    )


class VoBlueprintRequestInstance(BaseModel):
    type: Literal["VO"] = Field(
        None, description='type of the requested Blueprint'
    )
    callbackURL: Optional[str] = Field(
        None,
        description='url that will be used to notify when the topology terraforming ends',
    )
    config: Optional[Dict[str, Any]] = Field(
        None,
        description='parameters for the day2 configuration of the Blueprint instance',
    )
    vims: Optional[List[Vim]] = Field(
        None,
        description='list of VIMs to be used for the Blueprint instantiation',
        min_items=1,
    )
