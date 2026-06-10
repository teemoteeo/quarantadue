"""schemi pydantic che descrivono i contratti di I/O per il function calling."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

JsonScalarType = Literal["number", "integer", "string", "boolean"]


class ParameterSpec(BaseModel):
    """voce dello schema che descrive un singolo parametro di funzione."""

    model_config = ConfigDict(extra="forbid")

    type: JsonScalarType


class ReturnSpec(BaseModel):
    """voce dello schema che descrive il valore di ritorno di una funzione."""

    model_config = ConfigDict(extra="forbid")

    type: JsonScalarType


class FunctionDefinition(BaseModel):
    """una funzione chiamabile esposta al modello di linguaggio."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    parameters: dict[str, ParameterSpec]
    returns: ReturnSpec


class TestPrompt(BaseModel):
    """un prompt in linguaggio naturale da trasformare in una chiamata di funzione."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(..., min_length=1)


class FunctionCallResult(BaseModel):
    """il risultato del trasformare un prompt in una chiamata di funzione concreta."""

    model_config = ConfigDict(extra="forbid")

    prompt: str
    name: str
    parameters: dict[str, Any]
